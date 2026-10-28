"""Phase 5：'关于你的事实'的记忆半边，接 Context Forge（spec §3.1/§3.2）。

- 写：模型工具 remember_fact → store.put（draft 默认 candidate；实测 put 不碰 status，
  不改 CF 也不会自动 active）→ 本会话挂起。
- 批：会话收尾把"本会话新提议 + 库里未确认的 candidate"一起列（最多 5 条）
  → open_confirmation 拿活 token（同版本复用/过期自动重发，迟到不丢）
  → approve_confirmation(from_tty=真终端才 True)。没回答/非终端留到下次，不静默丢。
- 读：MemoryRecall 召回，注入 user 消息头部（可变段），不动稳定前缀。
- 物理隔离：进程内把 CONTEXT_FORGE_HOME 钉到 jmb 的 forge 目录（spec §3），
  CF 读环境变量是惰性的，先钉再调即可。
- 包边界（D32）：CF 是独立包，jmb 不复制其源码；开发期 editable path，
  发布期 pinned wheel，两边的 memory.db 始终各用各的。
"""
from __future__ import annotations

import os
import re
import uuid

from . import config

RECALL_LIMIT = 6
MAX_OFFERS = 5  # spec §3.2：每会话最多列 5 条，超出的下次再问


def _import_cf():
    """先钉 CONTEXT_FORGE_HOME 再 import——CF 的 runtime_dir() 惰性读环境变量。"""
    try:
        from context_forge.memory import MemoryStore
        from context_forge.memory_lifecycle import MemoryLifecycle
        from context_forge.memory_models import MemoryDraft, MemorySpace
        from context_forge.memory_recall import MemoryRecall
    except ImportError as exc:
        raise ImportError(
            "context-forge 包不可用：在 jmb 目录跑 `uv sync`；"
            "开发期它来自 ../Context Forge（editable，见 pyproject 的 tool.uv.sources）"
        ) from exc
    return MemoryStore, MemoryDraft, MemorySpace, MemoryRecall, MemoryLifecycle


class FactMemory:
    def __init__(self) -> None:
        os.environ["CONTEXT_FORGE_HOME"] = str(config.forge_home())  # 先钉，再让 CF 读
        MemoryStore, MemoryDraft, MemorySpace, MemoryRecall, MemoryLifecycle = _import_cf()

        self._MemoryDraft = MemoryDraft
        self._MemorySpace = MemorySpace
        self._MemoryLifecycle = MemoryLifecycle
        path = config.forge_home() / "memory.db"
        if not path.exists():
            MemoryStore.initialize(path)
        self.store = MemoryStore(path, readonly=False)
        self.recall = MemoryRecall(self.store)
        self.pending: list[dict] = []

    def propose(self, fact: str) -> str:
        body = (fact or "").strip()
        if not body:
            return "拒绝：事实内容为空。"
        memory_id = "jmb-" + uuid.uuid4().hex[:12]
        draft = self._MemoryDraft(
            kind="knowledge", role="claim", body=body, summary=body[:80],
            model=config.resolve_model().value,
            space=self._MemorySpace(owner="local", privacy="private"),
        )
        record = self.store.put(memory_id, draft, expected_version=0,
                                idempotency_key=f"jmb-propose:{memory_id}", actor="model",
                                reason="对话中他说的事实，待他确认")
        self.pending.append({"memory_id": record.id, "version": record.version, "body": body})
        return "OK：已存为待确认（candidate），会话收尾一起让他确认；确认前不会进召回。"

    def search(self, query: str) -> str:
        """召回 active 的记忆；candidate 召不到（设计如此）。失败返回空串，不阻塞对话。"""
        try:
            response = self.recall.search(query, project=None, limit=RECALL_LIMIT)
        except Exception:  # noqa: BLE001 —— 召回失败不该拖垮对话
            return ""
        lines = []
        for result in response.results:
            draft = result.memory.draft
            text = (draft.summary or draft.body).strip()
            if text:
                lines.append(f"- {text}")
        return "\n".join(lines)

    def _offers(self) -> tuple[list[dict], int]:
        """本会话新提议 + 库里未确认的 candidate；最多 5 条，返回(条目, 没列出的数量)。"""
        records = {record.id: record for record in self.store.current_records()}
        items: list[dict] = []
        for item in self.pending:
            record = records.get(item["memory_id"])
            if record is None or record.draft.status != "candidate" or record.draft.suppressed:
                continue
            items.append({"memory_id": record.id, "version": record.version, "body": item["body"]})
        seen = {item["memory_id"] for item in items}
        older = [record for record in records.values()
                 if record.id not in seen and record.draft.status == "candidate"
                 and not record.draft.suppressed]
        older.sort(key=lambda record: record.created_at)
        for record in older:
            body = (record.draft.summary or record.draft.body).strip()
            if body:
                items.append({"memory_id": record.id, "version": record.version, "body": body})
        return items[:MAX_OFFERS], max(0, len(items) - MAX_OFFERS)

    def _reject(self, items: list[dict]) -> str:
        """明确说 no 才走 CF 的 suppress；没回答/没选的都留到下次。"""
        lifecycle = self._MemoryLifecycle(self.store)
        out: list[str] = []
        for item in items:
            try:
                lifecycle.suppress(item["memory_id"], expected_version=item["version"],
                                   idempotency_key=f"jmb-suppress:{item['memory_id']}",
                                   reason="jmb 会话收尾：他说不要这条")
                out.append(f"不要了：{item['body'][:48]}")
            except Exception as exc:  # noqa: BLE001
                out.append(f"没丢成（{type(exc).__name__}: {str(exc)[:80]}）：{item['body'][:48]}")
        return "\n".join(out)

    def confirm_pending(self, interactive: bool, ask=None) -> str:
        """会话收尾批量确认。非终端（管道）运行一律不批——from_tty 守卫的语义。

        ask 是 GUI 回调：接收 (items, more)，返回 "ok"/"no"/序号串；不传就退回终端 input。
        """
        items, more = self._offers()
        self.pending.clear()
        if not items:
            return ""
        if ask is not None:
            answer = str(ask([item["body"] for item in items], more)).strip().lower()
        elif not interactive:
            return (f"[有 {len(items)} 条待确认事实，但本次不是终端运行——按设计不批，留到下次；"
                    f"要现在记就重开终端再聊一次。]")
        else:
            print(f"\n—— 会话收尾：{len(items)} 条事实等你确认（确认后才会进长期记忆）——")
            for i, item in enumerate(items, 1):
                print(f"  {i}) {item['body']}")
            if more:
                print(f"  （还有 {more} 条没列出来，下次再问）")
            try:
                answer = input(
                    "回 ok 全记 / 回序号（如 1,3，没选的留到下次）/ 回 no 全部不要 > "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n（没回答，全部留到下次）")
                return ""
        if answer in {"no", "n"}:
            return self._reject(items)
        chosen = (set(range(1, len(items) + 1)) if answer in {"ok", "y", "yes"}
                  else {int(n) for n in re.findall(r"\d+", answer) if 1 <= int(n) <= len(items)})
        if not chosen:
            print("（没选，全部留到下次）")
            return ""
        out: list[str] = []
        for i, item in enumerate(items, 1):
            if i not in chosen:
                out.append(f"留到下次：{item['body'][:48]}")
                continue
            try:
                token = self.store.open_confirmation(item["memory_id"], item["version"],
                                                     reason="jmb 会话收尾确认")["token"]
                self.store.approve_confirmation(token, from_tty=True)
                out.append(f"已记进长期记忆：{item['body'][:48]}")
            except Exception as exc:  # noqa: BLE001
                out.append(f"没记成（{type(exc).__name__}: {str(exc)[:80]}）：{item['body'][:48]}")
        return "\n".join(out)

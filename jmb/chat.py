"""jmb chat —— 对话循环（profile 驱动：循环不绑传输，spec §5.1/D29）。

- 流式出字；thinking 只提示不展示，历史里保留回传（按 profile 开关决定）。
- Anthropic 线：服务端 web_search 声明即用（端点忽略 max_uses，实测 ⇒ 轮数靠客户端闸门）。
- OpenAI 线：无服务端搜索 ⇒ 声明 search_web（Bing 兜底）。
- 客户端工具：fetch_page / remember_fact / read_code / grep / find / write_file / edit_file /
  run_command / today_brief / update_self_file / (search_web)。
  模型只出操作决策，落盘全走 gate / memory / grants / code / brief 的确定性代码。
- 预算闸门：每轮发送前 count_tokens（anthropic 线实测可用），超了折叠老轮次的 thinking 与搜索结果。
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
import uuid

from . import brief, code, config, gate, grants, prefix, providers, search, seeds, webfetch

INPUT_BUDGET = 30000  # spec §5.6 客户端闸门；跑一周后按 usage 重定


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def _usage_line(usage: dict) -> str:
    parts = [f"in={usage.get('input', 0)}", f"cache_read={usage.get('cache_read', 0)}",
             f"out={usage.get('output', 0)}"]
    if usage.get("web_search"):
        parts.append(f"web_search={usage['web_search']}")
    return " ".join(parts)


# ---- 客户端工具声明（顺序固定，利于缓存）----

FETCH_PAGE = {
    "name": "fetch_page",
    "description": ("抓一个网页的正文。服务端搜索结果没有正文（encrypted_content 客户端解不开），"
                    "要引用、核对就必须真去抓。404/反爬/JS 渲染会如实返回'读不到'——那就如实告诉他。"),
    "input_schema": {"type": "object",
                     "properties": {"url": {"type": "string", "description": "完整的 http(s) URL"}},
                     "required": ["url"]},
}

REMEMBER_FACT = {
    "name": "remember_fact",
    "description": ("把'他说过的关于他自己的原话级事实'存为一条待确认记忆（例：'我周末一般不开电脑'）。"
                    "一次一条、原话级；不记情绪数值、不推断性格、不记公司项目相关内容。"
                    "存进去是 candidate，他收尾确认后才生效。"),
    "input_schema": {"type": "object",
                     "properties": {"fact": {"type": "string", "description": "他的原话或极接近原话的一句话"}},
                     "required": ["fact"]},
}

READ_CODE = {
    "name": "read_code",
    "description": ("读他的代码（列目录或读文件）。默认任何仓都不可读（D11 白名单）；"
                    "未授权的路径会触发一个终端检查点，他允许才读得到。"
                    "read 可用 offset/limit 分段读；响应按行数和字符数截断。"),
    "input_schema": {"type": "object",
                     "properties": {
                         "path": {"type": "string", "description": "文件或目录路径"},
                         "action": {"type": "string", "enum": ["read", "list"],
                                    "description": "read=读文件内容，list=列目录（目录只能 list）"},
                         "offset": {"type": "integer", "description": "从第几行开始（1-based），默认 1"},
                         "limit": {"type": "integer", "description": "最多读多少行"}},
                     "required": ["path"]},
}

GREP = {
    "name": "grep",
    "description": ("在文件/目录里按正则搜代码。只读，不需要执行授权；会跳过 "
                    ".git/node_modules/.venv/二进制；输出有上限。"),
    "input_schema": {"type": "object",
                     "properties": {
                         "pattern": {"type": "string", "description": "正则表达式"},
                         "path": {"type": "string", "description": "文件或目录"},
                         "glob": {"type": "string", "description": "只搜匹配的文件名，如 *.py"},
                         "case_sensitive": {"type": "boolean", "description": "默认 true"},
                         "max_results": {"type": "integer", "description": "默认 200，上限 500"}},
                     "required": ["pattern", "path"]},
}

FIND = {
    "name": "find",
    "description": ("按文件名 glob 找文件。只读，不需要执行授权；会跳过 "
                    ".git/node_modules/.venv 等；输出有上限。"),
    "input_schema": {"type": "object",
                     "properties": {
                         "path": {"type": "string", "description": "目录"},
                         "name_pattern": {"type": "string", "description": "文件名 glob，默认 *"},
                         "max_results": {"type": "integer", "description": "默认 200，上限 500"}},
                     "required": ["path"]},
}

WRITE_FILE = {
    "name": "write_file",
    "description": ("创建或整文件覆盖一个代码文件。只用于新文件或完整重写；"
                    "改已有代码优先用 edit_file。首次写会请求本会话授权；"
                    "会存 preimage，undo 回滚整轮。"),
    "input_schema": {"type": "object",
                     "properties": {
                         "path": {"type": "string", "description": "文件路径（相对或绝对）"},
                         "content": {"type": "string", "description": "完整文件内容"}},
                     "required": ["path", "content"]},
}

EDIT_FILE = {
    "name": "edit_file",
    "description": ("对文件做精确文本替换。edits[].old_text 必须对原文唯一且不重叠；"
                    "一次调用可传多个不相邻的替换。改已有代码优先用它，返回 diff。"),
    "input_schema": {"type": "object",
                     "properties": {
                         "path": {"type": "string", "description": "文件路径（相对或绝对）"},
                         "edits": {"type": "array", "items": {
                             "type": "object",
                             "properties": {
                                 "old_text": {"type": "string", "description": "原文中必须唯一且精确匹配的片段"},
                                 "new_text": {"type": "string", "description": "替换后的文本"}},
                             "required": ["old_text", "new_text"]}}},
                     "required": ["path", "edits"]},
}

RUN_COMMAND = {
    "name": "run_command",
    "description": ("在指定目录执行 shell 命令（测试/构建/查看）。默认在 Docker 沙箱里执行"
                    "（JMB_SANDBOX_IMAGE）；只有 JMB_SANDBOX=host 才显式关闭。首次执行会请求"
                    "本会话授权；输出会截断，完整输出落盘；非零退出如实返回；命令副作用不能 undo。"),
    "input_schema": {"type": "object",
                     "properties": {
                         "command": {"type": "string", "description": "要执行的命令"},
                         "cwd": {"type": "string", "description": "工作目录；默认 jmb 当前目录"},
                         "timeout": {"type": "number", "description": "超时秒数，默认 120，最大 600"}},
                     "required": ["command"]},
}

TODAY_BRIEF = {
    "name": "today_brief",
    "description": "读今天已经生成的每日榜单（GitHub 新高星/周榜/AI 会议）。他问'今天有什么新东西'时先调这个。",
    "input_schema": {"type": "object", "properties": {}},
}

BING_SEARCH = {
    "name": "search_web",
    "description": "本机兜底搜索（当前线路没有服务端搜索时用）。Bing 网页结果：标题+链接+摘要；不可用就如实说，不编。",
    "input_schema": {"type": "object",
                     "properties": {"query": {"type": "string"}},
                     "required": ["query"]},
}


def _tools(profile) -> list:
    client_tools = [prefix.UPDATE_SELF_FILE, FETCH_PAGE, REMEMBER_FACT, READ_CODE,
                    GREP, FIND, WRITE_FILE, EDIT_FILE, RUN_COMMAND, TODAY_BRIEF]
    if profile.supports_server_web_search:
        return [prefix.WEB_SEARCH, *client_tools]
    return [*client_tools, BING_SEARCH]


# ---- 预算闸门（spec §5.6 本地侧）----

_MASKABLE_TOOLS = {"read_code", "grep", "find", "fetch_page", "search_web", "today_brief"}
_MASK_TEXT = "[已清理：{name} 的旧结果；需要时重新调用]"


def _mask_old_tool_results(history: list, keep: int = 10, min_chars: int = 400) -> None:
    """第一层压缩：旧的可重取工具结果换成占位符，不花模型调用。"""
    names: dict[str, str] = {}
    for message in history:
        if message.get("role") != "assistant":
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                names[str(block.get("id"))] = str(block.get("name") or "")
    for message in history[:-keep]:
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            name = names.get(str(block.get("tool_use_id")), "")
            value = block.get("content")
            if name in _MASKABLE_TOOLS and isinstance(value, str) and len(value) >= min_chars:
                block["content"] = _MASK_TEXT.format(name=name)


def _trim_search_results(history: list) -> None:
    """每块搜索结果最多留 5 条（spec 的 M=5；服务端无条数参数）。"""
    for message in history:
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for block in content:
            if (isinstance(block, dict) and block.get("type") == "web_search_tool_result"
                    and isinstance(block.get("content"), list) and len(block["content"]) > 5):
                block["content"] = block["content"][:5]


def _enforce_budget(count_fn, profile, system: str, tools: list, history: list,
                    budget: int = INPUT_BUDGET) -> None:
    _mask_old_tool_results(history)
    _trim_search_results(history)
    if count_fn is None:  # OpenAI 线暂无 count_tokens ⇒ 只做确定性修剪
        return
    try:
        used = count_fn(system, tools, history)
    except Exception:  # noqa: BLE001 —— count_tokens 挂了就跳过闸门，别挡对话
        return
    if used <= budget:
        return
    # 超预算：老轮次（保留最近 4 条消息）折叠——thinking 丢弃仅当 profile 允许（本线路实测白送）。
    for message in history[:-4]:
        content = message.get("content")
        if not isinstance(content, list):
            continue
        kept = []
        for block in content:
            if not isinstance(block, dict):
                kept.append(block)
                continue
            if block.get("type") == "thinking" and profile.allow_thinking_drop:
                continue
            if block.get("type") == "web_search_tool_result" and isinstance(block.get("content"), list):
                block = {**block, "content": block["content"][:2]}
            kept.append(block)
        if not kept:
            continue  # 整条只有可丢块（如 thinking-only）：保留原样，别写成空 content
        message["content"] = kept


# ---- 一轮对话（含客户端工具循环）----

def _dispatch(name: str, payload: dict, fact_memory, code_session) -> str:
    if name == "update_self_file":
        return gate.apply(payload)
    if name == "fetch_page":
        return webfetch.fetch_page(str(payload.get("url", "")))
    if name == "remember_fact":
        return (fact_memory.propose(str(payload.get("fact", ""))) if fact_memory
                else "记忆半边没接上（CF 不可用），这条先没记。")
    if name == "read_code":
        path, action = str(payload.get("path", "")), str(payload.get("action", "read"))
        ok, why = grants.authorize(path, action, interactive=sys.stdin.isatty())
        if not ok:
            return why
        return grants.perform(path, action, offset=payload.get("offset", 1),
                              limit=payload.get("limit"))
    if name == "grep":
        pattern, path = str(payload.get("pattern", "")), str(payload.get("path", ""))
        ok, why = grants.authorize(path, "grep", interactive=sys.stdin.isatty())
        if not ok:
            return why
        try:
            return search.grep(pattern, path, payload.get("glob"),
                               bool(payload.get("case_sensitive", True)),
                               payload.get("max_results", 200))
        except (search.SearchError, OSError) as exc:
            return f"拒绝：{type(exc).__name__}: {exc}"
    if name == "find":
        path = str(payload.get("path", ""))
        ok, why = grants.authorize(path, "find", interactive=sys.stdin.isatty())
        if not ok:
            return why
        try:
            return search.find(path, str(payload.get("name_pattern") or "*"),
                               payload.get("max_results", 200))
        except (search.SearchError, OSError) as exc:
            return f"拒绝：{type(exc).__name__}: {exc}"
    if name == "write_file":
        path = str(payload.get("path", ""))
        ok, why = grants.authorize_write(path, interactive=sys.stdin.isatty())
        if not ok:
            return why
        try:
            return code.write_file(path, payload.get("content", ""), code_session)
        except (code.CodeError, OSError) as exc:
            return f"拒绝：{type(exc).__name__}: {exc}"
    if name == "edit_file":
        path = str(payload.get("path", ""))
        ok, why = grants.authorize_write(path, interactive=sys.stdin.isatty())
        if not ok:
            return why
        try:
            return code.edit_file(path, payload.get("edits"), code_session)
        except (code.CodeError, OSError) as exc:
            return f"拒绝：{type(exc).__name__}: {exc}"
    if name == "run_command":
        command = str(payload.get("command", ""))
        cwd = str(payload.get("cwd") or os.getcwd())
        ok, why = grants.authorize_exec(command, cwd, interactive=sys.stdin.isatty())
        if not ok:
            return why
        try:
            return code.run_command(command, cwd, payload.get("timeout"), code_session)
        except (code.CodeError, OSError) as exc:
            return f"拒绝：{type(exc).__name__}: {exc}"
    if name == "today_brief":
        return brief.today_text()
    if name == "search_web":
        return webfetch.bing_search(str(payload.get("query", "")))
    return f"未知工具 {name}，没执行。"


_SELF_ANNOUNCE = {"update_self_file"}
_CODE_ANNOUNCE = {"write_file", "edit_file", "run_command"}


class ChatSession:
    """终端和 GUI 共用：模型/工具/记忆/代码改动都在这里，入口只负责收事件。"""

    def __init__(self, emit) -> None:
        self.emit = emit
        seeds.ensure()
        self.profile = providers.load_profile()
        if self.profile.protocol == "anthropic" and not config.resolve_token().value:
            raise RuntimeError("没有模型凭据——先跑 `jmb doctor` 看 token 那一行。")

        self.fact_memory = None
        try:
            from . import memory as jmb_memory
            self.fact_memory = jmb_memory.FactMemory()
        except Exception as exc:  # noqa: BLE001 —— 记忆半边不可用不阻塞对话
            self.emit("warning", f"[长期事实记忆没接上：{type(exc).__name__}: "
                                f"{str(exc)[:120]}——本会话只能用文件记录]")

        self.code_session = code.CodeSession()
        self.count_fn = None
        if self.profile.protocol == "anthropic":
            import anthropic
            client = anthropic.Anthropic(base_url=self.profile.base_url,
                                         auth_token=config.resolve_token().value,
                                         timeout=120.0, max_retries=1)
            self.count_fn = lambda system, tools, history: (  # noqa: E731
                client.messages.count_tokens(model=self.profile.model, system=system,
                                             tools=tools, messages=history).input_tokens)

        self.system = prefix.build_system()
        self.tools = _tools(self.profile)
        config.sessions_dir().mkdir(parents=True, exist_ok=True)
        self.tid = uuid.uuid4().hex[:6]
        self.transcript_path = config.sessions_dir() / f"{_dt.date.today().isoformat()}-{self.tid}.jsonl"
        self.log = self.transcript_path.open("a", encoding="utf-8")
        self.history: list[dict] = []
        self.notes: list[str] = []
        self.input_budget = self.profile.input_budget
        self.last_input_tokens = 0
        self._compact_cooldown = 0
        self.closed = False

    def _should_compact(self) -> bool:
        return (self._compact_cooldown <= 0
                and self.last_input_tokens >= int(self.input_budget * 0.8)
                and len(self.history) >= 14)

    def _compact(self) -> None:
        from . import compact
        before = len(self.history)
        self.emit("compacting", "")
        try:
            summary = compact.summarize(self.profile, self.history)
            result = compact.apply(self.history, summary)
        except Exception as exc:  # noqa: BLE001 —— 压缩失败就用裁剪兜底
            self.emit("warning", f"[上下文压缩失败：{type(exc).__name__}: "
                                f"{str(exc)[:120]}；继续用裁剪兜底]")
            self.last_input_tokens = 0
            self._compact_cooldown = 3
            return
        if result is None:
            self.last_input_tokens = 0
            self._compact_cooldown = 3
            return
        _cut, after = result
        self.last_input_tokens = 0
        try:
            self.log.write(json.dumps({"ts": _now(), "kind": "compact",
                                      "before": before, "after": after,
                                      "summary": summary}, ensure_ascii=False) + "\n")
            self.log.flush()
        except Exception:  # noqa: BLE001
            pass
        self.emit("compacted", {"before": before, "after": after})

    def send(self, text: str) -> None:
        user = (text or "").strip()
        if not user:
            return
        if self._compact_cooldown > 0:
            self._compact_cooldown -= 1
        if self._should_compact():
            self._compact()
        prefixes: list[str] = []
        if self.notes:
            prefixes.extend(self.notes)
            self.notes.clear()
        if self.fact_memory:
            recalled = self.fact_memory.search(user)
            if recalled:
                prefixes.append(f"[记忆召回——他以前说过的事，可自然引用]\n{recalled}")
        send_text = "\n\n".join([*prefixes, user]) if prefixes else user
        self.history.append({"role": "user", "content": send_text})
        self.log.write(json.dumps({"ts": _now(), "kind": "user", "text": user},
                                  ensure_ascii=False) + "\n")
        self.log.flush()
        try:
            self.code_session.begin_turn()
            usage = _stream_turn(self.profile, self.count_fn, self.system, self.tools,
                                 self.history, self.log, self.fact_memory, self.code_session,
                                 self.emit, budget=self.input_budget)
            if isinstance(usage, dict) and usage.get("input"):
                self.last_input_tokens = int(usage["input"])
        except Exception as exc:  # noqa: BLE001 —— 一轮失败不拖垮会话
            self.emit("error", f"{type(exc).__name__}: {str(exc)[:300]}")
        finally:
            self.code_session.end_turn()
            self.emit("turn_end", {"transcript": str(self.transcript_path)})

    def undo(self) -> str:
        message = self.code_session.undo_last_turn() or gate.undo()
        if (message and "没有可撤" not in message
                and "能撤的都撤过了" not in message
                and "没有文件需要恢复" not in message):
            note = ("[系统事件，不是用户发言] 用户刚撤销了最近一轮改动；以这条为准，"
                    "之前工具结果里的写入/编辑不再代表当前文件。撤销结果：" + message)
            self.notes.append(note)
            try:
                self.log.write(json.dumps({"ts": _now(), "kind": "undo",
                                          "message": message}, ensure_ascii=False) + "\n")
                self.log.flush()
            except Exception:  # noqa: BLE001
                pass
        return message

    def confirm_pending(self, interactive: bool, ask=None) -> str:
        return (self.fact_memory.confirm_pending(interactive=interactive, ask=ask)
                if self.fact_memory else "")

    def close(self) -> None:
        if self.closed:
            return
        try:
            self.log.close()
        finally:
            self.closed = True


def _stream_turn(profile, count_fn, system: str, tools: list, history: list, log,
                 fact_memory, code_session, emit, budget: int = INPUT_BUDGET) -> dict:
    thinking_shown = False
    last_usage: dict = {}

    def on_event(kind: str, text: str = "") -> None:
        nonlocal thinking_shown
        if kind == "thinking":
            if not thinking_shown:
                emit("thinking", "")
                thinking_shown = True
        else:
            emit(kind, text)

    while True:
        _enforce_budget(count_fn, profile, system, tools, history, budget=budget)
        turn = providers.stream_turn(profile, system, tools, history, on_event)
        last_usage = turn.usage or {}
        emit("text_end", "")
        emit("usage", turn.usage)
        log.write(json.dumps({"ts": _now(), "kind": "assistant", "blocks": turn.blocks,
                              "usage": turn.usage}, ensure_ascii=False) + "\n")
        log.flush()
        if not turn.blocks:
            return last_usage  # 空轮次不进历史，避免下次请求 400
        history.append({"role": "assistant", "content": turn.blocks})

        if turn.stop_reason != "tool_use":
            return last_usage

        results = []
        for block in turn.blocks:
            if block.get("type") != "tool_use":
                continue
            name, payload = block.get("name", ""), dict(block.get("input") or {})
            if name == "fetch_page":
                emit("activity", f"（抓正文：{str(payload.get('url', ''))[:80]}…）")
            elif name == "grep":
                emit("activity", f"（搜代码：{str(payload.get('pattern', ''))[:60]}）")
            elif name == "find":
                emit("activity", f"（找文件：{str(payload.get('name_pattern') or '*')[:60]}）")
            elif name == "remember_fact" and fact_memory and str(payload.get("fact", "")).strip():
                emit("activity", "（想记一条事实，收尾时让你确认）")
            receipt = _dispatch(name, payload, fact_memory, code_session)
            if name in _SELF_ANNOUNCE:
                note = str(payload.get("note", "")).strip()
                emit("self_edit", {"target": payload.get("target", "?"), "note": note})
                log.write(json.dumps({"ts": _now(), "kind": "self_edit", "decision": payload,
                                      "receipt": receipt}, ensure_ascii=False) + "\n")
            elif name in _CODE_ANNOUNCE:
                emit("code", {"name": name, "receipt": receipt})
                log.write(json.dumps({"ts": _now(), "kind": "code_tool", "name": name,
                                      "input": payload, "receipt": receipt},
                                     ensure_ascii=False) + "\n")
            results.append({"type": "tool_result", "tool_use_id": block.get("id", ""),
                            "content": receipt})
        if not results:
            return last_usage  # 声称 tool_use 却没有工具块：别写空 user 消息
        history.append({"role": "user", "content": results})


def _terminal_emit(kind: str, data) -> None:
    if kind == "text":
        print(data, end="", flush=True)
    elif kind == "text_start":
        print(flush=True)
    elif kind == "text_end":
        print()
    elif kind == "thinking":
        print("（它在想……）", flush=True)
    elif kind == "search":
        print("（联网搜索中……）", flush=True)
    elif kind == "usage":
        print(f"  └ {_usage_line(data)}")
    elif kind == "activity":
        print(str(data), flush=True)
    elif kind == "compacting":
        print("（压缩上下文……）", flush=True)
    elif kind == "compacted":
        print(f"  └ 上下文已压缩：{data.get('before')} → {data.get('after')} 条")
    elif kind == "warning":
        print(str(data), flush=True)
    elif kind == "self_edit":
        note = str(data.get("note", "")).strip()
        print(f"\n  [jmb 改了 {data.get('target', '?')}，说 undo 可撤]"
              f"{('——' + note) if note else ''}")
    elif kind == "code":
        receipt = str(data.get("receipt", ""))
        shown = receipt[:3000] + ("…" if len(receipt) > 3000 else "")
        print(f"\n  [jmb {data.get('name')}]\n{shown}")
    elif kind == "error":
        print(f"\n[这一轮出错：{data}]")
        print("（历史已保留，换个说法再说，或 /quit）")
    elif kind == "turn_end":
        pass


def run() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        session = ChatSession(_terminal_emit)
    except Exception as exc:  # noqa: BLE001
        print(f"{type(exc).__name__}: {exc}")
        return 1

    print(f"jmb · 会话 {session.tid}（线路 {session.profile.name} · 转录 {session.transcript_path.name}）")
    print("命令：/quit 退出 · undo 撤回最近一轮代码改动或最近一次自我改写 · 其余都是对话")
    print("——流式出字；（联网搜索中…）服务端搜索；（抓正文…）fetch_page\n")

    try:
        while True:
            try:
                user = input("你> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not user:
                continue
            if user in {"/quit", "/exit", "q"}:
                break
            if user.lower() == "undo":
                print(session.undo())
                continue
            session.send(user)
    finally:
        print(session.confirm_pending(interactive=sys.stdin.isatty()))
        session.close()
    print(f"\n再见。转录在 {session.transcript_path}")
    return 0

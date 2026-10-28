"""Phase 6：白名单授权（D11 丙 / D13 口子 3）。

grants.json 是记录不是配置；scope 两档（2026-10-27 评审定）：
session = 进程内集合（REPL 会话即进程，退出即失效）/ persistent = 落盘，可 revoke。
默认拒绝清单写死公司仓——命中就不追问，这是 D11 的裁定成本不对称（漏读没事，误读不可逆）。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from . import config

DENY_SUBSTRINGS = ("platform-group-projects",)
READ_CHAR_BUDGET = 20000

_session_grants: set[str] = set()
_write_session = False
_exec_session = False


def _norm(path: str) -> str:
    real = os.path.realpath(os.path.expanduser(path))
    return os.path.normpath(real).lower().replace("\\", "/")


def deny_reason(path: str) -> str:
    """公司仓、jmb 自身数据目录、.git 目录的硬拒原因；空串=没命中。"""
    norm = _norm(path)
    if any(marker in norm for marker in DENY_SUBSTRINGS):
        return "这个仓在默认拒绝清单里（公司项目，D11）。"
    spaces = _norm(str(config.spaces_dir()))
    if norm == spaces or norm.startswith(spaces + "/"):
        return "jmb 自身的数据目录（persona/记忆/授权/日志）不允许走代码工具写。"
    if ".git" in norm.split("/"):
        return ".git 目录不允许通过代码工具修改。"
    return ""


def _load() -> list[dict]:
    try:
        data = json.loads(config.grants_path().read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save(records: list[dict]) -> None:
    config.grants_path().parent.mkdir(parents=True, exist_ok=True)
    config.grants_path().write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")


def status(path: str) -> str:
    """deny（硬拒，不追问）/ granted / ask。persistent 授权按前缀覆盖子路径。"""
    if deny_reason(path):
        return "deny"
    norm = _norm(path)
    for record in _load():
        if record.get("scope") != "persistent":
            continue
        base = str(record.get("path", "")).rstrip("/")
        if norm == base or norm.startswith(base + "/"):
            return "granted"
    parts = norm.split("/")
    for i in range(len(parts), 2, -1):  # session 授权：任一祖先目录命中即覆盖
        if "/".join(parts[:i]) in _session_grants:
            return "granted"
    return "ask"


def grant(path: str, scope: str = "session") -> None:
    norm = _norm(path)
    if scope == "persistent":
        records = _load()
        if not any(r.get("path") == norm and r.get("scope") == "persistent" for r in records):
            records.append({"owner": "local", "path": norm,
                            "granted_at": datetime.now().isoformat(timespec="seconds"),
                            "scope": "persistent", "source_tag": "user_ok"})
            _save(records)
    _session_grants.add(norm)


def revoke(path: str) -> str:
    norm = _norm(path)
    records = _load()
    before = len(records)
    _save([r for r in records if r.get("path") != norm])
    _session_grants.discard(norm)
    return f"已撤销 {norm}（persistent 移除 {before - len(_load())} 条，session 授权已清）"


def records() -> list[dict]:
    return _load()


def reset_session() -> None:
    """测试/新会话用：清掉本会话的读、写、执行授权。"""
    global _write_session, _exec_session
    _session_grants.clear()
    _write_session = False
    _exec_session = False


def authorize(path: str, action: str, interactive: bool) -> tuple[bool, str]:
    """检查点：granted 直接过；ask 时终端里问一次；管道运行默认拒绝。"""
    reason = deny_reason(path)
    if reason:
        return False, reason
    state = status(path)
    if state == "deny":
        return False, "这个路径在默认拒绝清单里，不读。"
    if state == "granted":
        return True, ""
    if not interactive:
        return False, "需要授权，但他不在终端旁（本次是管道运行）：按设计默认拒绝。"
    try:
        answer = input(f"jmb 想读你的代码（{action} {path}）。允许吗？[y=仅本次会话 / a=以后都行 / n=不行] > ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False, "没拿到授权，就不读。"
    if answer not in {"y", "a", "yes", "all"}:
        return False, "他不允许读这个路径。"
    grant(path, scope="persistent" if answer.startswith("a") else "session")
    return True, ""


def authorize_write(path: str, interactive: bool) -> tuple[bool, str]:
    """写/改代码：本会话授权一次，之后本会话放行（D34）。"""
    global _write_session
    reason = deny_reason(path)
    if reason:
        return False, reason
    if _write_session:
        return True, ""
    if not interactive:
        return False, "写代码需要授权，但他不在终端旁（本次是管道运行）：按设计拒绝。"
    try:
        answer = input(
            f"jmb 想写/改你的代码（{path}）。允许本会话写代码吗？[y/n]"
            "（本会话后续写/改不再逐次询问；公司仓/jmb 数据目录/.git 仍硬拒） > "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False, "没拿到授权，就不写。"
    if answer not in {"y", "yes"}:
        return False, "他不允许本会话写代码。"
    _write_session = True
    _session_grants.add(_norm(path))
    return True, ""


def authorize_exec(command: str, cwd: str, interactive: bool) -> tuple[bool, str]:
    """执行命令：本会话授权一次；命令副作用不能 undo（D34）。"""
    global _exec_session
    reason = deny_reason(cwd)
    if reason:
        return False, reason
    low = command.lower().replace("\\", "/")
    if "platform-group-projects" in low:
        return False, "命令触碰公司仓（D11），拒绝执行。"
    spaces = _norm(str(config.spaces_dir()))
    if spaces and spaces in low:
        return False, "命令触碰 jmb 自身数据目录，拒绝执行。"
    if _exec_session:
        return True, ""
    if not interactive:
        return False, "执行命令需要授权，但他不在终端旁（本次是管道运行）：按设计拒绝。"
    print(f"jmb 想执行命令：{command[:300]}")
    print(f"工作目录：{cwd}")
    print("（命令以你的系统权限执行，jmb 没有沙箱；本会话后续命令不再逐次询问，副作用不能 undo。）")
    try:
        answer = input("允许本会话执行命令吗？[y/n] > ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False, "没拿到授权，就不执行。"
    if answer not in {"y", "yes"}:
        return False, "他不允许本会话执行命令。"
    _exec_session = True
    return True, ""


def perform(path: str, action: str, offset: int = 1, limit: int | None = None) -> str:
    """真正的读。调用前必须先 authorize。offset 从 1 开始。"""
    target = Path(os.path.expanduser(path))
    if action == "list":
        if not target.is_dir():
            return f"{path} 不是目录（要读文件就把 action 设为 read）。"
        try:
            entries = sorted(target.iterdir(), key=lambda e: e.name)
        except OSError as exc:
            return f"列不了：{type(exc).__name__}"
        lines = [f"[目录] {e.name}" if e.is_dir() else e.name for e in entries[:200]]
        more = f"\n…共 {len(entries)} 项，已截断" if len(entries) > 200 else ""
        return f"{path}（{len(entries)} 项）\n" + "\n".join(lines) + more
    if not target.is_file():
        return f"{path} 不是文件（要列目录就把 action 设为 list）。"
    try:
        data = target.read_bytes()
    except OSError as exc:
        return f"读不到：{type(exc).__name__}"
    text = data.decode("utf-8", "replace")
    if "\x00" in text:
        return f"{path} 看起来是二进制文件，不按文本读。"
    lines = text.splitlines()
    total = len(lines)
    if total == 0:
        return f"{path}（空文件）"
    try:
        start = max(0, int(offset) - 1)
    except (TypeError, ValueError):
        start = 0
    if start >= total:
        return f"offset {offset} 超出文件末尾（共 {total} 行）。"
    if limit is None:
        end = total
    else:
        try:
            end = min(total, start + max(1, int(limit)))
        except (TypeError, ValueError):
            end = total
    selected = "\n".join(lines[start:end])
    header = f"{path}（第 {start + 1}-{end} 行 / 共 {total} 行）"
    if len(selected) > READ_CHAR_BUDGET:
        kept = selected[:READ_CHAR_BUDGET]
        selected = kept + (f"\n…[已截断：本段共 {end - start} 行，已给前 "
                           f"{kept.count(chr(10)) + 1} 行；要后续段落说\"继续读 {path}\"]")
    return header + "\n" + selected

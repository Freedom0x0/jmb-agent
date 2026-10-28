"""代码写入工具（D34）：write_file / edit_file / run_command。

编辑语义参考 Pi coding agent（MIT）的 edit 契约：
多个精确替换对原文匹配、必须唯一且不重叠；精确失败后做保守归一（行尾空白/
智能引号/破折号/特殊空格）；保留 BOM 和原换行；返回 diff。

边界（他选的“任意路径 + 本会话授权 + 按轮次撤销”）：
- 公司仓、jmb 自身 spaces、.git 目录硬拒（安全护栏，不是项目根 fence）；
- 首次写/执行触发本会话授权，之后本会话放行；
- 每轮用户消息一个 change set，undo 回滚整轮；
- 命令副作用不能 undo；输出截断，完整输出落盘。
"""
from __future__ import annotations

import datetime as _dt
import difflib
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import time
import unicodedata
import uuid
from pathlib import Path

from . import config, grants

COMMAND_MAX_BYTES = 20 * 1024
COMMAND_MAX_LINES = 800
COMMAND_DEFAULT_TIMEOUT = 120
COMMAND_MAX_TIMEOUT = 600
DIFF_MAX_CHARS = 5000
BOM = b"\xef\xbb\xbf"


class CodeError(RuntimeError):
    pass


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.jmb-tmp-{uuid.uuid4().hex[:8]}")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _resolve(path: str) -> Path:
    return Path(os.path.realpath(os.path.abspath(os.path.expanduser(path))))


def _check_denied(path: str) -> Path:
    target = _resolve(path)
    reason = grants.deny_reason(str(target))
    if reason:
        raise CodeError(reason)
    return target


def _split_bom(data: bytes) -> tuple[bool, bytes]:
    if data.startswith(BOM):
        return True, data[len(BOM):]
    return False, data


def _detect_eol(text: str) -> str:
    index = text.find("\n")
    if index > 0 and text[index - 1] == "\r":
        return "\r\n"
    return "\n"


def _normalize_lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _restore_eol(text: str, eol: str) -> str:
    return text.replace("\n", "\r\n") if eol == "\r\n" else text


def _normalize_fuzzy(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"[\u2018\u2019\u201A\u201B]", "'", text)
    text = re.sub(r"[\u201C\u201D\u201E\u201F]", '"', text)
    text = re.sub(r"[\u2010-\u2015\u2212]", "-", text)
    text = re.sub(r"[\u00A0\u2002-\u200A\u202F\u205F\u3000]", " ", text)
    return text


def _unified_diff(path: str, old: str, new: str) -> str:
    diff = "".join(difflib.unified_diff(
        old.splitlines(keepends=True), new.splitlines(keepends=True),
        fromfile=path, tofile=path, n=4))
    if len(diff) > DIFF_MAX_CHARS:
        diff = diff[:DIFF_MAX_CHARS] + "\n...[diff 已截断]"
    return diff


def _occurrences(base: str, needle: str) -> int:
    count = 0
    start = 0
    while True:
        index = base.find(needle, start)
        if index == -1:
            return count
        count += 1
        start = index + len(needle)


def _apply_edits(path: str, content: str, edits) -> tuple[str, str]:
    if isinstance(edits, str):
        try:
            edits = json.loads(edits)
        except ValueError as exc:
            raise CodeError("edits 不是合法 JSON") from exc
    if isinstance(edits, dict):
        edits = [edits]
    if not isinstance(edits, list) or not edits:
        raise CodeError("edits 不能为空")
    normalized: list[tuple[int, str, str]] = []
    for index, edit in enumerate(edits):
        if not isinstance(edit, dict):
            raise CodeError(f"edits[{index}] 不是对象")
        old = edit.get("old_text", edit.get("oldText"))
        new = edit.get("new_text", edit.get("newText"))
        if not isinstance(old, str) or not isinstance(new, str):
            raise CodeError(f"edits[{index}] 需要 old_text/new_text 字符串")
        old = _normalize_lf(old)
        new = _normalize_lf(new)
        if not old:
            raise CodeError(f"edits[{index}].old_text 不能为空")
        normalized.append((index, old, new))

    need_fuzzy = any(content.find(old) == -1 for _, old, _ in normalized)
    base = _normalize_fuzzy(content) if need_fuzzy else content
    matches: list[tuple[int, int, str, int]] = []
    for index, old, new in normalized:
        needle = _normalize_fuzzy(old) if need_fuzzy else old
        match = base.find(needle)
        if match == -1:
            raise CodeError(f"edits[{index}] 在 {path} 里找不到精确文本；old_text 必须和原文一致")
        count = _occurrences(base, needle)
        if count > 1:
            raise CodeError(f"edits[{index}] 在 {path} 里出现 {count} 次；old_text 必须唯一")
        matches.append((match, len(needle), new, index))

    matches.sort(key=lambda item: item[0])
    for previous, current in zip(matches, matches[1:]):
        if previous[0] + previous[1] > current[0]:
            raise CodeError(
                f"edits[{previous[3]}] 和 edits[{current[3]}] 重叠；合并成一条或改成不相邻")

    if not need_fuzzy:
        result = base
        for match, length, new, _ in reversed(matches):
            result = result[:match] + new + result[match + length:]
    else:
        # 归一化只改空白/引号/破折号，不改行数；用行级 diff 把未变化行还原成原文。
        new_fuzzy = base
        for match, length, new, _ in reversed(matches):
            new_fuzzy = new_fuzzy[:match] + new + new_fuzzy[match + length:]
        old_lines = content.split("\n")
        fuzzy_lines = base.split("\n")
        new_lines = new_fuzzy.split("\n")
        if len(old_lines) != len(fuzzy_lines):
            raise CodeError("模糊匹配后行数不一致，拒绝写入；请改用精确文本")
        matcher = difflib.SequenceMatcher(None, fuzzy_lines, new_lines, autojunk=False)
        merged: list[str] = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                merged.extend(old_lines[i1:i2])
            else:
                merged.extend(new_lines[j1:j2])
        result = "\n".join(merged)

    if result == content:
        raise CodeError(f"{path} 没有发生变化；old_text 或 new_text 可能未命中")
    return result, _unified_diff(path, content, result)


class CodeSession:
    """一轮用户消息内的代码改动集合；preimage 落盘，undo 回滚整轮。"""

    def __init__(self) -> None:
        self.base_dir = config.changes_dir() / "code"
        self.turn_id: str | None = None
        self.turn_dir: Path | None = None
        self.files: dict[str, dict] = {}
        self.operations: list[dict] = []
        self.commands: list[dict] = []
        self.started: str | None = None

    def _ensure(self) -> None:
        if not self.turn_id:
            self.begin_turn()

    def begin_turn(self) -> None:
        if self.turn_id:
            self.end_turn()
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.turn_id = f"{stamp}-{uuid.uuid4().hex[:6]}"
        self.turn_dir = self.base_dir / self.turn_id
        self.turn_dir.mkdir(parents=True, exist_ok=True)
        self.files = {}
        self.operations = []
        self.commands = []
        self.started = _now()

    def record(self, path: str) -> None:
        self._ensure()
        target = _resolve(path)
        key = str(target).lower()
        if key in self.files:
            return
        if target.exists() and not target.is_file():
            raise CodeError(f"{path} 不是文件")
        if target.is_file():
            data = target.read_bytes()
            if self.turn_dir is None:
                raise CodeError("change set 未初始化")
            preimage = self.turn_dir / f"{len(self.files)}.preimage"
            preimage.write_bytes(data)
            self.files[key] = {"path": str(target), "existed": True,
                               "preimage": str(preimage),
                               "before_sha256": _sha256(data), "after_sha256": None}
        else:
            self.files[key] = {"path": str(target), "existed": False,
                               "preimage": None, "before_sha256": None, "after_sha256": None}

    def note_after(self, path: str) -> None:
        target = _resolve(path)
        info = self.files.get(str(target).lower())
        if info is None:
            return
        info["after_sha256"] = _sha256(target.read_bytes()) if target.is_file() else None

    def note_operation(self, tool: str, path: str, diff: str) -> None:
        self._ensure()
        self.operations.append({"ts": _now(), "tool": tool,
                                "path": str(_resolve(path)), "diff": diff})
        self.note_after(path)

    def command_log(self, command: str, cwd: str, output: str,
                    exit_code: int, timed_out: bool) -> Path:
        self._ensure()
        if self.turn_dir is None:
            raise CodeError("change set 未初始化")
        index = len(self.commands) + 1
        log_path = self.turn_dir / f"cmd-{index}.log"
        log_path.write_text(
            f"$ {command}\ncwd: {cwd}\nexit_code: {exit_code}\ntimeout: {timed_out}\n\n{output}",
            encoding="utf-8")
        self.commands.append({"ts": _now(), "command": command, "cwd": cwd,
                              "exit_code": exit_code, "timed_out": timed_out,
                              "log": str(log_path)})
        return log_path

    def end_turn(self) -> None:
        if not self.turn_id:
            return
        if self.turn_dir is None:
            self.turn_id = None
            return
        if not self.files and not self.operations and not self.commands:
            shutil.rmtree(self.turn_dir, ignore_errors=True)
        else:
            manifest = {"turn_id": self.turn_id, "started": self.started,
                        "ended": _now(), "files": list(self.files.values()),
                        "operations": self.operations, "commands": self.commands,
                        "undone": False}
            (self.turn_dir / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        self.turn_id = None
        self.turn_dir = None
        self.files = {}
        self.operations = []
        self.commands = []
        self.started = None

    def undo_last_turn(self) -> str:
        if not self.base_dir.exists():
            return ""
        manifests = sorted(self.base_dir.glob("*/manifest.json"),
                           key=lambda path: path.stat().st_mtime, reverse=True)
        for manifest_path in manifests:
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if manifest.get("undone"):
                continue
            notes: list[str] = []
            for info in reversed(manifest.get("files", [])):
                target = Path(info["path"])
                if info.get("existed"):
                    preimage = Path(info["preimage"]) if info.get("preimage") else None
                    if preimage is None or not preimage.is_file():
                        notes.append(f"跳过 {target}：底稿不在了")
                        continue
                    if target.is_file() and info.get("after_sha256") != _sha256(target.read_bytes()):
                        notes.append(f"跳过 {target}：之后被改过")
                        continue
                    try:
                        _atomic_write(target, preimage.read_bytes())
                        notes.append(f"已恢复 {target}")
                    except OSError as exc:
                        notes.append(f"没恢复 {target}：{type(exc).__name__}: {exc}")
                else:
                    if not target.is_file():
                        notes.append(f"{target} 已经不存在")
                        continue
                    if info.get("after_sha256") != _sha256(target.read_bytes()):
                        notes.append(f"跳过 {target}：之后被改过")
                        continue
                    try:
                        target.unlink()
                        notes.append(f"已删除新建的 {target}")
                    except OSError as exc:
                        notes.append(f"没删除 {target}：{type(exc).__name__}: {exc}")
            manifest["undone"] = True
            manifest["undone_at"] = _now()
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
            if manifest.get("commands"):
                notes.append("注意：命令产生的副作用不会回滚。")
            return "\n".join(notes) or "没有文件需要恢复。"
        return ""


def write_file(path: str, content, session: CodeSession) -> str:
    if not isinstance(content, str):
        raise CodeError("content 必须是字符串")
    target = _check_denied(path)
    if target.exists() and not target.is_file():
        raise CodeError(f"{path} 不是文件")
    old_bytes = target.read_bytes() if target.is_file() else None
    new_bytes = content.encode("utf-8")
    if old_bytes == new_bytes:
        return f"{path} 内容相同，未写。"
    session.record(str(target))
    _atomic_write(target, new_bytes)
    if old_bytes is None:
        diff = f"new file: {len(content)} chars"
    else:
        diff = _unified_diff(str(target), old_bytes.decode("utf-8", "replace"), content)
    session.note_operation("write_file", str(target), diff)
    return f"OK: wrote {target}\n{diff}"


def edit_file(path: str, edits, session: CodeSession) -> str:
    target = _check_denied(path)
    if not target.is_file():
        raise CodeError(f"{path} 不是文件（新文件用 write_file）")
    raw = target.read_bytes()
    has_bom, body = _split_bom(raw)
    text = body.decode("utf-8", "replace")
    if "\x00" in text:
        raise CodeError(f"{path} 看起来是二进制文件，拒绝按文本编辑")
    eol = _detect_eol(text)
    normalized = _normalize_lf(text)
    new_normalized, diff = _apply_edits(str(target), normalized, edits)
    final = (BOM if has_bom else b"") + _restore_eol(new_normalized, eol).encode("utf-8")
    if final == raw:
        return f"{path} 没有变化，未写。"
    session.record(str(target))
    _atomic_write(target, final)
    session.note_operation("edit_file", str(target), diff)
    count = len(edits) if isinstance(edits, list) else 1
    return f"OK: edited {target} ({count} block(s))\n{diff}"


def _shell_argv(command: str) -> list[str]:
    if os.name == "nt":
        bash = shutil.which("bash")
        if bash:
            return [bash, "-lc", command]
        shell = shutil.which("powershell") or shutil.which("pwsh")
        if shell:
            return [shell, "-NoProfile", "-Command", command]
        return [os.environ.get("COMSPEC", "cmd.exe"), "/c", command]
    return ["/bin/sh", "-lc", command]


def _kill_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            process.kill()
        except OSError:
            pass
        return
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except OSError:
        try:
            process.kill()
        except OSError:
            pass


def _tail(text: str) -> tuple[str, bool]:
    lines = text.splitlines()
    truncated = len(lines) > COMMAND_MAX_LINES
    if truncated:
        lines = lines[-COMMAND_MAX_LINES:]
    result = "\n".join(lines)
    if len(result.encode("utf-8")) > COMMAND_MAX_BYTES:
        result = result.encode("utf-8")[-COMMAND_MAX_BYTES:].decode("utf-8", "replace")
        truncated = True
    return result, truncated


def run_command(command: str, cwd: str | None, timeout, session: CodeSession) -> str:
    if not isinstance(command, str) or not command.strip():
        raise CodeError("command 不能为空")
    if timeout is None:
        timeout = COMMAND_DEFAULT_TIMEOUT
    try:
        seconds = float(timeout)
    except (TypeError, ValueError) as exc:
        raise CodeError("timeout 必须是数字") from exc
    if seconds <= 0 or seconds > COMMAND_MAX_TIMEOUT:
        raise CodeError(f"timeout 必须在 0-{COMMAND_MAX_TIMEOUT} 秒之间")
    cwd_path = _check_denied(cwd or os.getcwd())
    if not cwd_path.is_dir():
        raise CodeError(f"cwd 不是目录：{cwd_path}")
    low = command.lower().replace("\\", "/")
    if "platform-group-projects" in low:
        raise CodeError("命令触碰公司仓（D11），拒绝执行。")
    spaces = str(config.spaces_dir()).lower().replace("\\", "/")
    if spaces and spaces in low:
        raise CodeError("命令触碰 jmb 自身数据目录，拒绝执行。")

    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    started = time.monotonic()
    process = subprocess.Popen(
        _shell_argv(command), cwd=str(cwd_path), stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
    timed_out = False
    try:
        output, _ = process.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_tree(process)
        try:
            output, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            output = b""
    elapsed = time.monotonic() - started
    exit_code = -1 if timed_out else (process.returncode if process.returncode is not None else -1)
    text = output.decode("utf-8", "replace")
    tail, truncated = _tail(text)
    log_path = session.command_log(command, str(cwd_path), text, exit_code, timed_out)
    head = f"exit_code={exit_code} time={elapsed:.1f}s" + (" TIMEOUT" if timed_out else "")
    note = "\n[输出已截断]" if truncated else ""
    return f"{head}\n{tail}{note}\n[完整输出: {log_path}]"

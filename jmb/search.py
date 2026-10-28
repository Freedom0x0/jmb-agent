"""只读代码搜索（#4）：grep / find。

不起 shell、不需要 exec 授权；复用 grants 的 read 授权与 deny_reason。
输入路径和遍历中的每个文件/目录都过 deny_reason（公司仓、jmb spaces、.git）。
"""
from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path

from . import grants

IGNORED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv",
    "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache",
    "dist", "build", ".idea", ".vscode",
}
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_RESULTS = 200
MAX_OUTPUT_CHARS = 20000
MAX_LINE_CHARS = 500


class SearchError(RuntimeError):
    pass


def _resolve(path: str) -> Path:
    return Path(os.path.realpath(os.path.abspath(os.path.expanduser(path))))


def _allowed(path: Path) -> bool:
    return not grants.deny_reason(str(path))


def _iter_files(root: Path):
    if root.is_file():
        if _allowed(root):
            yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        base = Path(dirpath)
        dirnames[:] = sorted(
            name for name in dirnames
            if name not in IGNORED_DIRS and _allowed(base / name)
        )
        for name in sorted(filenames):
            file = base / name
            if _allowed(file):
                yield file


def _read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:4096]:
        return None
    return data.decode("utf-8", "replace")


def _limit(value, default: int = MAX_RESULTS) -> int:
    try:
        return max(1, min(int(value), 500))
    except (TypeError, ValueError):
        return default


def grep(pattern: str, path: str, glob: str | None = None,
         case_sensitive: bool = True, max_results: int = MAX_RESULTS) -> str:
    root = _resolve(path)
    if not root.exists():
        raise SearchError(f"{path} 不存在")
    reason = grants.deny_reason(str(root))
    if reason:
        raise SearchError(reason)
    try:
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)
    except re.error as exc:
        raise SearchError(f"正则不合法：{exc}") from exc
    limit = _limit(max_results)
    hits: list[str] = []
    truncated = False
    for file in _iter_files(root):
        if glob and not fnmatch.fnmatch(file.name, glob):
            continue
        text = _read_text(file)
        if text is None:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if regex.search(line):
                hits.append(f"{file}:{line_no}: {line[:MAX_LINE_CHARS]}")
                if len(hits) >= limit:
                    truncated = True
                    break
        if truncated:
            break
    if not hits:
        return f"没有匹配：{pattern}"
    output = "\n".join(hits)
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "\n...[grep 输出已截断]"
    if truncated:
        output += f"\n...[达到 max_results={limit}，可能还有更多]"
    return output


def find(path: str, name_pattern: str = "*", max_results: int = MAX_RESULTS) -> str:
    root = _resolve(path)
    if not root.exists():
        raise SearchError(f"{path} 不存在")
    reason = grants.deny_reason(str(root))
    if reason:
        raise SearchError(reason)
    pattern = name_pattern or "*"
    limit = _limit(max_results)
    hits: list[str] = []
    for file in _iter_files(root):
        if fnmatch.fnmatch(file.name, pattern):
            hits.append(str(file))
            if len(hits) >= limit:
                break
    if not hits:
        return f"没有找到：{pattern}"
    output = "\n".join(hits)
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "\n...[find 输出已截断]"
    if len(hits) >= limit:
        output += f"\n...[达到 max_results={limit}，可能还有更多]"
    return output

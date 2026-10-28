"""确定性写入器（spec §3.1 的"操作决策"通路）。

模型不许直接改文件——只许发 {op, target, payload, note}；这里校验、
存 preimage、落盘、记日志。这是 D21 那条"不可选规则"（可见/带时间线/可撤销）
的落地，也是 Phase 5 的真组件：Phase 5 只把"关于你的事实"那半接到 CF 的
issue/approve_confirmation 上，文件三件套就是这里这套，不会扔。

undo：弹栈恢复最近一次有 preimage 的改动。
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from . import config

OPS = {"ADD", "UPDATE"}  # DELETE/NONE 一期原型不支持，明确拒绝而不是静默

_TARGETS: dict[str, object] = {
    "RELATIONSHIP.md": config.persona_dir,
    "interests.md": config.persona_dir,
    "LEARNING.md": config.ledger_dir,
}


def _log_path() -> Path:
    return config.changes_dir() / "log.jsonl"


def apply(decision: dict) -> str:
    """执行一条操作决策。返回给模型的回执文本（拒绝也要说明白）。"""
    op = decision.get("op")
    target = decision.get("target")
    payload = decision.get("payload")
    if op not in OPS:
        return f"拒绝：op 只支持 ADD/UPDATE（原型不受理 {op!r}）。"
    if target not in _TARGETS:
        return f"拒绝：target 只许 {sorted(_TARGETS)}，SOUL.md 永远只读，收到 {target!r}。"
    if not isinstance(payload, str) or not payload.strip():
        return "拒绝：payload 不能为空。"

    path = _TARGETS[target]() / target
    path.parent.mkdir(parents=True, exist_ok=True)
    config.changes_dir().mkdir(parents=True, exist_ok=True)

    preimage: Path | None = None
    if path.exists():
        stamp = datetime.now().strftime("%H%M%S-%f")
        preimage = config.changes_dir() / f"{target}.{stamp}.preimage"
        shutil.copyfile(path, preimage)

    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)

    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "op": op,
        "target": target,
        "preimage": str(preimage) if preimage else None,
        "source_tag": "it_summarized",
        "undone": False,
    }
    with _log_path().open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return f"OK：已写入 {target}（op={op}，{len(payload)} 字）"


def undo() -> str:
    """撤回最近一次自我改写（弹栈）。没有 preimage 的首次创建撤不了——如实说。"""
    log = _log_path()
    if not log.is_file():
        return "没有可撤的改动。"
    entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
    for entry in reversed(entries):
        if entry.get("undone") or not entry.get("preimage"):
            continue
        pre = Path(entry["preimage"])
        if not pre.is_file():
            continue
        path = _TARGETS[entry["target"]]() / entry["target"]
        shutil.copyfile(pre, path)
        entry["undone"] = True
        with log.open("w", encoding="utf-8") as fh:
            for e in entries:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
        return f"已撤回对 {entry['target']} 的最近一次改动（文件回到改前）。"
    return "没有可撤的改动（能撤的都撤过了，或最近那次是首次创建、没有底稿）。"

"""稳定前缀装配 + 工具表（spec §5.3，2026-10-27 评审后的顺序）。

顺序纪律：越稳定的越靠前。工具定义在 API 参数层（最稳），system 内
SOUL → LEARNING → RELATIONSHIP → interests → surface。
原型阶段三个记录文件都是原文进前缀——原文本身就是确定性的；等文件变大
再上 spec 说的"按文件 hash 缓存的摘要"，不提前造。
"""
from __future__ import annotations

from pathlib import Path

from . import config

_SURFACE = (
    "当前入口 surface=desktop（终端原型）。可用能力：服务端联网搜索；"
    "经 update_self_file 工具维护你自己的三个记录文件；"
    "read_code / grep / find 读他的代码（白名单/逐路径授权）；write_file / edit_file 写改代码"
    "（首次写会请求本会话写授权）；run_command 执行命令（默认 Docker 沙箱，首次执行会请求"
    "本会话执行授权，命令副作用不能 undo）。收到 [系统事件] 时以事件为准；"
    "用户撤销后的文件现状要重新 read_code 确认。写 Obsidian 文档：原型未开放，他要求时如实说还没做。"
)

# 工具列表是模块常量（deterministic order 以利缓存，spec §4）。
# max_uses=3 是 spec §5.6 的目标值。⚠️ 2026-10-27 实测（scripts/probe_maxuses.py）：
# 这条线路**忽略 max_uses**（声明 1 实搜 2）⇒ 轮数上限只能靠客户端预算闸门（chat._enforce_budget）。
WEB_SEARCH = {"type": "web_search_20250305", "name": "web_search", "max_uses": 3}

UPDATE_SELF_FILE = {
    "name": "update_self_file",
    "description": (
        "改你自己的记录文件（不是他的文件，SOUL.md 永远只读）："
        "RELATIONSHIP.md=对相处的总结（短句规则一行一条）、"
        "interests.md=他表过兴趣的东西（名称+地址+日期）、"
        "LEARNING.md=学习进度（主题 | 日期 | 学到哪 | 下次从哪继续）。"
        "只在出现具体、可复用的事实时用，一次调用改一条；payload 是该文件的完整新内容（整文件替换，记得保留原有各行）。"
        "不许记情绪数值、不推断性格、不记公司项目相关内容。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["ADD", "UPDATE"],
                   "description": "新内容替换整份文件时用 UPDATE；原文件还是占位符时用 ADD"},
            "target": {"type": "string", "enum": ["RELATIONSHIP.md", "interests.md", "LEARNING.md"]},
            "payload": {"type": "string", "description": "写入的完整新文件内容（utf-8 文本）"},
            "note": {"type": "string", "description": "一句话说明这次改了什么（会原样转告给他）"},
        },
        "required": ["op", "target", "payload"],
    },
}

def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def build_system() -> str:
    parts = [
        _read(config.persona_dir() / "SOUL.md"),
        _read(config.ledger_dir() / "LEARNING.md"),
        _read(config.persona_dir() / "RELATIONSHIP.md"),
        _read(config.persona_dir() / "interests.md"),
        _SURFACE,
    ]
    return "\n\n---\n\n".join(p.strip() for p in parts if p.strip())

"""jmb 的路径与凭据解析——唯一出处。

spec §3 的目录契约在这里落成函数；模型/端点/凭据只从一个出处读：
jmb 自己的 config.json（D49：不读 shell env，不碰 Claude Code 的
~/.claude/settings.json——改 jmb 的模型不影响 Claude Code）。
这里只解析，不打印——任何输出（只报长度、不回显）由 cli 决定。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DEFAULT_BASE_URL = "https://api.deepseek.com/anthropic"
DEFAULT_MODEL = "deepseek-flash"


def jmb_home() -> Path:
    """jmb 的家：%LOCALAPPDATA%\\jmb\\（spec §8 待你改清单里的一条，可用 JMB_HOME 覆盖）。"""
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / "AppData" / "Local"
    override = os.environ.get("JMB_HOME")
    return Path(override) if override else root / "jmb"


def spaces_dir() -> Path:
    """owner 一期的唯一值是 local，但这层目录必须存在（D13 口子 2）。"""
    return jmb_home() / "spaces" / "local"


def persona_dir() -> Path:
    return spaces_dir() / "persona"


def sessions_dir() -> Path:
    return spaces_dir() / "sessions"


def grants_path() -> Path:
    return spaces_dir() / "grants.json"


def ledger_dir() -> Path:
    return spaces_dir() / "ledger"


def changes_dir() -> Path:
    """自我改写的 preimage 副本 + 变更日志（spec §3 的 changes/）。"""
    return spaces_dir() / "changes"


def forge_home() -> Path:
    """jmb 自己那套 Context Forge 实例的家：memory.db 在 spaces/<owner>/ 里面（spec §3）。"""
    return spaces_dir() / "forge"


def brief_state_path(day: date) -> Path:
    """Phase 7 日报的幂等标记，一天一个文件（D30：错过不补，无开机触发器）。"""
    return jmb_home() / "state" / f"brief-{day.isoformat()}.json"


def model_config_path() -> Path:
    """jmb 自己的模型/凭据配置（env 与 ~/.claude/settings.json 之外的第三层）。"""
    return jmb_home() / "config.json"


def load_model_config() -> dict:
    try:
        data = json.loads(model_config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_model_config(model: str, base_url: str, token: str) -> None:
    """只写非空字段（留空=保持不变），保留文件里的其它键。key 明文落盘，不回显。"""
    data = load_model_config()
    for key, value in (("model", model), ("base_url", base_url), ("token", token)):
        if value:
            data[key] = value
    path = model_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass(frozen=True)
class Resolved:
    value: str
    source: str


def resolve_token() -> Resolved:
    """模型凭据。只认 jmb/config.json（D49：不读环境变量，不碰 Claude Code 的设置）。

    调用方只许用 len()，不许打印 value。
    """
    value = load_model_config().get("token", "")
    if value:
        return Resolved(value, "jmb/config.json")
    return Resolved("", "missing")


def resolve_base_url() -> Resolved:
    value = load_model_config().get("base_url", "")
    if value:
        return Resolved(value, "jmb/config.json")
    return Resolved(DEFAULT_BASE_URL, "default")


def resolve_model() -> Resolved:
    value = load_model_config().get("model", "")
    if value:
        return Resolved(value, "jmb/config.json")
    return Resolved(DEFAULT_MODEL, "default")

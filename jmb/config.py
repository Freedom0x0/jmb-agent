"""jmb 的路径与凭据解析——唯一出处。

spec §3 的目录契约在这里落成函数；凭据解析照 scripts/probe_websearch.py
验证过的顺序：先 shell env，缺则读 ~/.claude/settings.json 的 env 段。
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
CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"


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


@dataclass(frozen=True)
class Resolved:
    value: str
    source: str


def _settings_env() -> dict[str, str]:
    """~/.claude/settings.json 的 env 段。读不到/解析失败就当空——doctor 会如实报。"""
    try:
        data = json.loads(CLAUDE_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    env = data.get("env") if isinstance(data, dict) else None
    if not isinstance(env, dict):
        return {}
    return {str(k): str(v) for k, v in env.items() if isinstance(v, str)}


def resolve_token() -> Resolved:
    """模型凭据。调用方只许用 len()，不许打印 value。"""
    for name in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY"):
        value = os.environ.get(name, "")
        if value:
            return Resolved(value, f"env:{name}")
    env = _settings_env()
    for name in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY"):
        value = env.get(name, "")
        if value:
            return Resolved(value, f"settings.json:env:{name}")
    return Resolved("", "missing")


def resolve_base_url() -> Resolved:
    value = os.environ.get("ANTHROPIC_BASE_URL", "")
    if value:
        return Resolved(value, "env:ANTHROPIC_BASE_URL")
    value = _settings_env().get("ANTHROPIC_BASE_URL", "")
    if value:
        return Resolved(value, "settings.json:env:ANTHROPIC_BASE_URL")
    return Resolved(DEFAULT_BASE_URL, "default")


def resolve_model() -> Resolved:
    value = os.environ.get("ANTHROPIC_MODEL", "")
    if value:
        return Resolved(value, "env:ANTHROPIC_MODEL")
    value = _settings_env().get("ANTHROPIC_MODEL", "")
    if value:
        return Resolved(value, "settings.json:env:ANTHROPIC_MODEL")
    return Resolved(DEFAULT_MODEL, "default")


def raw_model_values() -> tuple[str, str]:
    """env 与 settings.json 里各自的原始模型名。

    spec §6 那个未解之谜（探针实际用 deepseek-flash[1M]，settings 写 deepseek-flash，
    谁覆盖谁没查清）要靠把两个来源摆在一起对照才能解。
    """
    return os.environ.get("ANTHROPIC_MODEL", ""), _settings_env().get("ANTHROPIC_MODEL", "")

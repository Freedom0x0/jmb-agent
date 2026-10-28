"""探针：DeepSeek 这条线路认不认 web_search 的 max_uses（Phase 3 验收 5）。

跑法：uv run python scripts/probe_maxuses.py
判读：usage.server_tool_use.web_search_requests > max_uses ⇒ 端点忽略该参数
⇒ 轮数上限只能靠客户端闸门；=或< ⇒ 认。
"""
from __future__ import annotations

import json
import os
import pathlib
import urllib.request

BASE = os.environ.get("ANTHROPIC_BASE_URL", "")
TOKEN = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
MODEL = os.environ.get("ANTHROPIC_MODEL", "")
if not TOKEN or not MODEL:
    cfg = json.loads((pathlib.Path.home() / ".claude/settings.json").read_text(encoding="utf-8"))
    env = cfg.get("env", {})
    TOKEN = TOKEN or env.get("ANTHROPIC_AUTH_TOKEN", "")
    MODEL = MODEL or env.get("ANTHROPIC_MODEL", "deepseek-flash")
    BASE = BASE or env.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")

req = urllib.request.Request(
    f"{BASE}/v1/messages",
    data=json.dumps({
        "model": MODEL, "max_tokens": 1024,
        "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 1}],
        "messages": [{"role": "user",
                      "content": "分别查出 FastAPI 和 Flask 当前最新的版本号，两个都要查。"}],
    }).encode(),
    headers={"content-type": "application/json", "authorization": f"Bearer {TOKEN}"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=300) as resp:
    body = json.loads(resp.read().decode())
usage = body.get("usage", {})
searches = (usage.get("server_tool_use") or {}).get("web_search_requests", 0)
print(f"model={MODEL}")
print(f"max_uses=1 声明下实际 web_search_requests = {searches}")
print("结论：端点" + ("认 max_uses（≤1）" if searches <= 1 else "忽略 max_uses（>1）⇒ 轮数上限要靠客户端闸门"))

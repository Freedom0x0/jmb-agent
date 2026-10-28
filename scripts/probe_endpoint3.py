"""第三批：补 A4（稳定前缀 + 变化的用户话）与 D（tool_result.is_error 是否被忽略）。"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")
TOKEN = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")

PREFIX = (
    "You are a study companion. The following block is a stable persona and "
    "memory index. It is re-sent on every turn without modification.\n"
) + (
    "Section. The companion keeps a ledger of what the learner got wrong before, "
    "re-reads it at the start of each session, and asks recall questions first. "
) * 70

TOOLS = [{
    "name": "record_session",
    "description": "Record that a study session happened for a topic.",
    "input_schema": {"type": "object", "properties": {
        "topic": {"type": "string"}, "minutes": {"type": "integer"}},
        "required": ["topic", "minutes"]},
}]
SYS_D = "If a tool result is marked is_error, apologize and reply with exactly the word FAILED."


def post(body: dict):
    req = urllib.request.Request(
        f"{BASE}/v1/messages",
        data=json.dumps(body).encode("utf-8"),
        headers={"content-type": "application/json", "anthropic-version": "2023-06-01",
                 "authorization": f"Bearer {TOKEN}"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")[:400].replace(TOKEN, "<R>")
    except Exception as exc:  # noqa: BLE001
        return "EXC", f"{type(exc).__name__}: {exc}"[:200]


def line(label, status, j):
    if isinstance(j, dict):
        u = j.get("usage", {})
        print(f"{label}: HTTP {status} | input={u.get('input_tokens')} "
              f"cache_read={u.get('cache_read_input_tokens')} output={u.get('output_tokens')} "
              f"stop={j.get('stop_reason')}")
    else:
        print(f"{label}: HTTP {status} | {str(j)[:220]}")


print("=== A4 稳定 system 前缀 + 每轮换不同的用户话（这才是真实用法）===")
for k, q in enumerate(["今天学了什么？", "帮我出两道复习题", "我有点累，少安排点"]):
    st, j = post({"model": "deepseek-flash", "max_tokens": 4, "system": PREFIX,
                  "messages": [{"role": "user", "content": q}]})
    line(f"A4#{k+1} 用户话={q}", st, j)

print("\n=== D tool_result.is_error 到底有没有被读到 ===")
st, first = post({"model": "deepseek-flash", "max_tokens": 200,
                  "system": SYS_D + " You have tools; call record_session when asked to log.",
                  "messages": [{"role": "user", "content": "Log 25 minutes of recursion."}],
                  "tools": TOOLS})
blocks = first.get("content", []) if isinstance(first, dict) else []
tool_use = next((b for b in blocks if b.get("type") == "tool_use"), None)
thinking = next((b for b in blocks if b.get("type") == "thinking"), None)
print(f"D0 首轮 blocks={[b.get('type') for b in blocks]}"
      + (f" | thinking 键={sorted(thinking.keys())}" if thinking else ""))

if tool_use:
    for label, extra in (("D1 带 is_error:true", {"is_error": True}), ("D2 不带 is_error", {})):
        tr = {"type": "tool_result", "tool_use_id": tool_use["id"], "content": "disk full"}
        tr.update(extra)
        st, j = post({"model": "deepseek-flash", "max_tokens": 40,
                      "system": SYS_D + " You have tools; call record_session when asked to log.",
                      "messages": [{"role": "user", "content": "Log 25 minutes of recursion."},
                                   {"role": "assistant", "content": blocks},
                                   {"role": "user", "content": [tr]}],
                      "tools": TOOLS})
        line(label, st, j)
        if isinstance(j, dict):
            texts = [b.get("text", "") for b in j.get("content", []) if b.get("type") == "text"]
            print(f"     输出={json.dumps(texts, ensure_ascii=False)[:200]}")
else:
    print("D: 首轮没拿到 tool_use，跳过")

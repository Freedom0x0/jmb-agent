"""第二批端点探针：钉死三件设计前提。会产生真实模型调用。

跑法： py -3.13 -X utf8 scripts/probe_endpoint2.py
"""
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


def post(body: dict):
    req = urllib.request.Request(
        f"{BASE}/v1/messages",
        data=json.dumps(body).encode("utf-8"),
        headers={"content-type": "application/json", "anthropic-version": "2023-06-01",
                 "authorization": f"Bearer {TOKEN}"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        if TOKEN:
            raw = raw.replace(TOKEN, "<REDACTED>")
        return exc.code, raw[:400]
    except Exception as exc:  # noqa: BLE001
        return "EXC", f"{type(exc).__name__}: {exc}"[:300]


def show(label: str, status, j: dict) -> None:
    if isinstance(j, dict):
        u = j.get("usage", {})
        print(f"{label}: HTTP {status} | input={u.get('input_tokens')} "
              f"cache_read={u.get('cache_read_input_tokens')} "
              f"cache_write={u.get('cache_creation_input_tokens')} "
              f"output={u.get('output_tokens')} stop={j.get('stop_reason')}")
    else:
        print(f"{label}: HTTP {status} | {str(j)[:240]}")


print(f"BASE={BASE}  前缀字符数={len(PREFIX)}")

print("\n=== A. 前缀稳定位置对命中的影响（每个都连打两次，取第二次）===")
cases = {
    "A1 全稳定": PREFIX,
    "A2 只改结尾一个词": PREFIX.rstrip() + " EXTRA",
    "A3 只改开头一个词": "ZZZ " + PREFIX,
    "A4 稳定前缀 + 每轮都变的用户话": PREFIX,
}
for label, sys_text in cases.items():
    if label == "A3 只改开头一个词":
        # 先建立一个全稳定基线，再改开头，看命中是否归零
        post({"model": "deepseek-flash", "max_tokens": 4, "system": PREFIX,
              "messages": [{"role": "user", "content": "ping"}]})
    for i in range(2):
        st, j = post({"model": "deepseek-flash", "max_tokens": 4, "system": sys_text,
                      "messages": [{"role": "user", "content": f"ping"} if label != "A4 稳定前缀 + 每轮都变的用户话" else f"问句 {i} 换个说法"]})
        show(f"{label} #{i+1}", st, j)

print("\n=== B. count_tokens 带完整 body 是否存在 ===")
req = urllib.request.Request(
    f"{BASE}/v1/messages/count_tokens",
    data=json.dumps({"model": "deepseek-flash",
                     "system": PREFIX,
                     "messages": [{"role": "user", "content": "ping"}],
                     "tools": TOOLS}).encode("utf-8"),
    headers={"content-type": "application/json", "anthropic-version": "2023-06-01",
             "authorization": f"Bearer {TOKEN}"}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8", "replace"))
        print(f"B: HTTP {resp.status} | {json.dumps(body, ensure_ascii=False)[:200]}")
except urllib.error.HTTPError as exc:
    print(f"B: HTTP {exc.code} | {exc.read().decode('utf-8','replace')[:300]}")
except Exception as exc:  # noqa: BLE001
    print(f"B: EXC {exc}")

print("\n=== C. 多轮工具回传：thinking 块带回去 vs 丢掉 ===")
st, first = post({"model": "deepseek-flash", "max_tokens": 200,
                  "system": "You have tools. Always call record_session when asked to log.",
                  "messages": [{"role": "user", "content": "I studied recursion for 25 minutes. Log it."}],
                  "tools": TOOLS})
blocks = first.get("content", []) if isinstance(first, dict) else []
print(f"C0 首轮: HTTP {st} | blocks={[b.get('type') for b in blocks]}")

tool_use = next((b for b in blocks if b.get("type") == "tool_use"), None)
thinking = next((b for b in blocks if b.get("type") == "thinking"), None)

if tool_use:
    tool_result_msg = {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tool_use["id"], "content": "saved"}]}

    with_thinking = [b for b in blocks]
    st, j = post({"model": "deepseek-flash", "max_tokens": 64,
                  "system": "You have tools. Always call record_session when asked to log.",
                  "messages": [{"role": "user", "content": "I studied recursion for 25 minutes. Log it."},
                               {"role": "assistant", "content": with_thinking},
                               tool_result_msg],
                  "tools": TOOLS})
    show("C1 第二轮·把 thinking 原样带回去", st, j)

    without_thinking = [b for b in blocks if b.get("type") != "thinking"]
    st, j = post({"model": "deepseek-flash", "max_tokens": 64,
                  "system": "You have tools. Always call record_session when asked to log.",
                  "messages": [{"role": "user", "content": "I studied recursion for 25 minutes. Log it."},
                               {"role": "assistant", "content": without_thinking},
                               tool_result_msg],
                  "tools": TOOLS})
    show("C2 第二轮·丢掉 thinking", st, j)
    if thinking:
        print(f"    (首轮 thinking 类型键={sorted(thinking.keys())}, 长度={len(str(thinking))})")

print("\n=== D. tool_result.is_error 被忽略会不会改变模型行为 ===")
if tool_use:
    err_msg = {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tool_use["id"], "content": "boom", "is_error": True}]}
    st, j = post({"model": "deepseek-flash", "max_tokens": 64,
                  "system": "If a tool result says is_error, apologize and say the word FAILED.",
                  "messages": [{"role": "user", "content": "Log it."},
                               {"role": "assistant", "content": blocks}, err_msg],
                  "tools": TOOLS})
    show("D", st, j)
    if isinstance(j, dict):
        texts = [b.get("text", "") for b in j.get("content", []) if b.get("type") == "text"]
        print(f"    模型输出={json.dumps(texts, ensure_ascii=False)[:300]}")

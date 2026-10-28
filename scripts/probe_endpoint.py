"""一次性端点探针：只读，不写库，不外传任何文件内容。

跑法： py -3.13 -X utf8 scripts/probe_endpoint.py
用途：把两条文档答不了的事实变成实测数字。会产生真实模型调用。
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")
TOKEN = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
VERSION = "2023-06-01"

# 一段固定的长前缀，用来测自动前缀缓存：两次请求的 system 必须逐字节一致。
PREFIX = (
    "You are a study companion. The following block is a stable persona and "
    "memory index. It is re-sent on every turn without modification.\n"
) + (
    "Section. The companion keeps a ledger of what the learner got wrong before, "
    "re-reads it at the start of each session, and asks recall questions first. "
) * 70


def redact(text: str) -> str:
    if TOKEN:
        text = text.replace(TOKEN, "<REDACTED>")
    return text


def call(model: str, auth_mode: str, *, system: str, text: str, max_tokens: int = 4,
         tools: list | None = None, expect: str = "json") -> dict:
    url = f"{BASE}/v1/messages"
    if expect == "count":
        url = f"{BASE}/v1/messages/count_tokens"
    body: dict = {"model": model, "max_tokens": max_tokens}
    if expect != "count":
        body["messages"] = [{"role": "user", "content": text}]
        if system:
            body["system"] = system
    if tools:
        body["tools"] = tools
    payload = json.dumps(body).encode("utf-8")

    headers = {"content-type": "application/json", "anthropic-version": VERSION}
    if auth_mode == "bearer":
        headers["authorization"] = f"Bearer {TOKEN}"
    else:
        headers["x-api-key"] = TOKEN

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    out: dict = {"model": model, "auth": auth_mode, "url": url}
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode("utf-8", "replace")
            out["status"] = resp.status
            out["headers"] = {k.lower(): v for k, v in resp.getheaders()
                              if any(t in k.lower() for t in ("cache", "x-ds", "request-id", "token"))}
            try:
                out["json"] = json.loads(raw)
            except json.JSONDecodeError:
                out["raw"] = redact(raw)[:300]
    except urllib.error.HTTPError as exc:
        out["status"] = exc.code
        out["error"] = redact(exc.read().decode("utf-8", "replace"))[:400]
    except Exception as exc:  # noqa: BLE001
        out["status"] = "EXC"
        out["error"] = redact(f"{type(exc).__name__}: {exc}")[:300]
    return out


def summarize(label: str, res: dict) -> None:
    status = res.get("status")
    if isinstance(res.get("json"), dict):
        j = res["json"]
        usage = j.get("usage")
        model_ret = j.get("model")
        stop = j.get("stop_reason")
        print(f"{label}: HTTP {status} | model={model_ret} | stop={stop} | usage={json.dumps(usage, ensure_ascii=False)}")
        if res.get("headers"):
            print(f"    headers={json.dumps(res['headers'], ensure_ascii=False)}")
    else:
        err = (res.get("error") or res.get("raw") or "").replace("\n", " ")
        print(f"{label}: HTTP {status} | {err[:260]}")


print(f"BASE={BASE}  token_len={len(TOKEN)}")

print("\n=== A. 模型名 × 认证方式（每次 max_tokens=4）===")
for model in ("deepseek-flash", "deepseek-flash[1m]", "deepseek-flash[1M]", "deepseek-v4-pro"):
    r = call(model, "bearer", system="Reply with the single word ok.", text="ping")
    summarize(f"A bearer {model}", r)

r = call("deepseek-flash", "x-api-key", system="Reply with the single word ok.", text="ping")
summarize("A x-api-key deepseek-flash", r)

print("\n=== B. 自动前缀缓存：同一前缀连打三次 ===")
for i in range(1, 4):
    r = call("deepseek-flash", "bearer", system=PREFIX, text="ping")
    summarize(f"B#{i}", r)
    if i == 1 and isinstance(r.get("json"), dict):
        print(f"    前缀字符数={len(PREFIX)}  顶层键={sorted(r['json'].keys())}")

print("\n=== C. count_tokens 端点是否存在（决定能不能做本地预算闸门）===")
r = call("deepseek-flash", "bearer", system=PREFIX, text="ping", expect="count")
if isinstance(r.get("json"), dict):
    print(f"C: HTTP {r['status']} | usage={json.dumps(r['json'].get('usage'), ensure_ascii=False)}")
else:
    summarize("C", r)

print("\n=== D. 工具调用是否真能用（agent 循环的前提）===")
tools = [{
    "name": "record_session",
    "description": "Record that a study session happened for a topic.",
    "input_schema": {"type": "object", "properties": {
        "topic": {"type": "string"}, "minutes": {"type": "integer"}},
        "required": ["topic", "minutes"]},
}]
r = call("deepseek-flash", "bearer", system="You have tools. Always call record_session when asked.",
         text="I studied recursion for 25 minutes. Log it.", max_tokens=200, tools=tools)
if isinstance(r.get("json"), dict):
    j = r["json"]
    print(f"D: HTTP {r['status']} | stop={j.get('stop_reason')} | usage={json.dumps(j.get('usage'), ensure_ascii=False)}")
    kinds = [b.get("type") for b in j.get("content", [])]
    print(f"    content blocks={kinds}")
    for b in j.get("content", []):
        if b.get("type") == "tool_use":
            print(f"    tool_use name={b.get('name')} input={json.dumps(b.get('input'), ensure_ascii=False)}")
else:
    summarize("D", r)

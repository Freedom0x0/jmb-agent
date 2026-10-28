"""探针：DeepSeek /anthropic 端点上的服务端 Web Search 到底怎么声明、返回什么形状。
只发几次最小请求。不发送任何本机文件内容或个人信息，问题都是公开事实类。
跑法：py -3.13 -X utf8 scripts/probe_websearch.py
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")
TOKEN = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
MODEL = os.environ.get("ANTHROPIC_MODEL", "deepseek-flash")

# 这个 shell 不一定继承了那三个变量（上一批探针时 ANTHROPIC_AUTH_TOKEN 长度=35，本次=0）。
# 退化路径：从 ~/.claude/settings.json 的 env 段读。只读，绝不打印值。
if not TOKEN or MODEL == "deepseek-flash" and not os.environ.get("ANTHROPIC_MODEL"):
    try:
        import pathlib

        cfg = json.loads(pathlib.Path.home().joinpath(".claude/settings.json").read_text(encoding="utf-8"))
        env = cfg.get("env", {}) if isinstance(cfg, dict) else {}
        TOKEN = TOKEN or env.get("ANTHROPIC_AUTH_TOKEN", "") or env.get("ANTHROPIC_API_KEY", "")
        BASE = os.environ.get("ANTHROPIC_BASE_URL") or env.get("ANTHROPIC_BASE_URL", BASE)
        MODEL = os.environ.get("ANTHROPIC_MODEL") or env.get("ANTHROPIC_MODEL", MODEL)
        print("凭据来源：settings.json 的 env 段" if not os.environ.get("ANTHROPIC_AUTH_TOKEN") else "凭据来源：shell env")
    except Exception as exc:  # noqa: BLE001
        print(f"读 settings.json 失败：{type(exc).__name__}: {exc}")

# 需要新鲜信息、且必然要查的问题（公开事实，不含任何本机内容）
QUESTION = "What is the latest released version of the Python package 'mcp' on PyPI? Check the web."


def post(body: dict, extra_headers: dict | None = None):
    h = {"content-type": "application/json", "anthropic-version": "2023-06-01",
         "authorization": f"Bearer {TOKEN}"}
    if extra_headers:
        h.update(extra_headers)
    req = urllib.request.Request(f"{BASE}/v1/messages", data=json.dumps(body).encode("utf-8"),
                                 headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        return exc.code, raw.replace(TOKEN, "<REDACTED>")[:600] if TOKEN else raw[:600]
    except Exception as exc:  # noqa: BLE001
        return "EXC", f"{type(exc).__name__}: {exc}"[:300]


def report(label: str, status, j) -> None:
    print(f"\n--- {label} ---")
    if not isinstance(j, dict):
        print(f"HTTP {status}\n{j}")
        return
    blocks = j.get("content", [])
    kinds = [b.get("type") for b in blocks]
    print(f"HTTP {status} | stop={j.get('stop_reason')} | blocks={kinds}")
    print(f"usage={json.dumps(j.get('usage'), ensure_ascii=False)}")
    for b in blocks:
        t = b.get("type")
        if t in ("server_tool_use",):
            print(f"  [{t}] id={b.get('id')} name={b.get('name')} input={json.dumps(b.get('input'), ensure_ascii=False)[:200]}")
        elif t in ("web_search_tool_result",):
            res = b.get("content") or b.get("results")
            print(f"  [{t}] 顶层键={sorted(b.keys())}")
            if isinstance(res, list):
                print(f"      结果条数={len(res)} | 首条键={sorted(res[0].keys()) if res and isinstance(res[0], dict) else res[:1]}")
                for r in (res or [])[:2]:
                    if isinstance(r, dict):
                        print(f"      样本 url={str(r.get('url'))[:70]} title={str(r.get('title'))[:40]} "
                              f"页码字段={[k for k in r if 'page' in k or 'enc' in k]}")
                        print(f"        内容片段={str(r.get('content') or r.get('description') or '')[:160]}")
            else:
                print(f"      content 字段类型={type(res).__name__} 值前 160={str(res)[:160]}")
        elif t == "text":
            print(f"  [text] {str(b.get('text'))[:220]}")
        elif t == "thinking":
            print(f"  [thinking] 长度={len(str(b.get('thinking')))}")


print(f"BASE={BASE} MODEL={MODEL} token_len={len(TOKEN)}")

# A: Anthropic 官方的服务端搜索类型串
post_a_body = {"model": MODEL, "max_tokens": 1024,
               "tools": [{"type": "web_search_20250305", "name": "web_search"}],
               "messages": [{"role": "user", "content": QUESTION}]}
st, j = post(post_a_body)
report("A tools=[{type:web_search_20250305,name:web_search}]", st, j)

# B: 不带 max_tokens 之外差异，只把 name 去掉（有些实现靠 type 默认 name）
st, j = post({"model": MODEL, "max_tokens": 1024,
              "tools": [{"type": "web_search_20250305"}],
              "messages": [{"role": "user", "content": QUESTION}]})
report("B tools=[{type:web_search_20250305}] 无 name", st, j)

# C: 加 beta 头再试一次（我们已测过 anthropic-beta 被忽略，这里验证"加了也不 hurt"）
st, j = post(post_a_body, {"anthropic-beta": "web-search-2025-03-05"})
report("C 同 A 但带 anthropropic-beta 头", st, j)

# D: 对照组——完全不声明搜索工具，看它会不会自己查
st, j = post({"model": MODEL, "max_tokens": 512,
              "messages": [{"role": "user", "content": QUESTION}]})
report("D 对照：不声明任何工具", st, j)

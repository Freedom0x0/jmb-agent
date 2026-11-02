"""复现用户端看到的 10404 "No Available Source"（iFLYTEK MaaS 端点）。

最小对照：同一 endpoint，model 带 [1M] 后缀 vs 不带；是否带 system/tools。
max_retries=0，错误立即上抛。token 只打印长度。
"""
from __future__ import annotations

from anthropic import Anthropic

from jmb import config

token = config.resolve_token()
base = config.resolve_base_url()
model_env = config.resolve_model()
print(f"base   = {base.value}  ({base.source})")
print(f"model  = {model_env.value}  ({model_env.source})")
print(f"token  = len {len(token.value)}  ({token.source})")

client = Anthropic(base_url=base.value, auth_token=token.value,
                   timeout=30.0, max_retries=0)

system = "你是江慕白。"
tools = [{
    "name": "record_session",
    "description": "Record that a study session happened for a topic.",
    "input_schema": {"type": "object",
                     "properties": {"topic": {"type": "string"}},
                     "required": ["topic"]},
}]


def probe(label: str, **kwargs) -> None:
    try:
        r = client.messages.create(**kwargs)
        text = "".join(b.text for b in r.content if b.type == "text")
        print(f"OK   {label}: {text[:60]!r}")
    except Exception as exc:  # noqa: BLE001
        print(f"ERR  {label}: {type(exc).__name__}: {str(exc)[:300]}")


for model in (model_env.value, "spark-x2.6"):
    probe(f"plain        | {model}",
          model=model, max_tokens=64,
          messages=[{"role": "user", "content": "ping"}])
    probe(f"system+tools | {model}",
          model=model, max_tokens=64, system=system, tools=tools,
          messages=[{"role": "user", "content": "ping"}])

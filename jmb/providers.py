"""声明式 provider 表 + 两条传输（spec §5.1 / D29）。

设计边界（照 spec 的抽象位置）：
- 请求侧形状差异各 provider 一小段（这里：anthropic 传输 / openai 传输）；
  结果侧 jmb 只认自己的形状（Turn.blocks / usage / stop_reason）。
- 服务端 web_search 是 Anthropic 系的 server tool；OpenAI 线没有 ⇒ chat 按
  profile 声明换成客户端 search_web 工具（Bing 兜底，spec §5.4 第二层）。
- thinking：真 Anthropic 在 thinking 模式必须原样回传；DeepSeek 这条线路实测
  带回/丢都 200 且白送 ⇒ 由 profile 的两个开关决定，不许写死。
- 切 provider = 换 profile（JMB_PROVIDER env），chat 循环零改动（Phase 2 验收 5）。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from . import config


@dataclass(frozen=True)
class ProviderProfile:
    name: str
    protocol: str            # "anthropic" | "openai"
    base_url: str
    model: str
    supports_server_web_search: bool = False
    echo_thinking_required: bool = False   # True = 真 Anthropic thinking 必须回传
    allow_thinking_drop: bool = True       # 预算闸门能不能丢老轮次的 thinking 块
    context_window: int = 128_000          # 模型窗口；预算按它算，不写死 30k
    input_budget: int = 30_000             # 软预算（system+tools+history）
    max_output_tokens: int = 8192          # 单次回复上限；thinking 也算在里面


def budget_for_model(model: str) -> tuple[int, int]:
    """(context_window, input_budget)。1M 模型不把 1M 当工作区用。"""
    if "1m" in (model or "").lower():
        return 1_000_000, 120_000
    return 128_000, 30_000


def _env_positive(name: str) -> int | None:
    try:
        value = int(os.environ.get(name, ""))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


@dataclass
class Turn:
    blocks: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)   # {input, cache_read, output, web_search?}
    stop_reason: str = "end_turn"               # 统一成 anthropic 取值："tool_use" | "end_turn" | "max_tokens"


def load_profile() -> ProviderProfile:
    name = os.environ.get("JMB_PROVIDER", "deepseek-anthropic")
    if name == "openai":
        window, budget = budget_for_model(os.environ.get("JMB_OPENAI_MODEL", "gpt-4o-mini"))
        return ProviderProfile(
            "openai", "openai",
            os.environ.get("JMB_OPENAI_BASE_URL", "https://api.openai.com/v1"),
            os.environ.get("JMB_OPENAI_MODEL", "gpt-4o-mini"),
            context_window=_env_positive("JMB_CONTEXT_WINDOW") or window,
            input_budget=_env_positive("JMB_INPUT_BUDGET") or budget,
            max_output_tokens=_env_positive("JMB_MAX_OUTPUT_TOKENS") or 8192)
    if name == "openai-mock":
        window, budget = budget_for_model(os.environ.get("JMB_OPENAI_MODEL", "mock-model"))
        return ProviderProfile(
            "openai-mock", "openai",
            os.environ.get("JMB_OPENAI_BASE_URL", "http://127.0.0.1:8791/v1"),
            os.environ.get("JMB_OPENAI_MODEL", "mock-model"),
            context_window=_env_positive("JMB_CONTEXT_WINDOW") or window,
            input_budget=_env_positive("JMB_INPUT_BUDGET") or budget,
            max_output_tokens=_env_positive("JMB_MAX_OUTPUT_TOKENS") or 8192)
    # 默认：当前在用的这条线路（DeepSeek 的 Anthropic 兼容端点）
    model = config.resolve_model().value
    window, budget = budget_for_model(model)
    return ProviderProfile(
        "deepseek-anthropic", "anthropic",
        config.resolve_base_url().value, model,
        supports_server_web_search=True, echo_thinking_required=False, allow_thinking_drop=True,
        context_window=_env_positive("JMB_CONTEXT_WINDOW") or window,
        input_budget=_env_positive("JMB_INPUT_BUDGET") or budget,
        max_output_tokens=_env_positive("JMB_MAX_OUTPUT_TOKENS") or 8192)


# ---- 线路一：Anthropic 协议 ----

def _anthropic_turn(profile: ProviderProfile, system: str, tools: list,
                    history: list, on_event) -> Turn:
    import anthropic

    token = config.resolve_token()
    if not token.value:
        raise RuntimeError("没有模型凭据（jmb doctor 看 token 行）")
    client = anthropic.Anthropic(base_url=profile.base_url, auth_token=token.value,
                                 timeout=300.0, max_retries=2)
    with client.messages.stream(model=profile.model,
                                max_tokens=profile.max_output_tokens, system=system,
                                tools=tools, messages=history, timeout=300.0) as stream:
        for event in stream:
            if event.type == "content_block_start":
                btype = event.content_block.type
                if btype == "thinking":
                    on_event("thinking")
                elif btype == "server_tool_use":
                    on_event("search")
                elif btype == "text":
                    on_event("text_start")
            elif event.type == "content_block_delta" and event.delta.type == "text_delta":
                on_event("text", event.delta.text)
        message = stream.get_final_message()
    usage = message.usage
    stu = getattr(usage, "server_tool_use", None)
    return Turn(
        blocks=[{k: v for k, v in b.model_dump().items() if v is not None} for b in message.content],
        usage={"input": usage.input_tokens,
               "cache_read": getattr(usage, "cache_read_input_tokens", 0) or 0,
               "output": usage.output_tokens,
               "web_search": getattr(stu, "web_search_requests", 0) if stu else 0},
        stop_reason=message.stop_reason or "end_turn",
    )


# ---- 线路二：OpenAI 协议（客户端工具 only；无服务端搜索）----

def _openai_messages(system: str, history: list) -> list[dict]:
    messages: list[dict] = [{"role": "system", "content": system}]
    for entry in history:
        content = entry.get("content")
        if entry["role"] == "user":
            if isinstance(content, str):
                messages.append({"role": "user", "content": content})
            else:
                # OpenAI 线的 user 消息不会带 server 块；列表内容多为纯文本兜底
                messages.append({"role": "user", "content": " ".join(
                    str(b.get("text", b.get("content", ""))) if isinstance(b, dict) else str(b)
                    for b in content)})
        elif entry["role"] == "assistant":
            text_parts, tool_calls = [], []
            for block in content or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    tool_calls.append({"id": block["id"], "type": "function",
                                       "function": {"name": block["name"],
                                                    "arguments": json.dumps(block.get("input", {}),
                                                                            ensure_ascii=False)}})
            text = "\n".join(t for t in text_parts if t)
            if not text and not tool_calls:
                continue  # 只含 thinking 的助手消息在 OpenAI 线上无内容可发
            item: dict = {"role": "assistant", "content": text or None}
            if tool_calls:
                item["tool_calls"] = tool_calls
            messages.append(item)
    return messages


def _openai_turn(profile: ProviderProfile, system: str, tools: list,
                 history: list, on_event) -> Turn:
    from openai import OpenAI

    # 本机回环不走系统代理：shell 里 http_proxy=127.0.0.1:7897 会把 127.0.0.1 的请求也劫走（实测 502）
    loopback = any(host in profile.base_url for host in ("127.0.0.1", "localhost"))
    client = OpenAI(base_url=profile.base_url,
                    api_key=os.environ.get("JMB_OPENAI_API_KEY", "mock-key"),
                    timeout=300.0, max_retries=1,
                    http_client=_no_proxy_http() if loopback else None)
    messages = _openai_messages(system, history)
    # 历史里的 tool_result 块（chat 存在 user 消息里）翻成 role=tool，紧随其 assistant tool_calls
    for entry in history:
        content = entry.get("content")
        if entry.get("role") == "user" and isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    messages.append({"role": "tool", "tool_call_id": block.get("tool_use_id", ""),
                                     "content": str(block.get("content", ""))})

    function_tools = [{"type": "function",
                       "function": {"name": t["name"], "description": t.get("description", ""),
                                    "parameters": t.get("input_schema", {"type": "object"})}}
                      for t in tools if isinstance(t, dict) and "input_schema" in t]
    stream = client.chat.completions.create(
        model=profile.model, messages=messages, tools=function_tools or None,
        stream=True, stream_options={"include_usage": True}, timeout=300.0)

    text_parts: list[str] = []
    tool_acc: dict[int, dict] = {}
    usage_data: dict = {}
    finish = "stop"
    text_started = False
    for chunk in stream:
        if chunk.usage:
            details = getattr(chunk.usage, "prompt_tokens_details", None)
            usage_data = {"input": chunk.usage.prompt_tokens,
                          "cache_read": (getattr(details, "cached_tokens", 0) or 0) if details else 0,
                          "output": chunk.usage.completion_tokens}
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            if not text_started:
                on_event("text_start")
                text_started = True
            on_event("text", delta.content)
            text_parts.append(delta.content)
        if delta and delta.tool_calls:
            for call in delta.tool_calls:
                acc = tool_acc.setdefault(call.index, {"id": "", "name": "", "args": ""})
                if call.id:
                    acc["id"] = call.id
                if call.function and call.function.name:
                    acc["name"] = call.function.name
                if call.function and call.function.arguments:
                    acc["args"] += call.function.arguments
        if chunk.choices[0].finish_reason:
            finish = chunk.choices[0].finish_reason
    blocks = []
    if text_parts:
        blocks.append({"type": "text", "text": "".join(text_parts)})
    for acc in tool_acc.values():
        try:
            arguments = json.loads(acc["args"] or "{}")
        except ValueError:
            arguments = {}
        blocks.append({"type": "tool_use", "id": acc["id"] or f"mock-{acc['name']}",
                       "name": acc["name"], "input": arguments})
    return Turn(blocks=blocks, usage=usage_data,
                stop_reason="tool_use" if tool_acc else ("max_tokens" if finish == "length" else "end_turn"))


def _no_proxy_http():
    try:
        import httpx
    except ImportError:  # 2026 的 openai SDK 用了 httpx2 分叉模块名（本机实测只有 httpx2）
        import httpx2 as httpx  # type: ignore

    return httpx.Client(trust_env=False, timeout=300.0)


def complete(profile: ProviderProfile, system: str, user: str, max_tokens: int = 1800) -> str:
    """一次性非流式补全（只给上下文压缩用，不挂工具/人格）。"""
    token = config.resolve_token()
    if not token.value:
        raise RuntimeError("没有模型凭据")
    if profile.protocol == "anthropic":
        import anthropic

        client = anthropic.Anthropic(base_url=profile.base_url, auth_token=token.value,
                                     timeout=180.0, max_retries=1)
        parts: list[str] = []
        with client.messages.stream(
                model=profile.model, max_tokens=max_tokens, temperature=0, system=system,
                messages=[{"role": "user", "content": user}]) as stream:
            for event in stream:
                if (event.type == "content_block_delta"
                        and event.delta.type == "text_delta"):
                    parts.append(event.delta.text)
        return "".join(parts).strip()
    from openai import OpenAI

    client = OpenAI(base_url=profile.base_url, api_key=token.value,
                    timeout=180.0, max_retries=1)
    response = client.chat.completions.create(
        model=profile.model, max_tokens=max_tokens, temperature=0,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}])
    return (response.choices[0].message.content or "").strip()


def stream_turn(profile: ProviderProfile, system: str, tools: list, history: list, on_event) -> Turn:
    if profile.protocol == "anthropic":
        return _anthropic_turn(profile, system, tools, history, on_event)
    return _openai_turn(profile, system, tools, history, on_event)

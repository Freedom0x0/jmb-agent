"""jmb chat —— 对话循环（profile 驱动：循环不绑传输，spec §5.1/D29）。

- 流式出字；thinking 只提示不展示，历史里保留回传（按 profile 开关决定）。
- Anthropic 线：服务端 web_search 声明即用（端点忽略 max_uses，实测 ⇒ 轮数靠客户端闸门）。
- OpenAI 线：无服务端搜索 ⇒ 声明 search_web（Bing 兜底）。
- 客户端工具：fetch_page / remember_fact / read_code / write_file / edit_file / run_command /
  today_brief / update_self_file / (search_web)。
  模型只出操作决策，落盘全走 gate / memory / grants / code / brief 的确定性代码。
- 预算闸门：每轮发送前 count_tokens（anthropic 线实测可用），超了折叠老轮次的 thinking 与搜索结果。
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
import uuid

from . import brief, code, config, gate, grants, prefix, providers, seeds, webfetch

INPUT_BUDGET = 30000  # spec §5.6 客户端闸门；跑一周后按 usage 重定


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def _usage_line(usage: dict) -> str:
    parts = [f"in={usage.get('input', 0)}", f"cache_read={usage.get('cache_read', 0)}",
             f"out={usage.get('output', 0)}"]
    if usage.get("web_search"):
        parts.append(f"web_search={usage['web_search']}")
    return " ".join(parts)


# ---- 客户端工具声明（顺序固定，利于缓存）----

FETCH_PAGE = {
    "name": "fetch_page",
    "description": ("抓一个网页的正文。服务端搜索结果没有正文（encrypted_content 客户端解不开），"
                    "要引用、核对就必须真去抓。404/反爬/JS 渲染会如实返回'读不到'——那就如实告诉他。"),
    "input_schema": {"type": "object",
                     "properties": {"url": {"type": "string", "description": "完整的 http(s) URL"}},
                     "required": ["url"]},
}

REMEMBER_FACT = {
    "name": "remember_fact",
    "description": ("把'他说过的关于他自己的原话级事实'存为一条待确认记忆（例：'我周末一般不开电脑'）。"
                    "一次一条、原话级；不记情绪数值、不推断性格、不记公司项目相关内容。"
                    "存进去是 candidate，他收尾确认后才生效。"),
    "input_schema": {"type": "object",
                     "properties": {"fact": {"type": "string", "description": "他的原话或极接近原话的一句话"}},
                     "required": ["fact"]},
}

READ_CODE = {
    "name": "read_code",
    "description": ("读他的代码（列目录或读文件）。默认任何仓都不可读（D11 白名单）；"
                    "未授权的路径会触发一个终端检查点，他允许才读得到。"
                    "read 可用 offset/limit 分段读；响应按行数和字符数截断。"),
    "input_schema": {"type": "object",
                     "properties": {
                         "path": {"type": "string", "description": "文件或目录路径"},
                         "action": {"type": "string", "enum": ["read", "list"],
                                    "description": "read=读文件内容，list=列目录（目录只能 list）"},
                         "offset": {"type": "integer", "description": "从第几行开始（1-based），默认 1"},
                         "limit": {"type": "integer", "description": "最多读多少行"}},
                     "required": ["path"]},
}

WRITE_FILE = {
    "name": "write_file",
    "description": ("创建或整文件覆盖一个代码文件。只用于新文件或完整重写；"
                    "改已有代码优先用 edit_file。首次写会请求本会话授权；"
                    "会存 preimage，undo 回滚整轮。"),
    "input_schema": {"type": "object",
                     "properties": {
                         "path": {"type": "string", "description": "文件路径（相对或绝对）"},
                         "content": {"type": "string", "description": "完整文件内容"}},
                     "required": ["path", "content"]},
}

EDIT_FILE = {
    "name": "edit_file",
    "description": ("对文件做精确文本替换。edits[].old_text 必须对原文唯一且不重叠；"
                    "一次调用可传多个不相邻的替换。改已有代码优先用它，返回 diff。"),
    "input_schema": {"type": "object",
                     "properties": {
                         "path": {"type": "string", "description": "文件路径（相对或绝对）"},
                         "edits": {"type": "array", "items": {
                             "type": "object",
                             "properties": {
                                 "old_text": {"type": "string", "description": "原文中必须唯一且精确匹配的片段"},
                                 "new_text": {"type": "string", "description": "替换后的文本"}},
                             "required": ["old_text", "new_text"]}}},
                     "required": ["path", "edits"]},
}

RUN_COMMAND = {
    "name": "run_command",
    "description": ("在指定目录执行 shell 命令（测试/构建/查看）。首次执行会请求本会话授权；"
                    "输出会截断，完整输出落盘；非零退出如实返回；命令副作用不能 undo。"),
    "input_schema": {"type": "object",
                     "properties": {
                         "command": {"type": "string", "description": "要执行的命令"},
                         "cwd": {"type": "string", "description": "工作目录；默认 jmb 当前目录"},
                         "timeout": {"type": "number", "description": "超时秒数，默认 120，最大 600"}},
                     "required": ["command"]},
}

TODAY_BRIEF = {
    "name": "today_brief",
    "description": "读今天已经生成的每日榜单（GitHub 新高星/周榜/AI 会议）。他问'今天有什么新东西'时先调这个。",
    "input_schema": {"type": "object", "properties": {}},
}

BING_SEARCH = {
    "name": "search_web",
    "description": "本机兜底搜索（当前线路没有服务端搜索时用）。Bing 网页结果：标题+链接+摘要；不可用就如实说，不编。",
    "input_schema": {"type": "object",
                     "properties": {"query": {"type": "string"}},
                     "required": ["query"]},
}


def _tools(profile) -> list:
    client_tools = [prefix.UPDATE_SELF_FILE, FETCH_PAGE, REMEMBER_FACT, READ_CODE,
                    WRITE_FILE, EDIT_FILE, RUN_COMMAND, TODAY_BRIEF]
    if profile.supports_server_web_search:
        return [prefix.WEB_SEARCH, *client_tools]
    return [*client_tools, BING_SEARCH]


# ---- 预算闸门（spec §5.6 本地侧）----

def _trim_search_results(history: list) -> None:
    """每块搜索结果最多留 5 条（spec 的 M=5；服务端无条数参数）。"""
    for message in history:
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for block in content:
            if (isinstance(block, dict) and block.get("type") == "web_search_tool_result"
                    and isinstance(block.get("content"), list) and len(block["content"]) > 5):
                block["content"] = block["content"][:5]


def _enforce_budget(count_fn, profile, system: str, tools: list, history: list) -> None:
    _trim_search_results(history)
    if count_fn is None:  # OpenAI 线暂无 count_tokens ⇒ 只做确定性修剪
        return
    try:
        used = count_fn(system, tools, history)
    except Exception:  # noqa: BLE001 —— count_tokens 挂了就跳过闸门，别挡对话
        return
    if used <= INPUT_BUDGET:
        return
    # 超预算：老轮次（保留最近 4 条消息）折叠——thinking 丢弃仅当 profile 允许（本线路实测白送）。
    for message in history[:-4]:
        content = message.get("content")
        if not isinstance(content, list):
            continue
        kept = []
        for block in content:
            if not isinstance(block, dict):
                kept.append(block)
                continue
            if block.get("type") == "thinking" and profile.allow_thinking_drop:
                continue
            if block.get("type") == "web_search_tool_result" and isinstance(block.get("content"), list):
                block = {**block, "content": block["content"][:2]}
            kept.append(block)
        message["content"] = kept


# ---- 一轮对话（含客户端工具循环）----

def _dispatch(name: str, payload: dict, fact_memory, code_session) -> str:
    if name == "update_self_file":
        return gate.apply(payload)
    if name == "fetch_page":
        return webfetch.fetch_page(str(payload.get("url", "")))
    if name == "remember_fact":
        return (fact_memory.propose(str(payload.get("fact", ""))) if fact_memory
                else "记忆半边没接上（CF 不可用），这条先没记。")
    if name == "read_code":
        path, action = str(payload.get("path", "")), str(payload.get("action", "read"))
        ok, why = grants.authorize(path, action, interactive=sys.stdin.isatty())
        if not ok:
            return why
        return grants.perform(path, action, offset=payload.get("offset", 1),
                              limit=payload.get("limit"))
    if name == "write_file":
        path = str(payload.get("path", ""))
        ok, why = grants.authorize_write(path, interactive=sys.stdin.isatty())
        if not ok:
            return why
        try:
            return code.write_file(path, payload.get("content", ""), code_session)
        except (code.CodeError, OSError) as exc:
            return f"拒绝：{type(exc).__name__}: {exc}"
    if name == "edit_file":
        path = str(payload.get("path", ""))
        ok, why = grants.authorize_write(path, interactive=sys.stdin.isatty())
        if not ok:
            return why
        try:
            return code.edit_file(path, payload.get("edits"), code_session)
        except (code.CodeError, OSError) as exc:
            return f"拒绝：{type(exc).__name__}: {exc}"
    if name == "run_command":
        command = str(payload.get("command", ""))
        cwd = str(payload.get("cwd") or os.getcwd())
        ok, why = grants.authorize_exec(command, cwd, interactive=sys.stdin.isatty())
        if not ok:
            return why
        try:
            return code.run_command(command, cwd, payload.get("timeout"), code_session)
        except (code.CodeError, OSError) as exc:
            return f"拒绝：{type(exc).__name__}: {exc}"
    if name == "today_brief":
        return brief.today_text()
    if name == "search_web":
        return webfetch.bing_search(str(payload.get("query", "")))
    return f"未知工具 {name}，没执行。"


_SELF_ANNOUNCE = {"update_self_file"}
_CODE_ANNOUNCE = {"write_file", "edit_file", "run_command"}


def _stream_turn(profile, count_fn, system: str, tools: list, history: list, log,
                 fact_memory, code_session) -> None:
    thinking_shown = False

    def on_event(kind: str, text: str = "") -> None:
        nonlocal thinking_shown
        if kind == "thinking" and not thinking_shown:
            print("（它在想……）", flush=True)
            thinking_shown = True
        elif kind == "search":
            print("（联网搜索中……）", flush=True)
        elif kind == "text_start":
            print(flush=True)
        elif kind == "text":
            print(text, end="", flush=True)

    while True:
        _enforce_budget(count_fn, profile, system, tools, history)
        turn = providers.stream_turn(profile, system, tools, history, on_event)
        print()
        print(f"  └ {_usage_line(turn.usage)}")
        log.write(json.dumps({"ts": _now(), "kind": "assistant", "blocks": turn.blocks,
                              "usage": turn.usage}, ensure_ascii=False) + "\n")
        log.flush()
        history.append({"role": "assistant", "content": turn.blocks})

        if turn.stop_reason != "tool_use":
            return

        results = []
        for block in turn.blocks:
            if block.get("type") != "tool_use":
                continue
            name, payload = block.get("name", ""), dict(block.get("input") or {})
            if name == "fetch_page":
                print(f"（抓正文：{str(payload.get('url', ''))[:80]}…）", flush=True)
            elif name == "remember_fact" and fact_memory and str(payload.get("fact", "")).strip():
                print("（想记一条事实，收尾时让你确认）", flush=True)
            receipt = _dispatch(name, payload, fact_memory, code_session)
            if name in _SELF_ANNOUNCE:
                note = str(payload.get("note", "")).strip()
                print(f"\n  [jmb 改了 {payload.get('target', '?')}，说 undo 可撤]{('——' + note) if note else ''}")
                log.write(json.dumps({"ts": _now(), "kind": "self_edit", "decision": payload,
                                      "receipt": receipt}, ensure_ascii=False) + "\n")
            elif name in _CODE_ANNOUNCE:
                shown = receipt[:3000] + ("…" if len(receipt) > 3000 else "")
                print(f"\n  [jmb {name}]\n{shown}")
                log.write(json.dumps({"ts": _now(), "kind": "code_tool", "name": name,
                                      "input": payload, "receipt": receipt},
                                     ensure_ascii=False) + "\n")
            results.append({"type": "tool_result", "tool_use_id": block.get("id", ""),
                            "content": receipt})
        history.append({"role": "user", "content": results})


def run() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    seeds.ensure()

    profile = providers.load_profile()
    if profile.protocol == "anthropic" and not config.resolve_token().value:
        print("没有模型凭据——先跑 `jmb doctor` 看 token 那一行。")
        return 1

    fact_memory = None
    try:
        from . import memory as jmb_memory
        fact_memory = jmb_memory.FactMemory()
    except Exception as exc:  # noqa: BLE001 —— 记忆半边不可用不阻塞对话
        print(f"[长期事实记忆没接上：{type(exc).__name__}: {str(exc)[:120]}——本会话只能用文件记录]")

    code_session = code.CodeSession()

    count_fn = None
    if profile.protocol == "anthropic":
        import anthropic
        model = profile.model
        client = anthropic.Anthropic(base_url=profile.base_url,
                                     auth_token=config.resolve_token().value,
                                     timeout=120.0, max_retries=1)
        count_fn = lambda system, tools, history: (  # noqa: E731
            client.messages.count_tokens(model=model, system=system, tools=tools,
                                         messages=history).input_tokens)

    system = prefix.build_system()
    tools = _tools(profile)

    config.sessions_dir().mkdir(parents=True, exist_ok=True)
    tid = uuid.uuid4().hex[:6]
    tpath = config.sessions_dir() / f"{_dt.date.today().isoformat()}-{tid}.jsonl"
    log = tpath.open("a", encoding="utf-8")

    print(f"jmb · 会话 {tid}（线路 {profile.name} · 转录 {tpath.name}）")
    print("命令：/quit 退出 · undo 撤回最近一轮代码改动或最近一次自我改写 · 其余都是对话")
    print("——流式出字；（联网搜索中…）服务端搜索；（抓正文…）fetch_page\n")

    history: list[dict] = []
    try:
        while True:
            try:
                user = input("你> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not user:
                continue
            if user in {"/quit", "/exit", "q"}:
                break
            if user.lower() == "undo":
                print(code_session.undo_last_turn() or gate.undo())
                continue

            send_text = user
            if fact_memory:
                recalled = fact_memory.search(user)
                if recalled:
                    send_text = f"[记忆召回——他以前说过的事，可自然引用]\n{recalled}\n\n{user}"
            history.append({"role": "user", "content": send_text})
            log.write(json.dumps({"ts": _now(), "kind": "user", "text": user}, ensure_ascii=False) + "\n")
            log.flush()
            try:
                code_session.begin_turn()
                _stream_turn(profile, count_fn, system, tools, history, log,
                             fact_memory, code_session)
            except Exception as exc:  # noqa: BLE001 —— 一轮失败不拖垮会话
                print(f"\n[这一轮出错：{type(exc).__name__}: {str(exc)[:300]}]")
                print("（历史已保留，换个说法再说，或 /quit）")
            finally:
                code_session.end_turn()
    finally:
        if code_session.turn_id:
            code_session.end_turn()
        if fact_memory:
            print(fact_memory.confirm_pending(interactive=sys.stdin.isatty()))
        log.close()
    print(f"\n再见。转录在 {tpath}")
    return 0

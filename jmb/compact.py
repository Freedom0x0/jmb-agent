"""上下文压缩（D38）：观察遮蔽之后，把最老的对话压成结构化摘要。

只压历史，不碰 system 前缀（江慕白人格/三份记录永远不进摘要）；摘要作为一条
带标记的 user 消息放回历史，保留最近若干条消息和工具对，保证角色交替。
"""
from __future__ import annotations

import json

from . import providers

KEEP_MESSAGES = 8
CHUNK_CHARS = 40_000
MAX_SUMMARY_CHARS = 4_000
MIN_SUMMARY_CHARS = 40

SUMMARY_SYSTEM = """你在压缩一段长对话的旧部分。只输出一份中文摘要，不要寒暄、不要解释。
必须保留（有就写，没有写“无”）：
1. 目标 / 当前任务
2. 已确认的决定、约束、用户明确要求（尽量保留原话要点）
3. 动过的文件：完整路径 + 改了什么 + 当前状态（已改/未改/已撤销）
4. 跑过的命令/测试：命令、exit code、关键错误（短）
5. 未解决的问题 / 下一步
6. 试过但失败的路（不要再试）
7. 用户明确说不要提 / 不要做的事
路径、变量名、报错原文尽量原样保留。不要编造；不要写情绪评分；不要写公司项目名
（写“公司项目（略）”）；不要写密钥/token（写“凭据（略）”）。摘要控制在 1200 字以内。"""


def render(history: list) -> str:
    lines: list[str] = []
    for message in history:
        role = str(message.get("role") or "?")
        content = message.get("content")
        if isinstance(content, str):
            lines.append(f"[{role}] {content}")
            continue
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            if kind == "text":
                text = block.get("text") or ""
                if text:
                    lines.append(f"[{role}] {text}")
            elif kind == "tool_use":
                payload = json.dumps(block.get("input") or {}, ensure_ascii=False)
                lines.append(f"[{role} 工具调用] {block.get('name', '?')} {payload[:800]}")
            elif kind == "tool_result":
                value = block.get("content")
                if isinstance(value, list):
                    value = " ".join(str(item) for item in value)
                lines.append(f"[工具结果] {str(value)[:1500]}")
    return "\n".join(lines)


def summarize(profile, history: list) -> str:
    text = render(history).strip()
    if len(text) < 200:
        raise ValueError("历史太短，不值得压缩")
    summary = ""
    for start in range(0, len(text), CHUNK_CHARS):
        chunk = text[start:start + CHUNK_CHARS]
        prompt = (f"已有摘要：\n{summary}\n\n" if summary else "") + f"新增历史：\n{chunk}"
        part = providers.complete(profile, SUMMARY_SYSTEM, prompt, max_tokens=1800)
        if len(part.strip()) < MIN_SUMMARY_CHARS:
            raise ValueError("压缩器返回空摘要/过短")
        summary = part.strip()
    return summary[:MAX_SUMMARY_CHARS]


def cut_index(history: list, keep: int = KEEP_MESSAGES) -> int | None:
    """切在 assistant 消息上：摘要用 user 角色，后面紧跟 assistant，角色仍交替。"""
    if len(history) <= keep:
        return None
    for index in range(len(history) - keep, 0, -1):
        if history[index].get("role") == "assistant":
            return index
    return None


def apply(history: list, summary: str, keep: int = KEEP_MESSAGES) -> tuple[int, int] | None:
    cut = cut_index(history, keep)
    if cut is None:
        return None
    message = {"role": "user",
               "content": ("[系统生成的上下文摘要，不是用户发言]\n"
                           f"（压缩自前 {cut} 条消息）\n{summary}")}
    history[:] = [message, *history[cut:]]
    return cut, len(history)

"""假 OpenAI 兼容端点：不接模型，回固定内容。

用途：验收 Phase 2"只改 profile 就切 provider、循环零改动"——真第二家没有 key，
用这个把传输层做实。跑法：uv run python scripts/mock_openai.py（监听 127.0.0.1:8791）
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:  # 安静
        pass

    def do_POST(self) -> None:
        try:
            self._respond()
        except (ConnectionAbortedError, BrokenPipeError):
            pass  # 客户端中途断开（重试/超时）——正常，别刷栈

    def _respond(self) -> None:
        if not self.path.rstrip("/").endswith("chat/completions"):
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("content-length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            body = {}
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.end_headers()

        def sse(payload: dict) -> None:
            self.wfile.write(("data: " + json.dumps(payload, ensure_ascii=False) + "\n\n").encode("utf-8"))

        base = {"id": "mock", "object": "chat.completion.chunk", "created": 1,
                "model": body.get("model", "mock")}

        def chunk(delta: dict, finish: str | None = None) -> dict:
            return {**base, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}

        sse(chunk({"role": "assistant"}))
        for piece in ("MOCK", " OK", "：这是假端点的固定回复，证明对话循环没有绑死在 anthropic 传输上。"):
            sse(chunk({"content": piece}))
        sse(chunk({}, finish="stop"))
        sse({**base, "choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 9,
                                              "prompt_tokens_details": {"cached_tokens": 0}}})
        self.wfile.write(b"data: [DONE]\n\n")


if __name__ == "__main__":
    print("mock OpenAI 端点在 http://127.0.0.1:8791/v1 （Ctrl+C 退出）")
    HTTPServer(("127.0.0.1", 8791), Handler).serve_forever()

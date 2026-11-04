"""移动端薄后端（D50）：HTTP + SSE 包 ChatSession，surface=mobile。

形状照 spec §4 的二期预留：对话循环零改动，只包入口。模型 key 只留后端
（D13 口子5）；手机浏览器是瘦客户端。鉴权 v0 = 一次性配对 token 换
HttpOnly cookie（单 owner；多 owner / 真鉴权等 D13 二期）。

会话模型：一个 SSE 连接 = 一只 ChatSession（同桌面 app 一窗口一会话）。
sid 由客户端保管；重连 = 新会话，跨会话连续性靠 CF 记忆召回（同桌面重启）。
"""
from __future__ import annotations

import json
import queue
import threading
import uuid
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import chat, config

_COOKIE = "jmb_token"
_STATIC = Path(__file__).resolve().parent / "server_static"
_HEARTBEAT = 15.0
_CONFIRM_TIMEOUT = 300.0


class MobileSession:
    """一只移动端会话：事件队列出 SSE，收件队列进会话循环。"""

    def __init__(self) -> None:
        self.id = uuid.uuid4().hex[:6]
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.inbox: queue.Queue = queue.Queue()
        self._confirm_answer = ""
        self._confirm_event = threading.Event()
        self.session = chat.ChatSession(self._emit, surface="mobile")
        saved = chat.load_conversation()
        if saved.get("history"):
            self.session.history = saved["history"]
        self._saved_render = saved.get("render", [])

    def _emit(self, kind: str, data) -> None:
        self.events.put((kind, data))

    def _ask_confirm(self, items, more: int) -> str:
        self.events.put(("confirm", {"items": items, "more": more}))
        if not self._confirm_event.wait(timeout=_CONFIRM_TIMEOUT):
            return ""   # 超时按设计留到下次（同终端没回答）
        return self._confirm_answer

    def run(self) -> None:
        try:
            self.events.put(("ready", {"sid": self.id, "tid": self.session.tid,
                                       "surface": "mobile"}))
            if self._saved_render:
                self.events.put(("history", self._saved_render))
            try:
                self.session.warmup()
            except Exception:  # noqa: BLE001 —— 预热失败不影响对话
                pass
            while True:
                item = self.inbox.get()
                if item is None:
                    break
                if item == "__finish__":
                    try:
                        receipt = self.session.confirm_pending(
                            interactive=True, ask=self._ask_confirm)
                        if receipt:
                            self.events.put(("notice", receipt))
                    except Exception as exc:  # noqa: BLE001
                        self.events.put(("error", f"记忆确认失败：{str(exc)[:120]}"))
                    continue
                self.session.send(str(item))
        except Exception as exc:  # noqa: BLE001 —— 会话级失败如实上抛，不拖垮服务
            self.events.put(("fatal", f"{type(exc).__name__}: {str(exc)[:200]}"))
        finally:
            try:
                self.session.close()
            except Exception:  # noqa: BLE001
                pass

    def finish(self) -> None:
        self.inbox.put("__finish__")

    def stop(self) -> None:
        self.session.cancel_generation()
        self.inbox.put(None)


class Handler(BaseHTTPRequestHandler):
    server_version = "jmb-mobile/0.1"
    protocol_version = "HTTP/1.1"
    sessions: dict[str, MobileSession] = {}
    lock = threading.Lock()

    # ---- 工具 ----
    def _send(self, code: int, body: bytes, ctype: str,
              extra: list[tuple[str, str]] | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra or []):
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _token(self) -> str:
        return getattr(self.server, "token", "")

    def _authed(self) -> bool:
        cookies = SimpleCookie()
        cookies.load(self.headers.get("Cookie", ""))
        cookie = cookies.get(_COOKIE)
        return cookie is not None and cookie.value == self._token()

    def _body(self) -> dict:
        try:
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            return json.loads(raw or b"{}")
        except (ValueError, UnicodeDecodeError):
            return {}

    def log_message(self, *args) -> None:  # 安静点
        pass

    # ---- 路由 ----
    def do_GET(self) -> None:
        if self.path == "/":
            self._send(200, (_STATIC / "index.html").read_bytes(),
                       "text/html; charset=utf-8",
                       extra=[("Cache-Control", "no-store")])
            return
        if self.path == "/api/stream":
            self._stream()
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        body = self._body()
        if self.path == "/api/auth":
            if body.get("token") == self._token():
                self._send(200, b'{"ok":true}', "application/json",
                           [("Set-Cookie", f"{_COOKIE}={self._token()}; "
                                           f"Path=/; HttpOnly; SameSite=Lax")])
                return
            self._json(401, {"error": "token 不对"})
            return
        if not self._authed():
            self._json(401, {"error": "先配对"})
            return
        session = self.sessions.get(str(body.get("sid", "")))
        if self.path == "/api/turn":
            if session is None:
                self._json(404, {"error": "会话没了，重新打开页面"})
                return
            session.inbox.put(body.get("text", ""))
            self._json(200, {"ok": True})
        elif self.path == "/api/confirm":
            if session is None:
                self._json(404, {"error": "会话没了"})
                return
            session._confirm_answer = str(body.get("answer", ""))
            session._confirm_event.set()
            self._json(200, {"ok": True})
        elif self.path == "/api/finish":
            if session is None:
                self._json(404, {"error": "会话没了"})
                return
            session.finish()
            self._json(200, {"ok": True})
        else:
            self._json(404, {"error": "not found"})

    # ---- SSE ----
    def _stream(self) -> None:
        if not self._authed():
            self._json(401, {"error": "先配对"})
            return
        try:
            mobile = MobileSession()
        except Exception as exc:  # noqa: BLE001 —— 没有凭据等：如实告诉手机
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            payload = json.dumps({"error": str(exc)[:200]}, ensure_ascii=False)
            self.wfile.write(f"event: fatal\ndata: {payload}\n\n".encode("utf-8"))
            self.wfile.flush()
            return
        with self.lock:
            self.sessions[mobile.id] = mobile
        thread = threading.Thread(target=mobile.run, daemon=True)
        thread.start()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            while True:
                try:
                    kind, data = mobile.events.get(timeout=_HEARTBEAT)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                frame = f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                self.wfile.write(frame.encode("utf-8"))
                self.wfile.flush()
        except OSError:  # 断连/写关闭：普通噪音，清理在 finally
            pass
        finally:
            # 先停会话线程再摘表：dict 里没有 ⟹ transcript 句柄已释放（Windows 删除依赖这个）
            mobile.stop()
            thread.join(timeout=5)
            with self.lock:
                self.sessions.pop(mobile.id, None)


def run(host: str = "0.0.0.0", port: int = 8791) -> int:
    token = config.load_or_create_server_token()
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.token = token  # type: ignore[attr-defined]
    print(f"jmb 移动端后端 · http://{host}:{port}（surface=mobile，模型 key 只留本机）")
    print(f"配对 token（只打印这一次，手机上填一次）：{token}")
    print("手机浏览器打开 http://<本机IP>:{port} 填 token 即用；"
          "云上部署时前面套 TLS（HTTPS）再开给手机。")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

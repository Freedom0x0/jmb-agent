"""移动端后端（D50）：surface 能力表 + 前缀 + HTTP/SSE 冒烟（不需要真模型）。

流式与世界事实都 mock 掉：只验服务器形状（鉴权/SSE/会话生命周期），不碰网络。
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from unittest import mock

from jmb import chat, prefix, providers


class SurfaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._home = str(Path(self._tmp.name) / "home")
        Path(self._home).mkdir()
        (Path(self._home) / "config.json").write_text(
            json.dumps({"model": "deepseek-flash"}), encoding="utf-8")
        self._env = mock.patch.dict(os.environ, {"JMB_HOME": self._home}, clear=False)
        self._env.start()
        self.addCleanup(self._env.stop)

    def test_mobile_surface_only_chat_search_remember(self) -> None:
        profile = providers.load_profile()
        mobile = {t["name"] for t in chat._tools(profile, "mobile")}
        self.assertEqual(mobile, {"web_search", "fetch_page", "remember_fact"})
        desktop = {t["name"] for t in chat._tools(profile, "desktop")}
        self.assertIn("read_code", desktop)
        self.assertIn("write_file", desktop)
        self.assertIn("run_command", desktop)

    def test_mobile_prompt_drops_desktop_capabilities(self) -> None:
        system = prefix.build_system("mobile")
        self.assertIn("surface=mobile", system)
        self.assertNotIn("read_code", system)
        self.assertIn("fetch_page", system)
        default = prefix.build_system()
        self.assertIn("surface=desktop", default)
        self.assertIn("read_code", default)


class ServerSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._home = str(Path(self._tmp.name) / "home")
        Path(self._home).mkdir()
        # ChatSession 构造要凭据；假 token 只为过构造关，本测试不发真请求
        (Path(self._home) / "config.json").write_text(
            json.dumps({"model": "deepseek-flash", "token": "sk-test"}),
            encoding="utf-8")
        self._env = mock.patch.dict(os.environ, {"JMB_HOME": self._home}, clear=False)
        self._env.start()
        self.addCleanup(self._env.stop)

    def test_auth_index_and_stream(self) -> None:
        from jmb import server

        def fake_stream(profile, count_fn, system, tools, history, log,
                        fact_memory, code_session, emit, budget=0, cancel=None):
            emit("text_start", "")
            emit("text", "假回复")
            emit("text_end", "")
            return {"input": 10, "cache_read": 0, "output": 5}

        httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        httpd.token = "pair-me"
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)   # LIFO：先 shutdown 停 select，再关 socket
        self.addCleanup(httpd.shutdown)
        port = httpd.server_address[1]
        base = f"http://127.0.0.1:{port}"

        # warmup 也 mock 掉：它的 anthropic 延迟导入在本进程会触发 GC → PIL ImageTk
        # __del__ 对已销毁的 Tk 解释器死锁（test_app 的 Tk 测试留下的垃圾对象）；
        # 生产进程不创建 Tk，无此问题。
        with mock.patch("jmb.chat._stream_turn", fake_stream), \
                mock.patch("jmb.world.WorldFacts.context", lambda self: ""), \
                mock.patch("jmb.world.WorldFacts.refresh_async", lambda self: None), \
                mock.patch("jmb.chat.ChatSession.warmup", lambda self: None):
            # 未配对：页面可读（登录壳），API 拒绝
            with urllib.request.urlopen(base + "/") as resp:
                self.assertEqual(resp.status, 200)
                self.assertIn("江慕白", resp.read().decode("utf-8"))
                # 手机浏览器会缓存旧页面（没有 history 监听脚本）——禁止缓存
                self.assertIn("no-store", resp.headers.get("Cache-Control", ""))
            try:
                urllib.request.urlopen(base + "/api/stream")
                self.fail("未配对应该 401")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 401)

            # 配对：错 token 拒绝，对的给 cookie
            req = urllib.request.Request(base + "/api/auth",
                                         data=b'{"token":"wrong"}',
                                         headers={"Content-Type": "application/json"})
            try:
                urllib.request.urlopen(req)
                self.fail("错 token 应该 401")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 401)
            jar = CookieJar()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
            req = urllib.request.Request(base + "/api/auth",
                                         data=b'{"token":"pair-me"}',
                                         headers={"Content-Type": "application/json"})
            with opener.open(req) as resp:
                self.assertEqual(resp.status, 200)
            self.assertTrue(any(c.name == "jmb_token" for c in jar))

            # SSE：读到 ready 帧拿到 sid（会话构造成功即发，不触发模型调用）
            with opener.open(base + "/api/stream") as resp:
                self.assertEqual(resp.status, 200)
                self.assertIn("text/event-stream", resp.headers["Content-Type"])
                sid = None
                for _ in range(50):
                    line = resp.readline()
                    if not line:
                        break
                    if line.startswith(b"event: ready"):
                        data = json.loads(resp.readline().removeprefix(b"data: "))
                        sid = data["sid"]
                        break
                self.assertTrue(sid)
                # turn 接受排队（mock 的流式瞬间完成，不碰网络）
                req = urllib.request.Request(
                    base + "/api/turn",
                    data=json.dumps({"sid": sid, "text": "hi"}).encode(),
                    headers={"Content-Type": "application/json"})
                with opener.open(req) as turn_resp:
                    self.assertEqual(turn_resp.status, 200)
            # 断连清理：直接驱动 stop（真断连由 handler 的 finally 走同一路径）
            mobile = server.Handler.sessions.get(sid)
            self.assertTrue(mobile)
            mobile.stop()
            for _ in range(100):
                if mobile.session.closed:
                    break
                time.sleep(0.1)
            self.assertTrue(mobile.session.closed)

    def test_history_persists_across_connections(self) -> None:
        import time

        from jmb import server

        captured = {}

        def fake_stream(profile, count_fn, system, tools, history, log,
                        fact_memory, code_session, emit, budget=0, cancel=None):
            captured["history"] = [dict(m) for m in history]
            emit("text_start", "")
            emit("text", "记下了")
            emit("text_end", "")
            return {"input": 1, "cache_read": 0, "output": 1}

        httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        httpd.token = "pair-me"
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)   # LIFO：先 shutdown 停 select，再关 socket
        self.addCleanup(httpd.shutdown)
        base = f"http://127.0.0.1:{httpd.server_address[1]}"

        with mock.patch("jmb.chat._stream_turn", fake_stream), \
                mock.patch("jmb.world.WorldFacts.context", lambda self: ""), \
                mock.patch("jmb.world.WorldFacts.refresh_async", lambda self: None), \
                mock.patch("jmb.chat.ChatSession.warmup", lambda self: None):
            jar = CookieJar()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
            req = urllib.request.Request(base + "/api/auth", data=b'{"token":"pair-me"}',
                                         headers={"Content-Type": "application/json"})
            with opener.open(req) as resp:
                self.assertEqual(resp.status, 200)

            def open_stream():
                resp = opener.open(base + "/api/stream")
                sid = None
                for _ in range(100):
                    line = resp.readline()
                    if not line:
                        break
                    if line.startswith(b"event: ready"):
                        sid = json.loads(resp.readline().removeprefix(b"data: "))["sid"]
                        break
                return resp, sid

            def turn(resp, sid, text):
                req = urllib.request.Request(
                    base + "/api/turn",
                    data=json.dumps({"sid": sid, "text": text}).encode(),
                    headers={"Content-Type": "application/json"})
                with opener.open(req) as tr:
                    self.assertEqual(tr.status, 200)
                deadline = time.time() + 10
                while time.time() < deadline:
                    line = resp.readline()
                    if not line:
                        return False
                    if line.startswith(b"event: turn_end"):
                        return True
                return False

            # 第一会话：发一条 → turn_end 时 history+render 落盘
            resp1, sid1 = open_stream()
            with resp1:
                self.assertTrue(sid1)
                self.assertTrue(turn(resp1, sid1, "记住我"))
            saved = json.loads(chat.conversation_path().read_text(encoding="utf-8"))
            self.assertIn({"role": "user", "text": "记住我"}, saved["render"])
            self.assertTrue(any("记住我" in str(m.get("content", ""))
                                for m in saved["history"]))
            # 停掉第一会话，释放 transcript 句柄（临时目录才删得掉）
            mobile1 = server.Handler.sessions.get(sid1)
            self.assertTrue(mobile1)
            mobile1.stop()
            for _ in range(100):
                if mobile1.session.closed:
                    break
                time.sleep(0.1)
            self.assertTrue(mobile1.session.closed)

            # 第二会话：恢复渲染历史 + 模型带着上一条发轮
            resp2, sid2 = open_stream()
            with resp2:
                self.assertTrue(sid2)
                frames = {}
                deadline = time.time() + 10
                while time.time() < deadline and "history" not in frames:
                    line = resp2.readline()
                    if not line:
                        break
                    if line.startswith(b"event: "):
                        kind = line[7:].strip().decode()
                        frames[kind] = json.loads(
                            resp2.readline().removeprefix(b"data: "))
                self.assertIn({"role": "user", "text": "记住我"},
                              frames.get("history", []))
                self.assertTrue(turn(resp2, sid2, "现在几了"))
            self.assertTrue(any("记住我" in str(m.get("content", ""))
                                for m in captured["history"]))
            # 停掉第二会话，释放 transcript 句柄（临时目录才删得掉）
            mobile = server.Handler.sessions.get(sid2)
            self.assertTrue(mobile)
            mobile.stop()
            for _ in range(100):
                if mobile.session.closed:
                    break
                time.sleep(0.1)
            self.assertTrue(mobile.session.closed)


if __name__ == "__main__":
    unittest.main()

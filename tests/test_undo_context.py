from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class UndoContextTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self._old_home = os.environ.get("JMB_HOME")
        os.environ["JMB_HOME"] = str(Path(self.tmp.name) / "home")
        # D49 起凭据只认 jmb/config.json；本测试流式是 mock 的，种假 token 过构造关
        home = Path(self.tmp.name) / "home"
        home.mkdir()
        (home / "config.json").write_text('{"token": "sk-test"}', encoding="utf-8")

    def tearDown(self) -> None:
        if self._old_home is None:
            os.environ.pop("JMB_HOME", None)
        else:
            os.environ["JMB_HOME"] = self._old_home
        self.tmp.cleanup()

    def test_undo_injects_system_event_into_next_turn(self) -> None:
        from jmb import gate
        from jmb.chat import ChatSession

        session = ChatSession(lambda kind, data: None)
        try:
            gate.apply({"op": "UPDATE", "target": "RELATIONSHIP.md",
                        "payload": "- undo test\n", "note": "test"})
            message = session.undo()
            self.assertIn("已撤回", message)
            self.assertTrue(session.notes)

            captured: list[str] = []

            def fake_stream(profile, count_fn, system, tools, history, log,
                            fact_memory, code_session, emit, **kwargs):
                captured.append(history[-1]["content"])

            with mock.patch("jmb.chat._stream_turn", fake_stream):
                session.send("hello")
            self.assertIn("[系统事件", captured[0])
            self.assertIn("hello", captured[0])
            self.assertFalse(session.notes)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()

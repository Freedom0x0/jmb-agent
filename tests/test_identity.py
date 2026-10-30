from __future__ import annotations

import io
import unittest
from unittest import mock

from jmb import chat


class IdentityTest(unittest.TestCase):
    def test_direct_identity_questions_are_answered_locally(self) -> None:
        for question in ("你是谁？", "你是哪个模型？", "介绍一下你自己",
                         "你是AI吗", "你是真人吗"):
            reply = chat._identity_reply(question)
            self.assertIsNotNone(reply, question)
            self.assertIn("江慕白", reply)
            for bad in ("讯飞", "星火", "X2.6", "Spark", "DeepSeek", "OpenAI"):
                self.assertNotIn(bad, reply)

    def test_task_questions_are_not_intercepted(self) -> None:
        self.assertIsNone(chat._identity_reply("帮我查一下今天的金价"))
        self.assertIsNone(chat._identity_reply("你是谁，帮我查一下今天的金价"))
        self.assertTrue(chat._identity_sensitive("你是谁，帮我查一下今天的金价"))
        self.assertFalse(chat._identity_sensitive("帮我重构这段缓存代码"))

    def test_identity_turn_does_not_call_the_model(self) -> None:
        session = object.__new__(chat.ChatSession)
        session.history = []
        session.log = io.StringIO()
        session.transcript_path = "test.jsonl"
        events: list[tuple[str, object]] = []
        session.emit = lambda kind, data: events.append((kind, data))
        with mock.patch("jmb.chat._stream_turn") as stream:
            session.send("你是谁？你是哪个模型？")
        stream.assert_not_called()
        self.assertEqual([message["role"] for message in session.history],
                         ["user", "assistant"])
        text = "".join(str(data) for kind, data in events if kind == "text")
        self.assertIn("江慕白", text)
        self.assertTrue(any(kind == "turn_end" for kind, _ in events))


if __name__ == "__main__":
    unittest.main()

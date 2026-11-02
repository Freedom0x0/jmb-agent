from __future__ import annotations

import io
import threading
import unittest
from unittest import mock

from jmb import chat, providers


class StopGenerationTest(unittest.TestCase):
    def test_cancel_before_model_call_emits_stopped_without_request(self) -> None:
        cancel = threading.Event()
        cancel.set()
        history = [{"role": "user", "content": "hi"}]
        events: list[tuple[str, object]] = []
        with mock.patch("jmb.chat.providers.stream_turn") as stream:
            chat._stream_turn(None, None, "", [], history, io.StringIO(), None, None,
                              lambda kind, data: events.append((kind, data)),
                              cancel=cancel)
        stream.assert_not_called()
        self.assertEqual([kind for kind, _ in events], ["text_end", "stopped"])
        self.assertEqual(history, [{"role": "user", "content": "hi"}])

    def test_cancelled_turn_keeps_partial_text(self) -> None:
        history = [{"role": "user", "content": "hi"}]
        turn = providers.Turn(
            blocks=[{"type": "text", "text": "半句"}],
            usage={}, stop_reason="cancelled")
        events: list[tuple[str, object]] = []
        with mock.patch("jmb.chat.providers.stream_turn", return_value=turn):
            chat._stream_turn(None, None, "", [], history, io.StringIO(), None, None,
                              lambda kind, data: events.append((kind, data)))
        self.assertEqual(history[-1]["role"], "assistant")
        self.assertEqual(history[-1]["content"], [{"type": "text", "text": "半句"}])
        self.assertIn("stopped", [kind for kind, _ in events])
        self.assertNotIn("usage", [kind for kind, _ in events])

    def test_cancel_before_tool_execution_still_keeps_history_legal(self) -> None:
        history = [{"role": "user", "content": "hi"}]
        turn = providers.Turn(
            blocks=[{"type": "tool_use", "id": "t1", "name": "run_command",
                     "input": {"command": "echo hi"}}],
            usage={}, stop_reason="tool_use")
        cancel = threading.Event()

        def fake_stream(*_args, **_kwargs):
            cancel.set()
            return turn

        events: list[tuple[str, object]] = []
        with mock.patch("jmb.chat.providers.stream_turn", side_effect=fake_stream), \
                mock.patch("jmb.chat._dispatch") as dispatch:
            chat._stream_turn(None, None, "", [], history, io.StringIO(), None, None,
                              lambda kind, data: events.append((kind, data)),
                              cancel=cancel)
        dispatch.assert_not_called()
        self.assertEqual(history[-1]["role"], "user")
        self.assertEqual(history[-1]["content"][0]["tool_use_id"], "t1")
        self.assertIn("已停止", history[-1]["content"][0]["content"])
        self.assertIn("stopped", [kind for kind, _ in events])


class RewindTest(unittest.TestCase):
    def test_rewind_cuts_everything_after_selected_user_message(self) -> None:
        session = object.__new__(chat.ChatSession)
        session.history = [
            {"role": "user", "content": "u0"},
            {"role": "assistant", "content": [{"type": "text", "text": "a0"}]},
            {"role": "user", "content": "u1"},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t",
                                          "content": "x"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "a1"}]},
            {"role": "user", "content": "u2"},
        ]
        session.log = io.StringIO()
        session.last_input_tokens = 999
        self.assertTrue(session.rewind_user(1))
        self.assertEqual([m["content"] for m in session.history],
                         ["u0", [{"type": "text", "text": "a0"}]])
        self.assertEqual(session.last_input_tokens, 0)
        self.assertIn('"kind": "rewind"', session.log.getvalue())
        self.assertFalse(session.rewind_user(2))

    def test_rewind_skips_summary_and_falls_back_to_text_after_compaction(self) -> None:
        session = object.__new__(chat.ChatSession)
        session.history = [
            {"role": "user", "content": "[系统生成的上下文摘要，不是用户发言]\n旧内容"},
            {"role": "assistant", "content": [{"type": "text", "text": "a0"}]},
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": [{"type": "text", "text": "a1"}]},
            {"role": "user", "content": "u2"},
        ]
        session.log = io.StringIO()
        session.last_input_tokens = 0
        self.assertTrue(session.rewind_user(5, expected="u1"))
        self.assertEqual([m["content"] for m in session.history],
                         ["[系统生成的上下文摘要，不是用户发言]\n旧内容",
                          [{"type": "text", "text": "a0"}]])
        self.assertFalse(session.rewind_user(0, expected="not-in-context"))


class ChatViewEditTest(unittest.TestCase):
    def test_truncate_from_user_resets_index(self) -> None:
        try:
            import tkinter as tk
        except Exception:  # noqa: BLE001
            self.skipTest("tkinter unavailable")
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("no display")
        root.withdraw()
        try:
            from jmb.app.widgets import ChatView

            view = ChatView(root)
            view.on_edit_user = lambda index, text: None
            view.append("u0", "user")
            view.append("a0", "assistant")
            view.append("u1", "user")
            view.append("a1", "assistant")
            self.assertTrue(view.truncate_from_user(1))
            self.assertEqual([m["role"] for m in view._messages],
                             ["user", "assistant"])
            self.assertEqual(view._user_count, 1)
            view.append("u1-new", "user")
            self.assertEqual(view._messages[-1]["user_index"], 1)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()

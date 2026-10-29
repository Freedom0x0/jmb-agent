from __future__ import annotations

import unittest
from unittest import mock

from jmb import chat, providers


class BudgetHistoryTest(unittest.TestCase):
    def test_thinking_only_message_is_not_emptied(self) -> None:
        thinking = {"type": "thinking", "thinking": "x", "signature": "s"}
        history = [
            {"role": "assistant", "content": [thinking]},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": [{"type": "text", "text": "ok"}]},
            {"role": "user", "content": "again"},
            {"role": "assistant", "content": [thinking]},
        ]
        profile = providers.ProviderProfile("t", "anthropic", "http://x", "m")
        chat._enforce_budget(lambda s, t, h: 10**9, profile, "sys", [], history)
        self.assertEqual(history[0]["content"], [thinking])

    def test_trim_still_drops_thinking_when_text_remains(self) -> None:
        history = [
            {"role": "assistant", "content": [
                {"type": "thinking", "thinking": "x"},
                {"type": "text", "text": "ok"},
            ]},
            {"role": "user", "content": "1"},
            {"role": "assistant", "content": [{"type": "text", "text": "2"}]},
            {"role": "user", "content": "3"},
            {"role": "assistant", "content": [{"type": "text", "text": "4"}]},
        ]
        profile = providers.ProviderProfile("t", "anthropic", "http://x", "m")
        chat._enforce_budget(lambda s, t, h: 10**9, profile, "sys", [], history)
        self.assertEqual(history[0]["content"], [{"type": "text", "text": "ok"}])

    def test_empty_turn_is_not_appended(self) -> None:
        history = [{"role": "user", "content": "hi"}]
        turn = providers.Turn(blocks=[], usage={}, stop_reason="end_turn")
        with mock.patch("jmb.chat.providers.stream_turn", return_value=turn):
            chat._stream_turn(None, None, "", [], history, mock.Mock(), None, None,
                              lambda kind, data: None)
        self.assertEqual(history, [{"role": "user", "content": "hi"}])

    def test_empty_tool_results_are_not_appended(self) -> None:
        history = [{"role": "user", "content": "hi"}]
        turn = providers.Turn(blocks=[{"type": "thinking", "thinking": "x"}],
                              usage={}, stop_reason="tool_use")
        with mock.patch("jmb.chat.providers.stream_turn", return_value=turn):
            chat._stream_turn(None, None, "", [], history, mock.Mock(), None, None,
                              lambda kind, data: None)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[-1]["role"], "assistant")

    def test_openai_skips_thinking_only_assistant(self) -> None:
        history = [
            {"role": "assistant", "content": [{"type": "thinking", "thinking": "x"}]},
            {"role": "user", "content": "hi"},
        ]
        messages = providers._openai_messages("sys", history)
        self.assertEqual([m["role"] for m in messages], ["system", "user"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import os
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

    def test_max_output_tokens_env_override(self) -> None:
        with mock.patch.dict(os.environ, {"JMB_MAX_OUTPUT_TOKENS": "16384"}):
            self.assertEqual(providers.load_profile().max_output_tokens, 16384)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("JMB_MAX_OUTPUT_TOKENS", None)
            self.assertEqual(providers.load_profile().max_output_tokens, 8192)

    def test_max_tokens_emits_truncation_warning(self) -> None:
        events: list[tuple[str, object]] = []
        turn = providers.Turn(blocks=[{"type": "text", "text": "半句话"}],
                              usage={"output": 8192}, stop_reason="max_tokens")
        profile = providers.ProviderProfile("t", "anthropic", "http://x", "m")
        with mock.patch("jmb.chat.providers.stream_turn", return_value=turn):
            chat._stream_turn(profile, None, "", [],
                              [{"role": "user", "content": "hi"}], mock.Mock(), None, None,
                              lambda kind, data: events.append((kind, data)))
        self.assertTrue(any(kind == "warning" and "截断" in str(data)
                            for kind, data in events))

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

from __future__ import annotations

import os
import unittest
from unittest import mock

from jmb import chat, compact, providers


def _tool_pair(tool_id: str, name: str, result: str) -> list[dict]:
    return [
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": tool_id, "name": name, "input": {"path": "a.py"}}]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": tool_id, "content": result}]},
    ]


class MaskingTest(unittest.TestCase):
    def test_old_read_results_are_masked_recent_and_commands_kept(self) -> None:
        history = _tool_pair("t1", "read_code", "x" * 1000)
        history += _tool_pair("t2", "run_command", "y" * 1000)
        history += [{"role": "assistant", "content": [{"type": "text", "text": "ok"}]},
                    {"role": "user", "content": "继续"}] * 6
        history += _tool_pair("t3", "grep", "z" * 1000)
        chat._mask_old_tool_results(history, keep=4)
        self.assertIn("已清理", history[1]["content"][0]["content"])
        self.assertEqual(history[3]["content"][0]["content"], "y" * 1000)
        self.assertEqual(history[-1]["content"][0]["content"], "z" * 1000)


class CompactTest(unittest.TestCase):
    def test_render_skips_thinking_and_keeps_paths(self) -> None:
        history = [
            {"role": "assistant", "content": [
                {"type": "thinking", "thinking": "secret"},
                {"type": "text", "text": "改了 /tmp/a.py"},
                {"type": "tool_use", "id": "t1", "name": "read_code",
                 "input": {"path": "/tmp/a.py"}}]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t1",
                 "content": "Traceback: boom"}]},
        ]
        text = compact.render(history)
        self.assertIn("/tmp/a.py", text)
        self.assertIn("Traceback: boom", text)
        self.assertNotIn("secret", text)

    def test_cut_starts_at_assistant_and_keeps_recent(self) -> None:
        history: list[dict] = []
        for index in range(12):
            history.append({"role": "user", "content": f"u{index}"})
            history.append({"role": "assistant", "content": [{"type": "text", "text": "a"}]})
        cut = compact.cut_index(history, keep=6)
        self.assertIsNotNone(cut)
        assert cut is not None
        self.assertEqual(history[cut]["role"], "assistant")
        self.assertGreaterEqual(len(history) - cut, 6)

    def test_apply_puts_summary_first_and_keeps_roles(self) -> None:
        history: list[dict] = []
        for index in range(12):
            history.append({"role": "user", "content": f"u{index}"})
            history.append({"role": "assistant", "content": [{"type": "text", "text": "a"}]})
        result = compact.apply(history, "摘要" * 30)
        self.assertIsNotNone(result)
        self.assertEqual(history[0]["role"], "user")
        self.assertIn("系统生成的上下文摘要", history[0]["content"])
        self.assertEqual(history[1]["role"], "assistant")

    def test_summarize_uses_provider_complete(self) -> None:
        history = [{"role": "user", "content": "需求：" + "x" * 300},
                   {"role": "assistant", "content": [{"type": "text", "text": "收到"}]}]
        with mock.patch("jmb.providers.complete", return_value="## 目标\n" + "做完" * 30) as call:
            summary = compact.summarize(
                providers.ProviderProfile("t", "anthropic", "http://x", "m"), history)
        self.assertIn("## 目标", summary)
        self.assertTrue(call.called)

    def test_summarize_rejects_empty(self) -> None:
        history = [{"role": "user", "content": "需求：" + "x" * 300},
                   {"role": "assistant", "content": [{"type": "text", "text": "收到"}]}]
        with mock.patch("jmb.providers.complete", return_value=""):
            with self.assertRaises(ValueError):
                compact.summarize(
                    providers.ProviderProfile("t", "anthropic", "http://x", "m"), history)


class BudgetConfigTest(unittest.TestCase):
    def test_budget_for_model(self) -> None:
        self.assertEqual(providers.budget_for_model("spark-x2.6"), (1_000_000, 120_000))
        self.assertEqual(providers.budget_for_model("gpt-4o-mini"), (128_000, 30_000))

    def test_env_overrides_budget(self) -> None:
        with mock.patch.dict(os.environ, {"JMB_INPUT_BUDGET": "5000"}, clear=False):
            profile = providers.load_profile()
        self.assertEqual(profile.input_budget, 5000)


if __name__ == "__main__":
    unittest.main()

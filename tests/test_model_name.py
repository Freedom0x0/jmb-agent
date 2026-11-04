from __future__ import annotations

import os
import unittest
from unittest import mock

from jmb import providers


class ModelNameTest(unittest.TestCase):
    def test_xf_yun_strips_1m_suffix(self) -> None:
        base = "https://maas-api.cn-huabei-1.xf-yun.com/anthropic"
        self.assertEqual(providers._request_model("spark-x2.6[1M]", base),
                         "spark-x2.6")
        self.assertEqual(providers._request_model("spark-x2.6[1m]", base),
                         "spark-x2.6")

    def test_other_endpoints_keep_model_name(self) -> None:
        self.assertEqual(
            providers._request_model("some-model[1M]", "https://api.example.com/v1"),
            "some-model[1M]")

    def test_profile_strips_suffix_but_keeps_1m_budget(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        from jmb import config

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "jmbhome"
            home.mkdir()
            (home / "config.json").write_text(json.dumps({
                "model": "spark-x2.6[1M]",
                "base_url": "https://maas-api.cn-huabei-1.xf-yun.com/anthropic",
                "token": "sk-test",
            }), encoding="utf-8")
            with mock.patch.dict(os.environ, {"JMB_HOME": str(home)}, clear=False):
                profile = providers.load_profile()
        self.assertEqual(profile.model, "spark-x2.6")
        self.assertEqual(profile.context_window, 1_000_000)
        self.assertEqual(profile.input_budget, 120_000)

    def test_budget_layers_env_over_config_over_table(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "jmbhome"
            home.mkdir()
            (home / "config.json").write_text(json.dumps({
                "model": "my-model", "context_window": 123456, "input_budget": 789}),
                encoding="utf-8")
            with mock.patch.dict(os.environ, {"JMB_HOME": str(home)}, clear=False):
                profile = providers.load_profile()
            self.assertEqual((profile.context_window, profile.input_budget),
                             (123456, 789))
            # env 仍然盖过配置层（调优 env 保留，D49 只收编模型/端点/key）
            with mock.patch.dict(os.environ, {"JMB_HOME": str(home),
                                              "JMB_CONTEXT_WINDOW": "999"}, clear=False):
                profile = providers.load_profile()
            self.assertEqual(profile.context_window, 999)
            # 都没写 → 模型表/默认
            empty = Path(tmp) / "empty"
            empty.mkdir()
            with mock.patch.dict(os.environ, {"JMB_HOME": str(empty)}, clear=False):
                profile = providers.load_profile()
            self.assertEqual(profile.context_window, 128_000)
            self.assertEqual(profile.input_budget, 30_000)


if __name__ == "__main__":
    unittest.main()

"""config.py 的模型/端点/凭据解析（D49）：只认 jmb/config.json，不读环境变量。"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jmb import config


class ModelConfigChainTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name) / "jmbhome"
        self.home.mkdir(parents=True)
        # 全部挂上哨兵值：解析结果里出现任何一个，就说明链读到了环境
        self._patch = mock.patch.dict(os.environ, {
            "JMB_HOME": str(self.home),
            "ANTHROPIC_MODEL": "env-model",
            "ANTHROPIC_BASE_URL": "https://env.example",
            "ANTHROPIC_AUTH_TOKEN": "sk-env",
            "ANTHROPIC_API_KEY": "sk-env-2",
        }, clear=False)
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def _write_config(self, data: dict) -> None:
        (self.home / "config.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_config_is_the_only_source(self) -> None:
        self._write_config({"model": "jmb-model", "base_url": "https://jmb.example",
                            "token": "sk-jmb"})
        self.assertEqual(config.resolve_model(),
                         config.Resolved("jmb-model", "jmb/config.json"))
        self.assertEqual(config.resolve_base_url(),
                         config.Resolved("https://jmb.example", "jmb/config.json"))
        self.assertEqual(config.resolve_token(),
                         config.Resolved("sk-jmb", "jmb/config.json"))

    def test_env_is_ignored(self) -> None:
        # 配置空 + 环境有哨兵值：走默认/missing，环境的 key 和模型一个都不读
        self.assertEqual(config.resolve_model(),
                         config.Resolved(config.DEFAULT_MODEL, "default"))
        self.assertEqual(config.resolve_base_url().source, "default")
        self.assertEqual(config.resolve_token(), config.Resolved("", "missing"))

    def test_save_merges_non_empty_and_keeps_other_keys(self) -> None:
        self._write_config({"model": "old", "note": "keep"})
        config.save_model_config(model="", base_url="https://new", token="")
        data = json.loads((self.home / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(data, {"model": "old", "note": "keep", "base_url": "https://new"})

        config.save_model_config(model="m2", base_url="", token="sk-x")
        data = json.loads((self.home / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(data, {"model": "m2", "note": "keep",
                                "base_url": "https://new", "token": "sk-x"})

    def test_save_keeps_positive_ints_only(self) -> None:
        config.save_model_config(model="m", base_url="", token="",
                                 context_window=1_000_000, input_budget=0)
        data = json.loads((self.home / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(data["context_window"], 1_000_000)
        self.assertNotIn("input_budget", data)
        config.save_model_config(model="", base_url="", token="",
                                 context_window="abc", input_budget=789)
        data = json.loads((self.home / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(data["context_window"], 1_000_000)  # 非法值不覆盖
        self.assertEqual(data["input_budget"], 789)

    def test_load_ignores_broken_json(self) -> None:
        (self.home / "config.json").write_text("{oops", encoding="utf-8")
        self.assertEqual(config.load_model_config(), {})


if __name__ == "__main__":
    unittest.main()

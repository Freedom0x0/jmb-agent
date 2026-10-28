from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


class MemoryConfirmTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self._old_home = os.environ.get("JMB_HOME")
        os.environ["JMB_HOME"] = str(Path(self.tmp.name) / "home")

    def tearDown(self) -> None:
        if self._old_home is None:
            os.environ.pop("JMB_HOME", None)
        else:
            os.environ["JMB_HOME"] = self._old_home
        self.tmp.cleanup()

    def test_ask_callback_approves(self) -> None:
        from jmb.memory import FactMemory

        memory = FactMemory()
        memory.propose("测试事实：app 收尾确认。")
        result = memory.confirm_pending(interactive=True, ask=lambda items, more: "ok")
        self.assertIn("已记进长期记忆", result)
        self.assertIn("app 收尾确认", memory.search("app 收尾确认"))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jmb import prefix, seeds


class PrefixTest(unittest.TestCase):
    def test_identity_lock_is_first_and_last(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"JMB_HOME": tmp}):
                system = prefix.build_system()
        self.assertTrue(system.startswith(prefix.IDENTITY_LOCK))
        self.assertTrue(system.endswith(prefix._IDENTITY_TAIL))
        self.assertIn("江慕白", system)
        self.assertIn("狐狸眼", system)  # SOUL 缺失时回退到 seeds，而不是裸奔

    def test_soul_stays_between_lock_and_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spaces = Path(tmp) / "spaces" / "local"
            (spaces / "persona").mkdir(parents=True)
            (spaces / "ledger").mkdir(parents=True)
            (spaces / "persona" / "SOUL.md").write_text("SOUL-MARKER", encoding="utf-8")
            (spaces / "persona" / "RELATIONSHIP.md").write_text(
                "REL-MARKER", encoding="utf-8")
            (spaces / "ledger" / "LEARNING.md").write_text("LEARN-MARKER", encoding="utf-8")
            with mock.patch.dict(os.environ, {"JMB_HOME": tmp}):
                system = prefix.build_system()
        self.assertLess(system.index(prefix.IDENTITY_LOCK), system.index("SOUL-MARKER"))
        self.assertLess(system.index("SOUL-MARKER"), system.index("LEARN-MARKER"))
        self.assertLess(system.index("LEARN-MARKER"), system.index("REL-MARKER"))
        self.assertLess(system.index("REL-MARKER"), system.index(prefix._IDENTITY_TAIL))

    def test_seed_persona_contains_persona_core(self) -> None:
        self.assertIn("江慕白", seeds.SOUL_V0)
        self.assertIn("二十六岁", seeds.SOUL_V0)
        self.assertIn("狐狸眼", seeds.SOUL_V0)
        self.assertIn("AI科技公司", seeds.SOUL_V0)


if __name__ == "__main__":
    unittest.main()

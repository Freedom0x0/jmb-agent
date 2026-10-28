from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from jmb import grants, search


class SearchToolsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._old_home = os.environ.get("JMB_HOME")
        os.environ["JMB_HOME"] = str(self.root / "home")
        grants.reset_session()
        (self.root / "a.py").write_text("def foo():\n    return 1\n", encoding="utf-8")
        (self.root / "b.txt").write_text("foo bar\nFOO baz\n", encoding="utf-8")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "c.md").write_text("hello foo\n", encoding="utf-8")
        (self.root / ".git").mkdir()
        (self.root / ".git" / "config").write_text("foo secret\n", encoding="utf-8")
        (self.root / "node_modules").mkdir()
        (self.root / "node_modules" / "x.py").write_text("foo\n", encoding="utf-8")
        (self.root / "platform-group-projects").mkdir()
        (self.root / "platform-group-projects" / "x.py").write_text("foo\n", encoding="utf-8")
        (self.root / "bin.dat").write_bytes(b"\x00foo")
        spaces = Path(os.environ["JMB_HOME"]) / "spaces" / "local" / "persona"
        spaces.mkdir(parents=True)
        (spaces / "SOUL.md").write_text("foo secret\n", encoding="utf-8")

    def tearDown(self) -> None:
        grants.reset_session()
        if self._old_home is None:
            os.environ.pop("JMB_HOME", None)
        else:
            os.environ["JMB_HOME"] = self._old_home
        self.tmp.cleanup()

    def test_grep_glob(self) -> None:
        result = search.grep("foo", str(self.root), glob="*.py")
        self.assertIn("a.py", result)
        self.assertNotIn("b.txt", result)
        self.assertNotIn("c.md", result)

    def test_grep_case_sensitive(self) -> None:
        result = search.grep("FOO", str(self.root), glob="*.txt")
        self.assertIn("b.txt", result)
        self.assertIn("FOO baz", result)
        self.assertNotIn("a.py", result)
        result = search.grep("FOO", str(self.root), glob="*.txt", case_sensitive=False)
        self.assertIn("foo bar", result)

    def test_grep_skips_ignored_denied_and_binary(self) -> None:
        result = search.grep("foo", str(self.root))
        self.assertIn("a.py", result)
        self.assertIn("b.txt", result)
        self.assertNotIn(".git", result)
        self.assertNotIn("node_modules", result)
        self.assertNotIn("platform-group-projects", result)
        self.assertNotIn("spaces", result)
        self.assertNotIn("bin.dat", result)

    def test_grep_max_results(self) -> None:
        for index in range(5):
            (self.root / f"m{index}.py").write_text("foo\n", encoding="utf-8")
        result = search.grep("foo", str(self.root), glob="m*.py", max_results=2)
        self.assertIn("达到 max_results=2", result)

    def test_grep_invalid_regex(self) -> None:
        with self.assertRaises(search.SearchError):
            search.grep("(", str(self.root))

    def test_grep_denied_root(self) -> None:
        with self.assertRaises(search.SearchError):
            search.grep("foo", str(self.root / "platform-group-projects"))

    def test_find(self) -> None:
        result = search.find(str(self.root), "*.md")
        self.assertIn("c.md", result)
        self.assertNotIn("a.py", result)

    def test_find_skips_denied(self) -> None:
        result = search.find(str(self.root), "*")
        self.assertNotIn(".git", result)
        self.assertNotIn("node_modules", result)
        self.assertNotIn("platform-group-projects", result)
        self.assertNotIn("spaces", result)

    def test_missing_path(self) -> None:
        with self.assertRaises(search.SearchError):
            search.find(str(self.root / "nope"), "*")


if __name__ == "__main__":
    unittest.main()

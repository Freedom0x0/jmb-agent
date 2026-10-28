from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jmb import code, grants

BOM = b"\xef\xbb\xbf"


class CodeToolsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._old_home = os.environ.get("JMB_HOME")
        os.environ["JMB_HOME"] = str(self.root / "home")
        grants.reset_session()
        self.session = code.CodeSession()

    def tearDown(self) -> None:
        self.session.end_turn()
        grants.reset_session()
        if self._old_home is None:
            os.environ.pop("JMB_HOME", None)
        else:
            os.environ["JMB_HOME"] = self._old_home
        self.tmp.cleanup()

    def test_edit_preserves_bom_and_crlf(self) -> None:
        target = self.root / "a.py"
        target.write_bytes(BOM + b"print('a')\r\nprint('b')\r\n")
        self.session.begin_turn()
        result = code.edit_file(
            str(target), [{"old_text": "print('b')", "new_text": "print('c')"}], self.session)
        self.assertIn("print('c')", result)
        data = target.read_bytes()
        self.assertTrue(data.startswith(BOM))
        self.assertIn(b"print('c')\r\n", data)
        self.assertNotIn(b"print('b')", data)

    def test_edit_duplicate_rejected(self) -> None:
        target = self.root / "dup.py"
        target.write_text("x\nx\n", encoding="utf-8")
        with self.assertRaises(code.CodeError):
            code.edit_file(str(target), [{"old_text": "x", "new_text": "y"}], self.session)

    def test_edit_overlap_rejected(self) -> None:
        target = self.root / "overlap.py"
        target.write_text("abcdef", encoding="utf-8")
        edits = [{"old_text": "abcd", "new_text": "X"},
                 {"old_text": "cdef", "new_text": "Y"}]
        with self.assertRaises(code.CodeError):
            code.edit_file(str(target), edits, self.session)

    def test_edit_no_change_rejected(self) -> None:
        target = self.root / "same.py"
        target.write_text("abc", encoding="utf-8")
        with self.assertRaises(code.CodeError):
            code.edit_file(str(target), [{"old_text": "abc", "new_text": "abc"}], self.session)

    def test_edit_fuzzy_preserves_unchanged_lines(self) -> None:
        target = self.root / "fuzzy.py"
        target.write_text("hello  \nworld\n", encoding="utf-8")
        self.session.begin_turn()
        code.edit_file(str(target), [{"old_text": "hello\nworld", "new_text": "hi\nworld"}],
                       self.session)
        self.assertEqual(target.read_text(encoding="utf-8"), "hi\nworld\n")

    def test_write_and_undo_new_file(self) -> None:
        target = self.root / "new.py"
        self.session.begin_turn()
        code.write_file(str(target), "print('x')\n", self.session)
        self.session.end_turn()
        self.assertTrue(target.is_file())
        message = self.session.undo_last_turn()
        self.assertIn("已删除新建", message)
        self.assertFalse(target.exists())

    def test_write_and_undo_existing_file(self) -> None:
        target = self.root / "old.py"
        target.write_text("old\n", encoding="utf-8")
        self.session.begin_turn()
        code.write_file(str(target), "new\n", self.session)
        self.session.end_turn()
        self.session.undo_last_turn()
        self.assertEqual(target.read_text(encoding="utf-8"), "old\n")

    def test_undo_refuses_external_change(self) -> None:
        target = self.root / "changed.py"
        target.write_text("old\n", encoding="utf-8")
        self.session.begin_turn()
        code.write_file(str(target), "new\n", self.session)
        self.session.end_turn()
        target.write_text("external\n", encoding="utf-8")
        message = self.session.undo_last_turn()
        self.assertIn("之后被改过", message)
        self.assertEqual(target.read_text(encoding="utf-8"), "external\n")

    def test_deny_company_repo(self) -> None:
        target = self.root / "platform-group-projects" / "x.py"
        with self.assertRaises(code.CodeError):
            code.write_file(str(target), "x", self.session)

    def test_deny_jmb_spaces(self) -> None:
        target = Path(os.environ["JMB_HOME"]) / "spaces" / "local" / "persona" / "SOUL.md"
        with self.assertRaises(code.CodeError):
            code.write_file(str(target), "x", self.session)

    def test_deny_git_dir(self) -> None:
        target = self.root / ".git" / "config"
        with self.assertRaises(code.CodeError):
            code.write_file(str(target), "x", self.session)

    def test_authorize_write_is_session_scoped(self) -> None:
        target = self.root / "grant.py"
        with mock.patch("builtins.input", return_value="y"):
            ok, _ = grants.authorize_write(str(target), interactive=True)
        self.assertTrue(ok)
        with mock.patch("builtins.input", side_effect=AssertionError("should not prompt again")):
            ok, _ = grants.authorize_write(str(target), interactive=True)
        self.assertTrue(ok)

    def test_authorize_write_denied(self) -> None:
        target = self.root / "deny.py"
        with mock.patch("builtins.input", return_value="n"):
            ok, _ = grants.authorize_write(str(target), interactive=True)
        self.assertFalse(ok)

    def test_authorize_exec_is_session_scoped(self) -> None:
        with mock.patch("builtins.input", return_value="y"):
            ok, _ = grants.authorize_exec("echo hi", str(self.root), interactive=True)
        self.assertTrue(ok)
        with mock.patch("builtins.input", side_effect=AssertionError("should not prompt again")):
            ok, _ = grants.authorize_exec("echo hi", str(self.root), interactive=True)
        self.assertTrue(ok)

    def test_read_offset_and_limit(self) -> None:
        target = self.root / "lines.py"
        target.write_text("a\nb\nc\n", encoding="utf-8")
        result = grants.perform(str(target), "read", offset=2, limit=1)
        self.assertIn("第 2-2 行", result)
        self.assertIn("b", result)
        self.assertNotIn("\na\n", result)

    def test_read_binary_rejected(self) -> None:
        target = self.root / "bin.dat"
        target.write_bytes(b"a\x00b")
        result = grants.perform(str(target), "read")
        self.assertIn("二进制", result)

    def test_run_command(self) -> None:
        self.session.begin_turn()
        result = code.run_command("echo hello", str(self.root), 10, self.session)
        self.assertIn("exit_code=0", result)
        self.assertIn("hello", result)

    def test_command_output_truncated(self) -> None:
        command = f'"{sys.executable}" -c "print(\'x\'*100000)"'
        self.session.begin_turn()
        result = code.run_command(command, str(self.root), 30, self.session)
        self.assertIn("输出已截断", result)
        self.assertIn("完整输出", result)

    def test_command_timeout(self) -> None:
        self.session.begin_turn()
        result = code.run_command("sleep 5", str(self.root), 1, self.session)
        self.assertIn("TIMEOUT", result)

    def test_chat_dispatch_wiring(self) -> None:
        from jmb import chat

        target = self.root / "wired.py"
        self.session.begin_turn()
        with mock.patch("sys.stdin.isatty", return_value=True), \
                mock.patch("builtins.input", return_value="y"):
            message = chat._dispatch(
                "write_file", {"path": str(target), "content": "print('x')\n"},
                None, self.session)
        self.session.end_turn()
        self.assertIn("OK: wrote", message)
        self.assertTrue(target.is_file())

        grants.grant(str(target))
        self.assertEqual(
            grants.authorize(str(target), "read", interactive=False)[0], True)
        read_back = chat._dispatch(
            "read_code", {"path": str(target), "action": "read", "offset": 1, "limit": 10},
            None, self.session)
        self.assertIn("print('x')", read_back)

        self.session.begin_turn()
        message = chat._dispatch(
            "edit_file",
            {"path": str(target), "edits": [{"old_text": "print('x')", "new_text": "print('y')"}]},
            None, self.session)
        self.session.end_turn()
        self.assertIn("OK: edited", message)
        self.assertIn("print('y')", target.read_text(encoding="utf-8"))

        self.session.begin_turn()
        with mock.patch("sys.stdin.isatty", return_value=True), \
                mock.patch("builtins.input", return_value="y"):
            message = chat._dispatch(
                "run_command", {"command": "echo wired", "cwd": str(self.root)},
                None, self.session)
        self.session.end_turn()
        self.assertIn("wired", message)


if __name__ == "__main__":
    unittest.main()

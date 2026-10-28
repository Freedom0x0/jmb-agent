from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jmb import code, grants


class SandboxTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self._old = {
            name: os.environ.get(name)
            for name in ("JMB_HOME", "JMB_SANDBOX", "JMB_SANDBOX_IMAGE", "JMB_SANDBOX_NETWORK")
        }
        os.environ["JMB_HOME"] = str(Path(self.tmp.name) / "home")
        os.environ.pop("JMB_SANDBOX", None)
        os.environ.pop("JMB_SANDBOX_IMAGE", None)
        os.environ.pop("JMB_SANDBOX_NETWORK", None)
        grants.reset_session()

    def tearDown(self) -> None:
        for name, value in self._old.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self.tmp.cleanup()

    def test_default_mode_is_docker(self) -> None:
        self.assertEqual(code.sandbox_mode(), "docker")

    def test_explicit_host_mode(self) -> None:
        os.environ["JMB_SANDBOX"] = "host"
        self.assertEqual(code.sandbox_mode(), "host")

    def test_docker_argv_hardens_container(self) -> None:
        os.environ["JMB_SANDBOX_IMAGE"] = "example/image:1"
        cwd = Path(self.tmp.name)
        argv, name = code._docker_argv("pytest -q", cwd)
        self.assertEqual(argv[0], "docker")
        self.assertIn("--network", argv)
        self.assertEqual(argv[argv.index("--network") + 1], "none")
        self.assertIn("--read-only", argv)
        self.assertIn("example/image:1", argv)
        self.assertIn(f"{cwd}:/work", argv)
        self.assertEqual(argv[-3:], ["sh", "-lc", "pytest -q"])
        self.assertTrue(name.startswith("jmb-cmd-"))

    def test_summary_reports_image_and_network(self) -> None:
        os.environ["JMB_SANDBOX_IMAGE"] = "example/image:1"
        summary = code.sandbox_summary()
        self.assertIn("docker", summary)
        self.assertIn("example/image:1", summary)
        self.assertIn("none", summary)

    def test_summary_reports_daemon_state(self) -> None:
        os.environ["JMB_SANDBOX_IMAGE"] = "example/image:1"
        with mock.patch("jmb.code.docker_daemon_running", return_value=False):
            summary = code.sandbox_summary(check_daemon=True)
        self.assertIn("daemon=未运行", summary)

    def test_missing_docker_fails_closed(self) -> None:
        os.environ["JMB_SANDBOX"] = "docker"
        with mock.patch("jmb.code.shutil.which", return_value=None):
            with self.assertRaises(code.CodeError):
                code.run_command("echo hi", self.tmp.name, 10, code.CodeSession())


if __name__ == "__main__":
    unittest.main()

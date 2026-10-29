from __future__ import annotations

import unittest

try:
    import tkinter as tk

    HAS_TK = True
except Exception:  # noqa: BLE001
    HAS_TK = False


@unittest.skipUnless(HAS_TK, "tkinter unavailable")
class AppSmokeTest(unittest.TestCase):
    def test_pet_window_builds_and_renders(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("no display")
        root.withdraw()
        try:
            from jmb.app.pet import PetWindow

            pet = PetWindow(root)
            pet.win.withdraw()
            pet.set_state("thinking")
            pet.bubble("hello", 1000)
            pet.win.update_idletasks()
            self.assertGreaterEqual(len(pet.canvas.find_all()), 1)
            self.assertTrue(pet._sprite_frames)
            pet.close()
        finally:
            root.destroy()

    def test_main_window_builds_without_worker(self) -> None:
        try:
            from jmb.app.main import MainWindow

            window = MainWindow(start_worker=False)
        except tk.TclError:
            self.skipTest("no display")
        try:
            window.withdraw()
            window.pet.win.withdraw()
            window._append("hello", "user")
            self.assertIn("hello", window.text.get("1.0", "end"))
        finally:
            window.close()

    def test_brief_bubble_fires_once(self) -> None:
        import os
        import tempfile
        from datetime import date
        from pathlib import Path

        old = os.environ.get("JMB_HOME")
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["JMB_HOME"] = str(Path(tmp) / "home")
            try:
                try:
                    from jmb import config
                    from jmb.app.main import MainWindow

                    window = MainWindow(start_worker=False)
                except tk.TclError:
                    self.skipTest("no display")
                try:
                    window.withdraw()
                    window.pet.win.withdraw()
                    today = date.today()
                    state = config.brief_state_path(today)
                    state.parent.mkdir(parents=True, exist_ok=True)
                    state.write_text('{"ok": true}', encoding="utf-8")
                    md = config.jmb_home() / "state" / f"brief-{today.isoformat()}.md"
                    md.write_text("# jmb 每日清单", encoding="utf-8")
                    window._check_brief()
                    self.assertIn("清单", window.pet.bubble_window.label.cget("text"))
                    self.assertIsNotNone(window.pet.bubble_window._on_click)
                    self.assertIn("今天的清单好了", window.text.get("1.0", "end"))
                    window.pet.bubble_window.label.config(text="sentinel")
                    window._check_brief()
                    self.assertEqual(window.pet.bubble_window.label.cget("text"), "sentinel")
                    self.assertEqual(window.text.get("1.0", "end").count("今天的清单好了"), 1)
                    self.assertTrue((config.jmb_home() / "state" / "brief-seen.json").exists())
                finally:
                    window.close()
            finally:
                if old is None:
                    os.environ.pop("JMB_HOME", None)
                else:
                    os.environ["JMB_HOME"] = old

    def test_pet_click_opens_chat_and_bubble_click_fires(self) -> None:
        try:
            from jmb.app.main import MainWindow

            window = MainWindow(start_worker=False)
        except tk.TclError:
            self.skipTest("no display")
        try:
            from types import SimpleNamespace

            window.withdraw()
            window.pet.win.withdraw()
            calls: list[str] = []
            window.pet.on_click = lambda: calls.append("pet")
            window.pet._press(SimpleNamespace(x_root=100, y_root=100))
            window.pet._release(SimpleNamespace(x_root=102, y_root=101))
            self.assertEqual(calls, ["pet"])
            window.pet._press(SimpleNamespace(x_root=100, y_root=100))
            window.pet._release(SimpleNamespace(x_root=140, y_root=160))
            self.assertEqual(calls, ["pet"])

            window.pet.bubble("hi", 1000, on_click=lambda: calls.append("bubble"))
            window.pet.bubble_window._clicked()
            self.assertEqual(calls, ["pet", "bubble"])
            self.assertFalse(window.pet.bubble_window.win.winfo_ismapped())
        finally:
            window.close()

    def test_brief_notify_invokes_powershell(self) -> None:
        import sys
        from unittest import mock

        if sys.platform != "win32":
            self.skipTest("windows-only toast")
        from jmb import brief

        with mock.patch("jmb.brief.subprocess.run") as run:
            brief._notify_done(8)
        run.assert_called_once()
        self.assertIn("8", run.call_args.args[0][-1])

    def test_chat_worker_ready_and_stop(self) -> None:
        import os
        import tempfile
        from pathlib import Path

        from jmb import config

        if not config.resolve_token().value:
            self.skipTest("no model token")
        old = os.environ.get("JMB_HOME")
        worker = None
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["JMB_HOME"] = str(Path(tmp) / "home")
            try:
                from jmb.app.main import ChatWorker

                worker = ChatWorker()
                worker.start()
                kind, data = worker.events.get(timeout=90)
                self.assertEqual(kind, "ready")
                self.assertIn("tid", data)
            finally:
                if worker is not None:
                    worker.stop()
                if old is None:
                    os.environ.pop("JMB_HOME", None)
                else:
                    os.environ["JMB_HOME"] = old


if __name__ == "__main__":
    unittest.main()

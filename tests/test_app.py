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

    def test_chat_worker_ready_and_stop(self) -> None:
        import os
        import tempfile
        from pathlib import Path

        from jmb import config

        if not config.resolve_token().value:
            self.skipTest("no model token")
        old = os.environ.get("JMB_HOME")
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["JMB_HOME"] = str(Path(tmp) / "home")
            try:
                from jmb.app.main import ChatWorker

                worker = ChatWorker()
                worker.start()
                kind, data = worker.events.get(timeout=20)
                self.assertEqual(kind, "ready")
                self.assertIn("tid", data)
                worker.stop()
            finally:
                if old is None:
                    os.environ.pop("JMB_HOME", None)
                else:
                    os.environ["JMB_HOME"] = old


if __name__ == "__main__":
    unittest.main()

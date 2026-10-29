"""内置桌宠渲染层（D33）：Tkinter 透明置顶窗口 + 简单动画 + 气泡。

v1 用 Canvas 画占位形象，不依赖 Petdex 素材；后续可把 _draw 换成
pet.json + spritesheet 的 8x9/8x11 网格。Windows 用 -transparentcolor
做透明背景；其他平台会退化成纯色背景。
"""
from __future__ import annotations

import json
import math
import tkinter as tk
from pathlib import Path

STATE_COLORS = {
    "idle": "#5eead4",
    "thinking": "#93c5fd",
    "searching": "#c4b5fd",
    "working": "#fdba74",
    "waiting": "#fde68a",
    "failed": "#fca5a5",
    "waving": "#86efac",
}
TRANSPARENT = "#010203"
ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "pets" / "jmb"
STATE_ROWS = {
    "idle": 0,
    "thinking": 1,
    "searching": 2,
    "working": 3,
    "waving": 4,
    "failed": 5,
    "waiting": 0,
}
FRAME_W, FRAME_H = 192, 208


def _shade(hex_color: str, factor: float) -> str:
    raw = hex_color.lstrip("#")
    if len(raw) != 6:
        return hex_color
    parts = [max(0, min(255, int(int(raw[i:i + 2], 16) * factor))) for i in (0, 2, 4)]
    return "#" + "".join(f"{part:02x}" for part in parts)


class BubbleWindow:
    def __init__(self, master: tk.Misc) -> None:
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#f5f5f5")
        self.label = tk.Label(
            self.win, text="", bg="#f5f5f5", fg="#1e1f22",
            wraplength=300, justify="left", padx=12, pady=10,
            font=("Microsoft YaHei UI", 10))
        self.label.pack(fill="both", expand=True)
        self.label.bind("<Button-1>", self._clicked)
        self.win.withdraw()
        self._after: str | None = None
        self._on_click = None

    def show(self, text: str, x: int, y: int, milliseconds: int = 5000,
             on_click=None) -> None:
        self._on_click = on_click
        self.label.config(text=text)
        self.win.update_idletasks()
        width = min(340, max(200, self.label.winfo_reqwidth() + 24))
        self.label.config(wraplength=width - 24)
        self.win.geometry(f"+{x}+{y}")
        self.win.deiconify()
        self.win.lift()
        if self._after is not None:
            self.win.after_cancel(self._after)
        self._after = self.win.after(max(1000, milliseconds), self.win.withdraw)

    def _clicked(self, _event=None) -> None:
        if self._on_click is not None:
            callback, self._on_click = self._on_click, None
            self.win.withdraw()
            callback()

    def move(self, x: int, y: int) -> None:
        self.win.geometry(f"+{x}+{y}")

    def close(self) -> None:
        if self._after is not None:
            try:
                self.win.after_cancel(self._after)
            except tk.TclError:
                pass
        self.win.destroy()


class PetWindow:
    def __init__(self, master: tk.Misc) -> None:
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=TRANSPARENT)
        try:
            self.win.attributes("-transparentcolor", TRANSPARENT)
        except tk.TclError:
            pass
        self.width, self.height = 220, 250
        self.canvas = tk.Canvas(
            self.win, width=self.width, height=self.height,
            bg=TRANSPARENT, highlightthickness=0)
        self.canvas.pack()
        self.state = "idle"
        self.tick = 0
        self.blink = False
        self.on_click = None
        self._drag: tuple[int, int] | None = None
        self._press_pos: tuple[int, int] | None = None
        self._after: str | None = None
        self._closed = False
        self._sprite_frames = self._load_sprites()
        self.bubble_window = BubbleWindow(master)
        self._place()
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._move)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self._animate()

    def _load_sprites(self) -> dict[str, list]:
        try:
            from PIL import Image, ImageTk

            meta = json.loads((ASSET_DIR / "pet.json").read_text(encoding="utf-8"))
            sheet = Image.open(ASSET_DIR / meta["spritesheetPath"]).convert("RGBA")
            frames: dict[str, list] = {}
            for state, row in STATE_ROWS.items():
                frames[state] = []
                for col in range(8):
                    box = (col * FRAME_W, row * FRAME_H, (col + 1) * FRAME_W, (row + 1) * FRAME_H)
                    frames[state].append(ImageTk.PhotoImage(sheet.crop(box)))
            return frames
        except Exception:  # noqa: BLE001 —— 没有 Pillow/素材时回退 Canvas
            return {}

    def _place(self) -> None:
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        self.win.geometry(f"{self.width}x{self.height}+{sw - self.width - 40}+{sh - self.height - 80}")

    def _draw(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        frames = self._sprite_frames.get(self.state) or self._sprite_frames.get("idle")
        if frames:
            canvas.create_image(self.width // 2, self.height // 2,
                                image=frames[(self.tick // 3) % len(frames)])
            return
        color = STATE_COLORS.get(self.state, STATE_COLORS["idle"])
        bob = int(math.sin(self.tick / 7.0) * 3) if self.state != "failed" else 0
        dark = _shade(color, 0.65)
        canvas.create_oval(62, 205, 158, 221, fill="#2b2d31", outline="")
        canvas.create_oval(44, 54 + bob, 176, 202 + bob, fill=color, outline=dark, width=2)
        canvas.create_oval(58, 40 + bob, 100, 82 + bob, fill=_shade(color, 0.9), outline=dark)
        canvas.create_oval(120, 40 + bob, 162, 82 + bob, fill=_shade(color, 0.9), outline=dark)
        canvas.create_oval(69, 51 + bob, 89, 71 + bob, fill=_shade(color, 1.08), outline="")
        canvas.create_oval(131, 51 + bob, 151, 71 + bob, fill=_shade(color, 1.08), outline="")

        eye = "#1e1f22"
        if self.state == "failed":
            for x1, x2 in ((83, 101), (119, 137)):
                canvas.create_line(x1, 111 + bob, x2, 129 + bob, fill=eye, width=3)
                canvas.create_line(x2, 111 + bob, x1, 129 + bob, fill=eye, width=3)
        elif self.blink:
            canvas.create_line(84, 122 + bob, 100, 122 + bob, fill=eye, width=3)
            canvas.create_line(120, 122 + bob, 136, 122 + bob, fill=eye, width=3)
        else:
            canvas.create_oval(84, 112 + bob, 102, 136 + bob, fill=eye, outline="")
            canvas.create_oval(120, 112 + bob, 138, 136 + bob, fill=eye, outline="")
            canvas.create_oval(90, 117 + bob, 96, 125 + bob, fill="white", outline="")
            canvas.create_oval(126, 117 + bob, 132, 125 + bob, fill="white", outline="")

        if self.state == "thinking":
            canvas.create_line(102, 153 + bob, 118, 153 + bob, fill=eye, width=2)
        elif self.state == "searching":
            canvas.create_arc(101, 145 + bob, 119, 161 + bob, start=0, extent=180,
                              style=tk.ARC, outline=eye, width=2)
            canvas.create_oval(136, 72 + bob, 154, 90 + bob, outline=eye, width=2)
            canvas.create_line(150, 86 + bob, 160, 96 + bob, fill=eye, width=2)
        else:
            canvas.create_arc(98, 143 + bob, 122, 161 + bob, start=200, extent=140,
                              style=tk.ARC, outline=eye, width=2)
        canvas.create_oval(66, 142 + bob, 82, 151 + bob, fill="#ffffff", outline="", stipple="gray25")
        canvas.create_oval(138, 142 + bob, 154, 151 + bob, fill="#ffffff", outline="", stipple="gray25")

        if self.state == "waving":
            canvas.create_line(166, 145 + bob, 194, 118 + bob, fill=dark, width=8,
                               capstyle=tk.ROUND)
            canvas.create_oval(184, 100 + bob, 206, 122 + bob, fill=_shade(color, 0.9), outline=dark)

        canvas.create_oval(60, 180 + bob, 94, 202 + bob, fill=_shade(color, 0.85), outline=dark)
        canvas.create_oval(126, 180 + bob, 160, 202 + bob, fill=_shade(color, 0.85), outline=dark)
        canvas.create_text(110, 232, text=self.state, fill="#2b2d31",
                           font=("Microsoft YaHei UI", 8))

    def _animate(self) -> None:
        if self._closed:
            return
        self.tick += 1
        if self.tick % 22 == 0:
            self.blink = True
            self.win.after(160, self._unblink)
        self._draw()
        self._after = self.win.after(160, self._animate)

    def _unblink(self) -> None:
        self.blink = False
        if not self._closed:
            self._draw()

    def set_state(self, state: str) -> None:
        self.state = state if state in STATE_COLORS else "idle"
        if not self._closed:
            self._draw()

    def bubble(self, text: str, milliseconds: int = 5000, on_click=None) -> None:
        x = self.win.winfo_x() + 10
        y = max(0, self.win.winfo_y() - 58)
        self.bubble_window.show(text, x, y, milliseconds, on_click=on_click)

    def _press(self, event: tk.Event) -> None:
        self._drag = (event.x_root - self.win.winfo_x(), event.y_root - self.win.winfo_y())
        self._press_pos = (event.x_root, event.y_root)

    def _move(self, event: tk.Event) -> None:
        if self._drag is None:
            return
        dx, dy = self._drag
        self.win.geometry(f"+{event.x_root - dx}+{event.y_root - dy}")
        if self.bubble_window.win.winfo_ismapped():
            self.bubble_window.move(event.x_root - dx + 10, max(0, event.y_root - dy - 58))

    def _release(self, event: tk.Event) -> None:
        self._drag = None
        pressed = self._press_pos
        self._press_pos = None
        if (pressed is not None and self.on_click is not None
                and abs(event.x_root - pressed[0]) <= 4
                and abs(event.y_root - pressed[1]) <= 4):
            self.on_click()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._after is not None:
            try:
                self.win.after_cancel(self._after)
            except tk.TclError:
                pass
        self.bubble_window.close()
        self.win.destroy()

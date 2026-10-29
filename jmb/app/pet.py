"""内置桌宠渲染层（D33）：透明置顶 + 薄荷色状态 + 圆角气泡。

素材是 jmb 自有的 8x9 spritesheet（192x208 帧）；没有 Pillow 时退回 Canvas 画。
"""
from __future__ import annotations

import json
import math
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont

from . import theme

STATE_COLORS = {
    "idle": "#5eead4",
    "thinking": "#93c5fd",
    "searching": "#c4b5fd",
    "working": "#fdba74",
    "waiting": "#fde68a",
    "failed": "#fca5a5",
    "waving": "#86efac",
}
STATE_LABELS = {
    "idle": "在线",
    "thinking": "在想",
    "searching": "搜索中",
    "working": "工作中",
    "waiting": "等你",
    "failed": "出错了",
    "waving": "在呢",
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
BUBBLE_BG = "#f7f3e9"
BUBBLE_BORDER = "#e3dccd"
BUBBLE_TEXT = "#20242b"


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
        self.win.configure(bg=TRANSPARENT)
        try:
            self.win.attributes("-transparentcolor", TRANSPARENT)
        except tk.TclError:
            pass
        self.canvas = tk.Canvas(self.win, bg=TRANSPARENT, highlightthickness=0, bd=0)
        self.canvas.pack()
        self._text = ""
        self._font = ("Microsoft YaHei UI", 10)
        self._measure = tkfont.Font(root=self.win, font=self._font)
        self._on_click = None
        self._after: str | None = None
        self._size = (200, 50)
        self.canvas.bind("<Button-1>", self._clicked)
        self.win.withdraw()

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        self._text = value

    def _wrap(self, text: str, width: int) -> list[str]:
        lines: list[str] = []
        for paragraph in (text or "").splitlines() or [""]:
            current = ""
            for char in paragraph:
                if self._measure.measure(current + char) <= width:
                    current += char
                else:
                    lines.append(current)
                    current = char
            lines.append(current)
        return lines or [""]

    def show(self, text: str, anchor_x: int, anchor_y: int,
             milliseconds: int = 5000, on_click=None) -> None:
        self._text = text
        self._on_click = on_click
        lines = self._wrap(text, 280)
        text_w = max((self._measure.measure(line) for line in lines), default=0)
        line_h = self._measure.metrics("linespace") + 3
        pad_x, pad_y = 14, 11
        name_h = 15
        width = max(160, min(320, text_w + pad_x * 2 + 14))
        height = max(52, len(lines) * line_h + pad_y * 2 + name_h)
        total_h = height + 9
        self.canvas.configure(width=width, height=total_h)
        self.canvas.delete("all")
        theme.round_rect(self.canvas, 1, 1, width - 1, height - 1, 15,
                         fill=BUBBLE_BG, outline=BUBBLE_BORDER)
        self.canvas.create_polygon(width // 2 - 7, height - 2,
                                   width // 2 + 7, height - 2,
                                   width // 2, height + 8,
                                   fill=BUBBLE_BG, outline="")
        theme.round_rect(self.canvas, 0, 0, 4, height, 2,
                         fill=theme.MINT, outline="")
        self.canvas.create_text(pad_x + 6, 6, anchor="nw", text="江慕白",
                                fill="#2f7c70", font=theme.FONT_TINY)
        self.canvas.create_text(pad_x + 6, pad_y + name_h, anchor="nw",
                                text=chr(10).join(lines),
                                fill=BUBBLE_TEXT, font=self._font)
        x = max(0, anchor_x - width // 2)
        y = max(0, anchor_y - total_h)
        self.win.geometry(f"{width}x{total_h}+{x}+{y}")
        self._size = (width, total_h)
        self.win.deiconify()
        self.win.lift()
        if self._after is not None:
            self.win.after_cancel(self._after)
        self._after = self.win.after(max(1000, milliseconds), self.win.withdraw)

    def move(self, anchor_x: int, anchor_y: int) -> None:
        width, height = self._size
        x = max(0, anchor_x - width // 2)
        y = max(0, anchor_y - height)
        self.win.geometry(f"+{x}+{y}")

    def _clicked(self, _event=None) -> None:
        if self._on_click is not None:
            callback, self._on_click = self._on_click, None
            self.win.withdraw()
            callback()

    def close(self) -> None:
        if self._after is not None:
            try:
                self.win.after_cancel(self._after)
            except tk.TclError:
                pass
        self.win.destroy()


def _star(canvas: tk.Canvas, cx: int, cy: int, radius: int, fill: str) -> None:
    k = radius * 0.28
    canvas.create_polygon(
        cx, cy - radius, cx + k, cy - k, cx + radius, cy, cx + k, cy + k,
        cx, cy + radius, cx - k, cy + k, cx - radius, cy, cx - k, cy - k,
        fill=fill, outline="")


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
        self.width, self.height = 220, 262
        self.canvas = tk.Canvas(self.win, width=self.width, height=self.height,
                                bg=TRANSPARENT, highlightthickness=0)
        self.canvas.pack()
        self.state = "idle"
        self.tick = 0
        self.blink = False
        self.on_click = None
        self.on_brief = None
        self.on_quit = None
        self._drag: tuple[int, int] | None = None
        self._press_pos: tuple[int, int] | None = None
        self._after: str | None = None
        self._closed = False
        self._hover = False
        self._bounce = 0
        self._sparkle = 0
        self._sprite_frames = self._load_sprites()
        self.bubble_window = BubbleWindow(master)
        self._place()
        self.canvas.configure(cursor="hand2")
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._move)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Button-3>", self._menu)
        self.canvas.bind("<Enter>", self._enter)
        self.canvas.bind("<Leave>", self._leave)
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
                    box = (col * FRAME_W, row * FRAME_H,
                           (col + 1) * FRAME_W, (row + 1) * FRAME_H)
                    frames[state].append(ImageTk.PhotoImage(sheet.crop(box), master=self.win))
            return frames
        except Exception:  # noqa: BLE001 —— 没有 Pillow/素材时回退 Canvas
            return {}

    def _place(self) -> None:
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        self.win.geometry(
            f"{self.width}x{self.height}+{sw - self.width - 48}+{sh - self.height - 90}")

    def move_to(self, x: int, y: int) -> None:
        screen_w = self.win.winfo_screenwidth()
        screen_h = self.win.winfo_screenheight()
        x = max(-self.width + 90, min(int(x), screen_w - 90))
        y = max(0, min(int(y), screen_h - 60))
        self.win.geometry(f"+{x}+{y}")

    def _draw(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        color = STATE_COLORS.get(self.state, STATE_COLORS["idle"])
        bob = int(math.sin(self.tick / 9.0) * 2) + self._bounce
        frames = self._sprite_frames.get(self.state) or self._sprite_frames.get("idle")
        if self._hover:
            canvas.create_oval(11, 1, 209, 217, outline=_shade(color, 0.8), width=1)
        if frames:
            canvas.create_image(self.width // 2, 106 - bob,
                                image=frames[(self.tick // 3) % len(frames)])
        else:
            dark = _shade(color, 0.65)
            canvas.create_oval(44, 46 - bob, 176, 194 - bob, fill=color,
                               outline=dark, width=2)
            canvas.create_oval(58, 32 - bob, 100, 74 - bob, fill=_shade(color, 0.9),
                               outline=dark)
            canvas.create_oval(120, 32 - bob, 162, 74 - bob, fill=_shade(color, 0.9),
                               outline=dark)
            eye = "#1e1f22"
            canvas.create_oval(84, 104 - bob, 102, 128 - bob, fill=eye, outline="")
            canvas.create_oval(120, 104 - bob, 138, 128 - bob, fill=eye, outline="")
            canvas.create_arc(98, 135 - bob, 122, 153 - bob, start=200, extent=140,
                              style=tk.ARC, outline=eye, width=2)
        chip = f"江慕白 · {STATE_LABELS.get(self.state, '在线')}"
        theme.round_rect(canvas, 57, 229, 163, 255, 13, fill=theme.PANEL,
                         outline=theme.BORDER)
        canvas.create_oval(69, 239, 77, 247, fill=color, outline="")
        canvas.create_text(83, 242, anchor="w", text=chip, fill=theme.TEXT,
                           font=theme.FONT_TINY)
        if self._hover or self._sparkle > 0:
            sparkle = _shade(color, 1.12)
            points = [(36, 46, 4), (187, 66, 3), (176, 176, 3)]
            if self._sparkle > 0:
                points += [(50, 90, 3), (168, 126, 4), (148, 38, 2)]
            for index, (sx, sy, size) in enumerate(points):
                if (self.tick // 5 + index) % 2:
                    size = max(2, size - 1)
                _star(canvas, sx, sy, size, sparkle)

    def _animate(self) -> None:
        if self._closed:
            return
        self.tick += 1
        if self._bounce > 0:
            self._bounce = max(0, self._bounce - 1)
        if self._sparkle > 0:
            self._sparkle = max(0, self._sparkle - 1)
        if self.tick % 22 == 0:
            self.blink = True
            self.win.after(160, self._unblink)
        self._draw()
        self._after = self.win.after(120, self._animate)

    def _unblink(self) -> None:
        self.blink = False
        if not self._closed:
            self._draw()

    def set_state(self, state: str) -> None:
        state = state if state in STATE_COLORS else "idle"
        if state != self.state and state in ("thinking", "waving", "failed"):
            self._bounce = 4
        self.state = state
        if not self._closed:
            self._draw()

    def bubble(self, text: str, milliseconds: int = 5000, on_click=None) -> None:
        anchor_x = self.win.winfo_x() + self.width // 2
        anchor_y = self.win.winfo_y() + 6
        self.bubble_window.show(text, anchor_x, anchor_y, milliseconds, on_click=on_click)

    def _enter(self, _event=None) -> None:
        self._hover = True
        self._draw()

    def _leave(self, _event=None) -> None:
        self._hover = False
        self._draw()

    def _menu(self, event) -> None:
        menu = tk.Menu(self.win, tearoff=0, bg=theme.PANEL, fg=theme.TEXT,
                       activebackground=theme.MINT_DIM, activeforeground=theme.TEXT,
                       bd=0, relief="flat")
        menu.add_command(label="打开聊天", command=lambda: self.on_click and self.on_click())
        menu.add_command(label="今日清单", command=lambda: self.on_brief and self.on_brief())
        menu.add_separator()
        menu.add_command(label="切换置顶", command=self.toggle_topmost)
        menu.add_command(label="退出", command=lambda: self.on_quit and self.on_quit())
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def toggle_topmost(self) -> None:
        current = bool(self.win.attributes("-topmost"))
        self.win.attributes("-topmost", not current)

    def _press(self, event: tk.Event) -> None:
        self._drag = (event.x_root - self.win.winfo_x(),
                      event.y_root - self.win.winfo_y())
        self._press_pos = (event.x_root, event.y_root)

    def _move(self, event: tk.Event) -> None:
        if self._drag is None:
            return
        dx, dy = self._drag
        x, y = event.x_root - dx, event.y_root - dy
        self.win.geometry(f"+{x}+{y}")
        if self.bubble_window.win.winfo_ismapped():
            self.bubble_window.move(x + self.width // 2, y + 6)

    def _release(self, event: tk.Event) -> None:
        self._drag = None
        pressed = self._press_pos
        self._press_pos = None
        if (pressed is not None and self.on_click is not None
                and abs(event.x_root - pressed[0]) <= 4
                and abs(event.y_root - pressed[1]) <= 4):
            self._bounce = 6
            self._sparkle = 10
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

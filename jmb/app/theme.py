"""app 壳的视觉主题：颜色、字体、圆角、头像、Windows 深色标题栏。"""
from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from pathlib import Path

BG = "#111318"
PANEL = "#171a20"
PANEL_2 = "#1d2129"
BORDER = "#282e38"
TEXT = "#e9e6e1"
MUTED = "#8d95a4"
MINT = "#6ee7d2"
MINT_DIM = "#2a5c55"
USER_BG = "#1e3538"
USER_FG = "#dcfff8"
ASSIST_BG = "#1b1f27"
ASSIST_FG = "#e9e6e1"
WARN = "#f3c969"
ERROR = "#f28b82"
EDIT = "#c9a7ff"
SHADOW = "#0c0d10"

FONT = ("Microsoft YaHei UI", 10)
FONT_SMALL = ("Microsoft YaHei UI", 9)
FONT_TINY = ("Microsoft YaHei UI", 8)
FONT_TITLE = ("Microsoft YaHei UI", 13, "bold")
FONT_NAME = ("Microsoft YaHei UI", 9, "bold")
FONT_MONO = ("Consolas", 9)

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "pets" / "jmb"


def round_rect(canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float,
               radius: float, **kwargs):
    radius = max(0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    points = [
        x1 + radius, y1, x1 + radius, y1, x2 - radius, y1, x2 - radius, y1,
        x2, y1, x2, y1 + radius, x2, y1 + radius, x2, y2 - radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x2 - radius, y2,
        x1 + radius, y2, x1 + radius, y2, x1, y2, x1, y2 - radius,
        x1, y2 - radius, x1, y1 + radius, x1, y1 + radius, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def load_avatar(size: int, bg: str = BG, ring: str | None = None, master=None):
    """优先用单独的头像图，否则把 spritesheet 第一帧裁成圆形头像。"""
    from PIL import Image, ImageDraw, ImageTk

    try:
        avatar_path = ASSET_DIR / "avatar.png"
        if avatar_path.exists():
            frame = Image.open(avatar_path).convert("RGBA")
        else:
            sheet = Image.open(ASSET_DIR / "spritesheet.png").convert("RGBA")
            frame = sheet.crop((0, 0, 192, 208))
        bbox = frame.getbbox()
        if bbox:
            frame = frame.crop(bbox)
    except Exception:  # noqa: BLE001 —— 没素材时用纯色圆
        frame = None
    canvas = Image.new("RGB", (size, size), bg)
    draw = ImageDraw.Draw(canvas)
    pad = max(1, size // 12)
    draw.ellipse((pad, pad, size - pad, size - pad), fill=PANEL_2,
                 outline=ring or BORDER, width=max(1, size // 18))
    if frame is not None:
        inner = size - pad * 4
        frame.thumbnail((inner, inner), Image.LANCZOS)
        x = (size - frame.width) // 2
        y = (size - frame.height) // 2
        canvas.paste(frame, (x, y), frame)
    return ImageTk.PhotoImage(canvas, master=master)


def enable_dark_titlebar(window: tk.Misc) -> None:
    if sys.platform != "win32":
        return
    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id()) or window.winfo_id()
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        corner = ctypes.c_int(2)  # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 33, ctypes.byref(corner), ctypes.sizeof(corner))
    except Exception:  # noqa: BLE001 —— 旧系统/非 Win11 忽略
        pass

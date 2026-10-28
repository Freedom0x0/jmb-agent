"""Generate jmb's own pet assets: pet.json + 8x9 spritesheet (192x208 frames)."""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

FRAME_W, FRAME_H = 192, 208
COLS, ROWS = 8, 9
SCALE = 2
OUT = Path(__file__).resolve().parents[1] / "jmb" / "assets" / "pets" / "jmb"

STATES = {
    "idle": 0,
    "thinking": 1,
    "searching": 2,
    "working": 3,
    "waving": 4,
    "failed": 5,
}
COLORS = {
    "idle": "#5eead4",
    "thinking": "#93c5fd",
    "searching": "#c4b5fd",
    "working": "#fdba74",
    "waving": "#86efac",
    "failed": "#fca5a5",
}


def _rgb(value: str) -> tuple[int, int, int]:
    raw = value.lstrip("#")
    return tuple(int(raw[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _shade(value: str, factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(part * factor))) for part in _rgb(value))  # type: ignore[return-value]


def _box(values) -> list[int]:
    return [int(value * SCALE) for value in values]


def _width(value: float) -> int:
    return max(1, int(value * SCALE))


def _ellipse(draw, values, **kwargs) -> None:
    draw.ellipse(_box(values), **kwargs)


def _line(draw, points, **kwargs) -> None:
    draw.line([(int(x * SCALE), int(y * SCALE)) for x, y in points], **kwargs)


def _arc(draw, values, **kwargs) -> None:
    draw.arc(_box(values), **kwargs)


def draw_frame(state: str, frame: int) -> Image.Image:
    size = (FRAME_W * SCALE, FRAME_H * SCALE)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    color_hex = COLORS.get(state, COLORS["idle"])
    color = _rgb(color_hex)
    dark = _shade(color_hex, 0.55)
    light = _shade(color_hex, 1.18)
    ink = (30, 31, 34, 255)

    phase = frame / COLS * math.tau
    bob = math.sin(phase) * 4
    if state == "failed":
        bob = 0
    sway = math.sin(phase) * 3

    # shadow
    _ellipse(draw, (62, 198, 158, 214), fill=(0, 0, 0, 55))

    # feet behind body
    _ellipse(draw, (58, 178 + bob, 94, 202 + bob), fill=_shade(color_hex, 0.82), outline=dark,
             width=2 * SCALE)
    _ellipse(draw, (126, 178 + bob, 162, 202 + bob), fill=_shade(color_hex, 0.82), outline=dark,
             width=2 * SCALE)

    # ears behind body
    _ellipse(draw, (56, 36 + bob, 102, 84 + bob), fill=_shade(color_hex, 0.92), outline=dark,
             width=2 * SCALE)
    _ellipse(draw, (118, 36 + bob, 164, 84 + bob), fill=_shade(color_hex, 0.92), outline=dark,
             width=2 * SCALE)

    # body
    _ellipse(draw, (44, 52 + bob, 176, 200 + bob), fill=color, outline=dark, width=2 * SCALE)

    # inner ears
    _ellipse(draw, (69, 49 + bob, 91, 71 + bob), fill=light)
    _ellipse(draw, (129, 49 + bob, 151, 71 + bob), fill=light)

    blink = state in {"idle", "working", "waving"} and frame == 6
    eye_y = 110 + bob
    if state == "failed":
        for x1, x2 in ((83, 101), (119, 137)):
            _line(draw, [(x1, eye_y + 2), (x2, eye_y + 20)], fill=ink, width=3 * SCALE)
            _line(draw, [(x2, eye_y + 2), (x1, eye_y + 20)], fill=ink, width=3 * SCALE)
    elif blink:
        _line(draw, [(84, eye_y + 12), (100, eye_y + 12)], fill=ink, width=3 * SCALE)
        _line(draw, [(120, eye_y + 12), (136, eye_y + 12)], fill=ink, width=3 * SCALE)
    else:
        _ellipse(draw, (84, eye_y, 102, eye_y + 26), fill=ink)
        _ellipse(draw, (120, eye_y, 138, eye_y + 26), fill=ink)
        _ellipse(draw, (90, eye_y + 5, 96, eye_y + 13), fill=(255, 255, 255, 255))
        _ellipse(draw, (126, eye_y + 5, 132, eye_y + 13), fill=(255, 255, 255, 255))

    # cheeks
    _ellipse(draw, (64, 140 + bob, 82, 150 + bob), fill=(255, 255, 255, 65))
    _ellipse(draw, (138, 140 + bob, 156, 150 + bob), fill=(255, 255, 255, 65))

    if state == "thinking":
        _line(draw, [(100, 154 + bob), (118, 154 + bob)], fill=ink, width=2 * SCALE)
        for dot_x in (84, 98, 112):
            _ellipse(draw, (dot_x, 78 + bob, dot_x + 7, 85 + bob), fill=(255, 255, 255, 185))
    elif state == "searching":
        _arc(draw, (99, 144 + bob, 121, 162 + bob), start=0, end=180, fill=ink, width=2 * SCALE)
        _ellipse(draw, (142, 72 + bob, 164, 94 + bob), outline=ink, width=2 * SCALE)
        _line(draw, [(158, 88 + bob), (170, 100 + bob)], fill=ink, width=2 * SCALE)
    elif state == "failed":
        _line(draw, [(101, 154 + bob), (119, 154 + bob)], fill=ink, width=2 * SCALE)
    else:
        _arc(draw, (98, 142 + bob, 122, 160 + bob), start=20, end=160, fill=ink, width=2 * SCALE)

    if state == "working":
        for dx in (-4, 0, 4):
            _line(draw, [(160 + dx, 118 + bob), (166 + dx, 108 + bob)], fill=(255, 255, 255, 185),
                  width=2 * SCALE)

    if state == "waving":
        hand_x = 188 + sway
        hand_y = 110 - abs(sway) * 2
        _line(draw, [(166, 146 + bob), (hand_x, hand_y)], fill=dark, width=8 * SCALE)
        _ellipse(draw, (hand_x - 10, hand_y - 10, hand_x + 12, hand_y + 12),
                 fill=_shade(color_hex, 0.9), outline=dark, width=2 * SCALE)

    return image.resize((FRAME_W, FRAME_H), Image.Resampling.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGBA", (FRAME_W * COLS, FRAME_H * ROWS), (0, 0, 0, 0))
    rows = {state: row for state, row in STATES.items()}
    for row in range(ROWS):
        state = next((name for name, value in rows.items() if value == row), "idle")
        for col in range(COLS):
            frame = draw_frame(state, col)
            sheet.alpha_composite(frame, (col * FRAME_W, row * FRAME_H))
    sheet.save(OUT / "spritesheet.png", optimize=True)
    (OUT / "pet.json").write_text(json.dumps({
        "id": "jmb",
        "displayName": "jmb",
        "description": "jmb's own tiny blob companion.",
        "spriteVersionNumber": 2,
        "spritesheetPath": "spritesheet.png",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT / 'spritesheet.png'} ({sheet.width}x{sheet.height})")
    print(f"wrote {OUT / 'pet.json'}")


if __name__ == "__main__":
    main()

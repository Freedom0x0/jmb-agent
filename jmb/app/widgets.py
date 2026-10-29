"""自绘圆角控件 + 气泡聊天视图（Tkinter 原生控件没有圆角）。"""
from __future__ import annotations

import re
import tkinter as tk
from tkinter import font as tkfont

from . import theme

COLORS = {
    "user": (theme.USER_BG, theme.USER_FG, theme.MINT_DIM),
    "assistant": (theme.ASSIST_BG, theme.ASSIST_FG, theme.BORDER),
    "meta": (theme.BG, theme.MUTED, theme.BG),
    "warn": (theme.BG, theme.WARN, theme.BG),
    "edit": (theme.BG, theme.EDIT, theme.BG),
    "error": (theme.BG, theme.ERROR, theme.BG),
    "notice": (theme.BG, theme.MINT, theme.BG),
}


class RoundedButton(tk.Canvas):
    def __init__(self, master, text: str, command=None, width: int = 88, height: int = 38,
                 fill: str = theme.MINT, fg: str = theme.BG, hover: str | None = None,
                 disabled_fill: str = theme.PANEL_2, disabled_fg: str = theme.MUTED,
                 radius: int = 14, font=theme.FONT):
        super().__init__(master, width=width, height=height, bg=theme.BG,
                         highlightthickness=0, bd=0)
        self._bw, self._bh, self._radius = width, height, radius
        self._text, self._command = text, command
        self._fill, self._fg = fill, fg
        self._hover_fill = hover or fill
        self._disabled_fill, self._disabled_fg = disabled_fill, disabled_fg
        self._font = font
        self._state = "normal"
        self._hover = self._pressed = False
        self.configure(cursor="hand2")
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        enabled = self._state != "disabled"
        fill = (self._hover_fill if self._hover and enabled else self._fill) if enabled else self._disabled_fill
        fg = self._fg if enabled else self._disabled_fg
        theme.round_rect(self, 1, 1, self._bw - 1, self._bh - 1, self._radius,
                         fill=fill, outline="")
        self.create_text(self._bw / 2, self._bh / 2, text=self._text, fill=fg,
                         font=self._font)

    def set_state(self, state: str) -> None:
        self._state = state
        self._draw()

    def set_text(self, text: str) -> None:
        self._text = text
        self._draw()

    def _on_press(self, _event=None) -> None:
        if self._state == "disabled":
            return
        self._pressed = True

    def _on_release(self, event=None) -> None:
        if self._state == "disabled" or not self._pressed:
            return
        self._pressed = False
        x, y = (event.x, event.y) if event is not None else (0, 0)
        if 0 <= x <= self._bw and 0 <= y <= self._bh and self._command:
            self._command()

    def _on_enter(self, _event=None) -> None:
        self._hover = True
        self._draw()

    def _on_leave(self, _event=None) -> None:
        self._hover = False
        self._draw()


_NON_TEXT_KEYS = {"Return", "KP_Enter", "Tab", "Escape", "Shift_L", "Shift_R",
                  "Control_L", "Control_R", "Alt_L", "Alt_R", "Left", "Right",
                  "Home", "End", "Up", "Down"}


class InputBar(tk.Frame):
    """圆角输入槽：Canvas 画底，Entry 嵌在里面；placeholder 直接放 Entry 里。"""

    def __init__(self, master, placeholder: str = "和江慕白说点什么…",
                 on_return=None):
        super().__init__(master, bg=theme.BG)
        self._placeholder = placeholder
        self._on_return = on_return
        self._showing_placeholder = False
        self._focused = False
        self.canvas = tk.Canvas(self, height=54, bg=theme.BG, highlightthickness=0, bd=0)
        self.canvas.pack(fill="x", expand=True)
        self.entry = tk.Entry(self.canvas, bg=theme.PANEL, fg=theme.TEXT,
                              insertbackground=theme.MINT, relief="flat", bd=0,
                              font=theme.FONT, disabledbackground=theme.PANEL_2,
                              disabledforeground=theme.MUTED)
        self._window = self.canvas.create_window(18, 27, anchor="w", window=self.entry)
        self.canvas.bind("<Configure>", self._layout)
        self.canvas.bind("<Button-1>", lambda _e: self.entry.focus_set())
        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self.entry.bind("<KeyPress>", self._on_key)
        if on_return is not None:
            self.entry.bind("<Return>", lambda _e: on_return())
        self._show_placeholder()

    def _show_placeholder(self, text: str | None = None) -> None:
        if str(self.entry.cget("state")) == "disabled":
            self.entry.config(state="normal")
            self.entry.delete(0, "end")
            self.entry.insert(0, text or self._placeholder)
            self.entry.config(fg=theme.MUTED, state="disabled")
        else:
            self.entry.delete(0, "end")
            self.entry.insert(0, text or self._placeholder)
            self.entry.config(fg=theme.MUTED)
        self._showing_placeholder = True

    def _focus_in(self, _event=None) -> None:
        self._focused = True
        self._layout()
        if not self.entry.get():
            self._show_placeholder()

    def _on_key(self, event) -> None:
        if not self._showing_placeholder:
            return
        if event.keysym in _NON_TEXT_KEYS:
            return
        self.entry.delete(0, "end")
        self.entry.config(fg=theme.TEXT)
        self._showing_placeholder = False

    def _focus_out(self, _event=None) -> None:
        self._focused = False
        self._layout()
        if not self.entry.get():
            self._show_placeholder()

    def _layout(self, event=None) -> None:
        width = event.width if event is not None else self.canvas.winfo_width()
        if width < 40:
            return
        self.canvas.delete("bg")
        theme.round_rect(self.canvas, 1, 1, width - 1, 52, 16,
                         fill=theme.PANEL if str(self.entry.cget("state")) != "disabled"
                         else theme.PANEL_2,
                         outline=(theme.MINT_DIM if self._focused
                                  and str(self.entry.cget("state")) != "disabled"
                                  else theme.BORDER), tags="bg")
        self.canvas.tag_lower("bg")
        self.canvas.itemconfigure(self._window, width=max(40, width - 36))
        self.canvas.coords(self._window, 18, 27)

    def get(self) -> str:
        return "" if self._showing_placeholder else self.entry.get()

    def clear(self) -> None:
        self.entry.delete(0, "end")
        self._showing_placeholder = False
        self.entry.config(fg=theme.TEXT)
        if self.entry.focus_get() is not self.entry:
            self._show_placeholder()

    def set_state(self, state: str, placeholder: str | None = None) -> None:
        if placeholder:
            self._placeholder = placeholder
        if state == "disabled":
            if not self.entry.get() or self._showing_placeholder:
                self._show_placeholder("江慕白正在回复…")
            self.entry.config(state="disabled")
        else:
            self.entry.config(state="normal")
            if self._showing_placeholder:
                self.entry.delete(0, "end")
                self._showing_placeholder = False
            if not self.entry.get():
                self._show_placeholder()
            self.entry.config(fg=theme.TEXT if not self._showing_placeholder else theme.MUTED)
        self._layout()

    def focus_set(self) -> None:
        self.entry.focus_set()
        if not self.entry.get():
            self._show_placeholder()


_FENCE_RE = re.compile(r"```([^\n]*)\n(.*?)(?:```|$)", re.S)


def split_segments(text: str) -> list[tuple[str, str, str]]:
    """把消息拆成 (kind, content, lang) 段；支持未闭合的代码围栏。"""
    text = text or ""
    parts: list[tuple[str, str, str]] = []
    position = 0
    for match in _FENCE_RE.finditer(text):
        before = text[position:match.start()].strip("\n")
        if before.strip():
            parts.append(("text", before, ""))
        code_text = match.group(2).rstrip("\n")
        if code_text.strip():
            parts.append(("code", code_text, match.group(1).strip()))
        position = match.end()
    tail = text[position:].strip("\n")
    if tail.strip():
        parts.append(("text", tail, ""))
    return parts or [("text", text, "")]


class CodeBubble(tk.Canvas):
    MAX_LINES = 22

    def __init__(self, master, code: str, lang: str = "", max_width: int = 600):
        super().__init__(master, bg=theme.BG, highlightthickness=0, bd=0)
        self._font = tkfont.Font(root=self, font=("Consolas", 9))
        self._pad = 12
        self._code = code
        lines = code.splitlines() or [""]
        total = len(lines)
        shown = lines[:self.MAX_LINES]
        wrapped: list[str] = []
        for line in shown:
            wrapped.extend(self._wrap(line, max_width - self._pad * 2 - 6) or [""])
        truncated = total > len(shown)
        line_h = self._font.metrics("linespace") + 2
        header = 14 if lang else 0
        text_width = max((self._font.measure(line) for line in wrapped), default=0)
        width = max(160, min(max_width, text_width + self._pad * 2 + 8))
        height = (len(wrapped) * line_h + self._pad * 2 + header
                  + (line_h if truncated else 0))
        self.configure(width=width, height=height)
        theme.round_rect(self, 1, 1, width - 1, height - 1, 10,
                         fill="#0f1217", outline="#26313a")
        theme.round_rect(self, 0, 0, 3, height, 1, fill=theme.MINT, outline="")
        y = self._pad
        if lang:
            self.create_text(width - self._pad, 6, anchor="ne", text=lang,
                             fill=theme.MUTED, font=theme.FONT_TINY)
            y += header
        self.create_text(self._pad + 4, y, anchor="nw", text=chr(10).join(wrapped),
                         fill="#d6e2ea", font=self._font)
        if truncated:
            self.create_text(self._pad + 4, y + len(wrapped) * line_h, anchor="nw",
                             text=f"…（共 {total} 行，已折叠）", fill=theme.MUTED,
                             font=theme.FONT_TINY)
        self.bind("<Button-3>", self._copy_menu)

    def _wrap(self, line: str, max_px: int) -> list[str]:
        if not line:
            return [""]
        out: list[str] = []
        current = ""
        for char in line:
            if self._font.measure(current + char) <= max_px:
                current += char
            else:
                out.append(current)
                current = char
        out.append(current)
        return out

    def _copy_menu(self, event) -> None:
        menu = tk.Menu(self, tearoff=0, bg=theme.PANEL, fg=theme.TEXT,
                       activebackground=theme.MINT_DIM, activeforeground=theme.TEXT)
        menu.add_command(label="复制代码",
                         command=lambda: (self.clipboard_clear(),
                                          self.clipboard_append(self._code)))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()


class ChatBubble(tk.Canvas):
    def __init__(self, master, text: str, role: str, max_width: int = 540):
        super().__init__(master, bg=theme.BG, highlightthickness=0, bd=0)
        self._role = role
        self._text = ""
        self._max_width = max_width
        self._font = tkfont.Font(root=self, font=theme.FONT)
        self._pad_x, self._pad_y = 15, 11
        self.bind("<Button-3>", self._copy_menu)
        self.set_text(text)

    def set_text(self, text: str) -> None:
        self._text = text
        fill, fg, outline = COLORS.get(self._role, COLORS["assistant"])
        line_height = self._font.metrics("linespace") + 3
        lines = self._wrap(text)
        text_width = max((self._font.measure(line) for line in lines), default=0)
        width = min(self._max_width, max(72, text_width + self._pad_x * 2))
        height = max(38, len(lines) * line_height + self._pad_y * 2)
        self.configure(width=width, height=height)
        self.delete("all")
        theme.round_rect(self, 1, 1, width - 1, height - 1, 16,
                         fill=fill, outline=outline)
        self.create_text(self._pad_x, self._pad_y, anchor="nw", text="\n".join(lines),
                         fill=fg, font=theme.FONT)

    def _copy_menu(self, event) -> None:
        menu = tk.Menu(self, tearoff=0, bg=theme.PANEL, fg=theme.TEXT,
                       activebackground=theme.MINT_DIM, activeforeground=theme.TEXT)
        menu.add_command(label="复制这条", command=lambda: self._copy())
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self._text)

    def _wrap(self, text: str) -> list[str]:
        lines: list[str] = []
        for paragraph in (text or "").splitlines() or [""]:
            current = ""
            for char in paragraph:
                if self._font.measure(current + char) <= self._max_width - self._pad_x * 2:
                    current += char
                else:
                    lines.append(current)
                    current = char
            lines.append(current)
        return lines or [""]


class ScrollThumb(tk.Canvas):
    """自绘细滚动条，避免 Windows 默认白色滚动条。"""

    def __init__(self, master, command):
        super().__init__(master, width=8, bg=theme.BG, highlightthickness=0, bd=0)
        self._command = command
        self._first, self._last = 0.0, 1.0
        self._dragging = False
        self._hover = False
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Button-1>", self._jump)
        self.bind("<B1-Motion>", self._drag_move)
        self.bind("<ButtonRelease-1>", lambda _e: setattr(self, "_dragging", False))
        self.bind("<Enter>", lambda _e: self._draw(hover=True))
        self.bind("<Leave>", lambda _e: self._draw(hover=False))

    def set_view(self, first, last) -> None:
        self._first, self._last = float(first), float(last)
        self._draw()

    def _draw(self, hover: bool | None = None) -> None:
        if hover is not None:
            self._hover = hover
        self.delete("all")
        width = self.winfo_width() or 8
        height = self.winfo_height()
        if height < 2 or self._last - self._first >= 0.999:
            return
        y1 = self._first * height
        y2 = self._last * height
        thumb_h = max(24, y2 - y1)
        y1 = min(y1, height - thumb_h)
        theme.round_rect(self, 2, y1, width - 2, y1 + thumb_h,
                         (width - 4) / 2,
                         fill=theme.MUTED if self._hover else theme.BORDER, outline="")

    def _fraction(self, y: int) -> float:
        return max(0.0, min(1.0, y / max(1, self.winfo_height())))

    def _jump(self, event) -> None:
        self._dragging = True
        self._command("moveto", self._fraction(event.y))

    def _drag_move(self, event) -> None:
        if self._dragging:
            self._command("moveto", self._fraction(event.y))


class ChatView(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=theme.BG)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, bg=theme.BG, highlightthickness=0, bd=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar = ScrollThumb(self, self.canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self.scrollbar.set_view)
        self.inner = tk.Frame(self.canvas, bg=theme.BG)
        self._window = self.canvas.create_window(0, 0, anchor="nw", window=self.inner)
        self.inner.bind("<Configure>", lambda _e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self._messages: list[dict] = []
        self._stream_text = ""
        self._stream_row = None
        self._stream_bubble = None
        self._stream_after = None
        self._stream_active = False
        self._stream_stick = True
        self._typing_row = None
        self._avatar = theme.load_avatar(30, bg=theme.BG, master=self)
        self._empty = self._build_empty()

    def _on_resize(self, event) -> None:
        if event.width > 20:
            self.canvas.itemconfigure(self._window, width=event.width)

    def _on_wheel(self, event) -> None:
        self.canvas.yview_scroll(-int(event.delta / 120), "units")
        self._stream_stick = self._at_bottom()

    def _at_bottom(self) -> bool:
        try:
            return self.canvas.yview()[1] >= 0.97
        except tk.TclError:
            return True

    def _bubble_width(self) -> int:
        width = self.canvas.winfo_width()
        return max(300, min(600, width - 120 if width > 200 else 520))

    def _wrap_width(self) -> int:
        width = self.canvas.winfo_width()
        return max(320, (width - 80) if width > 200 else 600)

    def _build_empty(self) -> tk.Canvas:
        card = tk.Canvas(self.inner, width=380, height=250, bg=theme.BG,
                         highlightthickness=0)
        card.pack(pady=(70, 30))
        theme.round_rect(card, 1, 1, 379, 249, 22, fill=theme.PANEL,
                         outline=theme.BORDER)
        body = tk.Frame(card, bg=theme.PANEL)
        card.create_window(190, 125, window=body)
        avatar = theme.load_avatar(76, bg=theme.PANEL, ring=theme.MINT_DIM, master=card)
        image = tk.Label(body, image=avatar, bg=theme.PANEL, bd=0)
        image.image = avatar
        image.pack()
        tk.Label(body, text="江慕白", bg=theme.PANEL, fg=theme.TEXT,
                 font=("Microsoft YaHei UI", 15, "bold")).pack(pady=(12, 2))
        tk.Label(body, text="在。想写点什么？", bg=theme.PANEL, fg=theme.MUTED,
                 font=theme.FONT).pack()
        tk.Label(body, text="直接说话，或者问「今天有什么」", bg=theme.PANEL,
                 fg=theme.MUTED, font=theme.FONT_TINY).pack(pady=(6, 0))
        return card

    def _hide_empty(self) -> None:
        if self._empty is not None:
            self._empty.destroy()
            self._empty = None

    def _bind_wheel(self, widget) -> None:
        widget.bind("<MouseWheel>", self._on_wheel)
        for child in widget.winfo_children():
            self._bind_wheel(child)

    def _segments(self, parent: tk.Frame, text: str, role: str,
                  max_width: int, anchor: str) -> None:
        for kind, value, lang in split_segments(text):
            if kind == "code":
                widget = CodeBubble(parent, value, lang, max_width)
            else:
                widget = ChatBubble(parent, value, role, max_width)
            widget.pack(anchor=anchor, pady=(0, 6))
            self._bind_wheel(widget)

    def _row(self, text: str, role: str, stream: bool = False) -> tk.Frame:
        self._hide_empty()
        row = tk.Frame(self.inner, bg=theme.BG)
        row.pack(fill="x")
        self._bind_wheel(row)
        if role == "assistant":
            avatar = tk.Label(row, image=self._avatar, bg=theme.BG, bd=0)
            avatar.image = self._avatar
            avatar.pack(side="left", anchor="n", padx=(18, 10), pady=(4, 10))
            column = tk.Frame(row, bg=theme.BG)
            column.pack(side="left", anchor="n", fill="x", expand=True,
                        padx=(0, 80), pady=(2, 10))
            tk.Label(column, text="江慕白", bg=theme.BG, fg=theme.MINT,
                     font=theme.FONT_NAME).pack(anchor="w", pady=(0, 4))
            if stream:
                bubble = ChatBubble(column, text, role, self._bubble_width())
                bubble.pack(anchor="w")
            else:
                content = tk.Frame(column, bg=theme.BG)
                content.pack(anchor="w")
                self._segments(content, text, role, self._bubble_width(), "w")
            self._bind_wheel(row)
        elif role == "user":
            content = tk.Frame(row, bg=theme.BG)
            content.pack(side="right", anchor="e", padx=(90, 18), pady=(4, 10))
            self._segments(content, text, role, self._bubble_width(), "e")
            self._bind_wheel(content)
        else:
            row.destroy()
            return self._meta_row(text, role)
        return row

    def _meta_row(self, text: str, role: str) -> tk.Frame:
        self._hide_empty()
        color = COLORS.get(role, COLORS["meta"])[1]
        row = tk.Frame(self.inner, bg=theme.BG)
        row.pack(fill="x", pady=2)
        tk.Frame(row, bg=color, width=2, height=12).pack(
            side="left", padx=(48, 8), pady=(5, 0))
        label = tk.Label(row, text=text, bg=theme.BG, fg=color, font=theme.FONT_SMALL,
                         justify="left", anchor="w", wraplength=self._wrap_width())
        label.pack(side="left", fill="x", expand=True, padx=(0, 18), pady=2)
        label.bind("<Button-3>", lambda _e: self._copy_text(text))
        self._bind_wheel(row)
        return row

    def append(self, text: str, role: str = "assistant") -> None:
        text = (text or "").rstrip()
        if not text:
            return
        stick = role == "user" or self._at_bottom()
        row = self._row(text, role)
        self._messages.append({"role": role, "text": text, "row": row})
        if stick:
            self._scroll_to_end()

    def begin_stream(self) -> None:
        self.show_typing(False)
        self._stream_stick = self._at_bottom()
        self._stream_active = True
        self._stream_text = ""
        self._stream_row = None
        self._stream_bubble = None

    def stream(self, delta: str) -> None:
        if not self._stream_active:
            self.begin_stream()
        self._stream_text += delta or ""
        if self._stream_bubble is None and self._stream_text.strip():
            self._stream_row = self._row(self._stream_text, "assistant", stream=True)
            self._messages.append({"role": "assistant", "text": self._stream_text,
                                   "row": self._stream_row, "stream": True})
            for child in self._stream_row.winfo_children():
                if isinstance(child, tk.Frame):
                    for sub in child.winfo_children():
                        if isinstance(sub, ChatBubble):
                            self._stream_bubble = sub
        if self._stream_bubble is not None:
            if self._stream_after is None:
                self._stream_after = self.after(30, self._flush_stream)

    def _flush_stream(self) -> None:
        self._stream_after = None
        if self._stream_bubble is not None:
            self._stream_bubble.set_text(self._stream_text)
            if self._messages and self._messages[-1].get("stream"):
                self._messages[-1]["text"] = self._stream_text
            if self._stream_stick:
                self._scroll_to_end()

    def end_stream(self) -> None:
        if self._stream_after is not None:
            self.after_cancel(self._stream_after)
            self._stream_after = None
        if self._stream_bubble is not None:
            self._flush_stream()
        if self._messages and self._messages[-1].get("stream"):
            message = self._messages[-1]
            message.pop("stream", None)
            if not self._stream_text.strip():
                row = self._messages.pop()["row"]
                row.destroy()
            elif "```" in message["text"]:
                old_row = message["row"]
                old_row.destroy()
                message["row"] = self._row(message["text"], "assistant")
                if self._stream_stick:
                    self._scroll_to_end()
        self._stream_active = False
        self._stream_text = ""
        self._stream_row = None
        self._stream_bubble = None

    def show_typing(self, show: bool) -> None:
        if not show:
            if self._typing_row is not None:
                self._typing_row.destroy()
                self._typing_row = None
            return
        if self._typing_row is not None:
            return
        stick = self._at_bottom()
        self._hide_empty()
        row = tk.Frame(self.inner, bg=theme.BG)
        row.pack(fill="x", pady=(2, 8))
        tk.Label(row, text="● 江慕白正在输入…", bg=theme.BG, fg=theme.MINT_DIM,
                 font=theme.FONT_TINY).pack(anchor="w", padx=(60, 18))
        self._typing_row = row
        if stick:
            self._scroll_to_end()

    def _copy_text(self, text: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)

    def last_text(self) -> str:
        for message in reversed(self._messages):
            if message["role"] in ("user", "assistant"):
                return message["text"]
        return ""

    def plain_text(self) -> str:
        return "\n".join(message["text"] for message in self._messages)

    def get(self, *_args) -> str:
        return self.plain_text()

    def clear(self) -> None:
        if self._typing_row is not None:
            self._typing_row.destroy()
            self._typing_row = None
        for message in self._messages:
            message["row"].destroy()
        self._messages.clear()
        self._stream_active = False
        self._stream_stick = True
        self._stream_text = ""
        self._stream_row = self._stream_bubble = None
        if self._empty is None:
            self._empty = self._build_empty()

    def _scroll_to_end(self) -> None:
        try:
            self.canvas.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            self.canvas.yview_moveto(1.0)
        except tk.TclError:
            pass


def _center(win: tk.Toplevel, parent: tk.Misc, width: int, height: int) -> None:
    try:
        parent.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - width) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - height) // 2)
    except tk.TclError:
        x = (win.winfo_screenwidth() - width) // 2
        y = (win.winfo_screenheight() - height) // 2
    win.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")


def ask_yes_no(parent: tk.Misc, title: str, message: str,
               yes: str = "允许", no: str | None = "取消") -> bool:
    """深色模态确认窗；no=None 时只有一个确认按钮。"""
    win = tk.Toplevel(parent)
    win.title(title)
    win.configure(bg=theme.BG)
    win.transient(parent)
    win.resizable(False, False)
    result = {"ok": False}
    body = tk.Frame(win, bg=theme.BG)
    body.pack(fill="both", expand=True, padx=22, pady=18)
    tk.Label(body, text=title, bg=theme.BG, fg=theme.TEXT, anchor="w",
             font=("Microsoft YaHei UI", 12, "bold")).pack(fill="x")
    tk.Label(body, text=message, bg=theme.BG, fg=theme.MUTED, anchor="w",
             justify="left", wraplength=430, font=theme.FONT).pack(
        fill="x", pady=(10, 18))
    row = tk.Frame(body, bg=theme.BG)
    row.pack(fill="x", anchor="e")
    row.grid_columnconfigure(0, weight=1)
    if no is not None:
        RoundedButton(row, no, command=lambda: close(False), width=80, height=36,
                      fill=theme.PANEL_2, fg=theme.TEXT, hover=theme.BORDER,
                      font=theme.FONT, radius=12).grid(row=0, column=1, padx=(8, 0))
    RoundedButton(row, yes, command=lambda: close(True), width=96, height=36,
                  fill=theme.MINT, fg=theme.BG, hover="#8af0de",
                  font=theme.FONT, radius=12).grid(row=0, column=2, padx=(8, 0))

    def close(ok: bool) -> None:
        result["ok"] = ok
        try:
            win.grab_release()
        except tk.TclError:
            pass
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", lambda: close(False))
    win.bind("<Escape>", lambda _e: close(False))
    win.update_idletasks()
    width = max(460, body.winfo_reqwidth() + 44)
    height = body.winfo_reqheight() + 36
    _center(win, parent, width, height)
    theme.enable_dark_titlebar(win)
    win.grab_set()
    win.focus_force()
    parent.wait_window(win)
    return bool(result["ok"])


def show_message(parent: tk.Misc, title: str, message: str) -> None:
    ask_yes_no(parent, title, message, yes="好", no=None)

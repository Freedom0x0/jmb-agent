"""jmb 桌面 app 壳（Tkinter）：聊天窗口 + 内置桌宠事件流。"""
from __future__ import annotations

import json
import os
import queue
import re
import sys
import threading
import tkinter as tk
import uuid
from datetime import date

from .. import config
from . import theme
from .pet import PetWindow
from .widgets import ChatView, InputBar, RoundedButton, ask_text, ask_yes_no, show_message

BG = theme.BG
PANEL = theme.PANEL
TEXT = theme.TEXT
MUTED = theme.MUTED


class ChatWorker(threading.Thread):
    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.inbox: queue.Queue[object] = queue.Queue()
        self.pending_permissions: dict[str, dict] = {}
        self.confirm_event = threading.Event()
        self.confirm_answer = "no"
        self.session = None

    def run(self) -> None:
        from .. import grants

        grants.set_prompt_handler(self._ask_permission)
        try:
            try:
                from ..chat import ChatSession
                self.session = ChatSession(self._emit)
            except Exception as exc:  # noqa: BLE001
                self.events.put(("fatal", f"{type(exc).__name__}: {exc}"))
                return
            self.events.put(("ready", {
                "tid": self.session.tid,
                "profile": self.session.profile.name,
                "transcript": str(self.session.transcript_path),
            }))
            try:
                threading.Thread(target=self.session.warmup, daemon=True).start()
            except Exception:  # noqa: BLE001
                pass
            while True:
                item = self.inbox.get()
                if item is None:
                    break
                if isinstance(item, tuple) and item and item[0] == "__stop__":
                    try:
                        self.session.confirm_pending(interactive=True,
                                                     ask=self._ask_confirmation)
                    except Exception:  # noqa: BLE001
                        pass
                    self.session.close()
                    self.events.put(("closed", None))
                    return
                if isinstance(item, tuple) and item and item[0] == "__undo__":
                    self.events.put(("undo", self.session.undo()))
                    continue
                if isinstance(item, tuple) and item and item[0] == "__edit__":
                    ordinal, text = int(item[1]), str(item[2])
                    expected = str(item[3]) if len(item) > 3 else ""
                    if self.session.rewind_user(ordinal, expected=expected):
                        self.events.put(("rewound", {"ordinal": ordinal, "text": text}))
                        self.session.send(text)
                    else:
                        self.events.put(("error", "编辑失败：这条消息已不在当前上下文"
                                                  "（可能被压缩），请重新发送。"))
                        self.events.put(("turn_end", {
                            "transcript": str(self.session.transcript_path)}))
                    continue
                self.session.send(str(item))
            try:
                pending = self.session.confirm_pending(interactive=False)
                if pending:
                    self.events.put(("warning", pending))
            except Exception:  # noqa: BLE001
                pass
            self.session.close()
            self.events.put(("closed", None))
        finally:
            grants.set_prompt_handler(None)

    def _emit(self, kind: str, data) -> None:
        self.events.put((kind, data))

    def _ask_permission(self, prompt: str) -> str:
        key = uuid.uuid4().hex
        event = threading.Event()
        self.pending_permissions[key] = {"event": event, "answer": False}
        self.events.put(("permission", {"id": key, "text": prompt}))
        event.wait(timeout=300)
        item = self.pending_permissions.pop(key, None)
        return "y" if item and item["answer"] else "n"

    def answer_permission(self, key: str, ok: bool) -> None:
        item = self.pending_permissions.get(key)
        if item is not None:
            item["answer"] = bool(ok)
            item["event"].set()

    def _ask_confirmation(self, items, more: int) -> str:
        self.confirm_event = threading.Event()
        self.confirm_answer = "no"
        self.events.put(("confirm", {"items": items, "more": more}))
        self.confirm_event.wait(timeout=300)
        return self.confirm_answer

    def answer_confirmation(self, answer: str) -> None:
        self.confirm_answer = str(answer)
        self.confirm_event.set()

    def send(self, text: str) -> None:
        self.inbox.put(text)

    def edit_resend(self, ordinal: int, text: str, expected: str = "") -> None:
        self.inbox.put(("__edit__", int(ordinal), str(text), str(expected)))

    def cancel_generation(self) -> None:
        session = self.session
        if session is not None:
            session.cancel_generation()

    def clear_cancel(self) -> None:
        session = self.session
        if session is not None:
            session.clear_cancel()

    def undo(self) -> None:
        self.inbox.put(("__undo__", None))

    def request_stop(self) -> None:
        if self.session is not None:
            self.session.cancel_generation()
        for item in list(self.pending_permissions.values()):
            item["answer"] = False
            item["event"].set()
        self.confirm_answer = "no"
        self.confirm_event.set()
        self.inbox.put(("__stop__", None))

    def stop(self) -> None:
        self.request_stop()
        self.join(timeout=5)


class MainWindow(tk.Tk):
    def __init__(self, start_worker: bool = True) -> None:
        super().__init__()
        self._persist = bool(start_worker)
        if self._persist:
            try:
                self.attributes("-alpha", 0.0)
            except tk.TclError:
                pass
        self.title("江慕白 · jmb")
        self.geometry("900x680+140+80")
        self.minsize(720, 560)
        self.configure(bg=BG)
        self.busy = False
        self._closing = False
        self._destroyed = False
        self._poll_id: str | None = None
        self._titlebar_id: str | None = None
        self.worker: ChatWorker | None = None
        self.pet = PetWindow(self)
        self.pet.on_click = self._show_chat
        self.pet.on_brief = self.show_brief
        self.pet.on_quit = self.close
        self._build_ui()
        self._icon = theme.load_avatar(64, bg=BG, ring=theme.MINT_DIM, master=self)
        try:
            self.iconphoto(True, self._icon)
        except tk.TclError:
            pass
        self.update_idletasks()
        theme.enable_dark_titlebar(self)
        self._titlebar_id = self.after(120, self._apply_dark_titlebar)
        if self._persist:
            self._restore_ui_state()
            self.after(30, self._fade_in)
        if start_worker:
            self._start_worker()
        else:
            self.subtitle.config(text="jmb · UI 预览")
            self.status.config(text="未启动 worker")
            self.input.set_state("normal")
            self.button.set_state("normal")
            self.stop_button.set_state("disabled")
            self.undo_button.set_state("normal")
        self.bind("<Escape>", self._on_escape)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self._poll_id = self.after(50, self._poll)
        self._brief_id: str | None = self.after(1500, self._check_brief_loop)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = tk.Frame(self, bg=BG)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 10))
        header.grid_columnconfigure(1, weight=1)
        self._avatar = theme.load_avatar(40, bg=BG, ring=theme.MINT_DIM, master=header)
        avatar = tk.Label(header, image=self._avatar, bg=BG, bd=0)
        avatar.grid(row=0, column=0, rowspan=2, padx=(0, 11))
        self.header = tk.Label(header, text="江慕白", bg=BG, fg=TEXT, anchor="w",
                               font=("Microsoft YaHei UI", 13, "bold"))
        self.header.grid(row=0, column=1, sticky="w")
        subtitle_row = tk.Frame(header, bg=BG)
        subtitle_row.grid(row=1, column=1, sticky="w")
        dot = tk.Canvas(subtitle_row, width=7, height=7, bg=BG, highlightthickness=0)
        dot.create_oval(1, 1, 6, 6, fill=theme.MINT, outline="")
        dot.pack(side="left")
        self.subtitle = tk.Label(subtitle_row, text="jmb · 正在启动…", bg=BG, fg=MUTED,
                                 anchor="w", font=theme.FONT_TINY)
        self.subtitle.pack(side="left", padx=(5, 0))
        self.brief_button = RoundedButton(header, "清单", command=self.show_brief,
                                          width=62, height=32, fill=theme.PANEL_2,
                                          fg=TEXT, hover=theme.BORDER,
                                          font=theme.FONT_SMALL, radius=12)
        self.brief_button.grid(row=0, column=2, rowspan=2, padx=(6, 0))
        self.more_button = RoundedButton(header, "···", command=self._show_menu,
                                         width=38, height=32, fill=theme.PANEL_2,
                                         fg=MUTED, hover=theme.BORDER,
                                         font=theme.FONT, radius=12)
        self.more_button.grid(row=0, column=3, rowspan=2, padx=(6, 0))

        self._sep = tk.Canvas(self, height=2, bg=BG, highlightthickness=0)
        self._sep.grid(row=1, column=0, sticky="ew")
        self._sep.bind("<Configure>", self._draw_separator)

        self.chat = ChatView(self)
        self.chat.grid(row=2, column=0, sticky="nsew", padx=8)
        self.chat.on_edit_user = self.edit_user
        self.text = self.chat  # 兼容旧代码/测试里的 text.get()

        bottom = tk.Frame(self, bg=BG)
        bottom.grid(row=3, column=0, sticky="ew", padx=18, pady=(8, 6))
        bottom.grid_columnconfigure(0, weight=1)
        self.input = InputBar(bottom, on_return=self.send)
        self.input.grid(row=0, column=0, sticky="ew")
        self.entry = self.input.entry
        self.button = RoundedButton(bottom, "发送", command=self.send, width=74,
                                    height=46, fill=theme.MINT, fg=BG,
                                    hover="#8af0de", font=theme.FONT, radius=15)
        self.button.grid(row=0, column=1, padx=(8, 0))
        self.stop_button = RoundedButton(bottom, "停止", command=self.stop_generation,
                                         width=62, height=46, fill=theme.PANEL_2,
                                         fg=theme.ERROR, hover="#3a2426",
                                         disabled_fill=theme.PANEL_2,
                                         disabled_fg=theme.MUTED, font=theme.FONT,
                                         radius=15)
        self.stop_button.grid(row=0, column=2, padx=(8, 0))
        self.stop_button.set_state("disabled")
        self.undo_button = RoundedButton(bottom, "撤销", command=self.undo, width=62,
                                         height=46, fill=theme.PANEL_2, fg=TEXT,
                                         hover=theme.BORDER, disabled_fill=theme.PANEL_2,
                                         disabled_fg=theme.MUTED, font=theme.FONT,
                                         radius=15)
        self.undo_button.grid(row=0, column=3, padx=(8, 0))

        statusbar = tk.Frame(self, bg=BG)
        statusbar.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.status = tk.Label(statusbar, text="准备中…", bg=BG, fg=MUTED, anchor="w",
                               font=theme.FONT_TINY)
        self.status.pack(side="left")
        self.usage_label = tk.Label(statusbar, text="", bg=BG, fg=theme.MUTED,
                                    anchor="e", font=theme.FONT_TINY)
        self.usage_label.pack(side="right")

    def _copy_last(self) -> None:
        text = self.chat.last_text()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.config(text="已复制最后一条")

    def _draw_separator(self, event=None) -> None:
        canvas = self._sep
        width = event.width if event is not None else canvas.winfo_width()
        canvas.delete("all")
        canvas.create_line(0, 1, width, 1, fill=theme.BORDER)
        canvas.create_line(20, 1, min(width - 20, 82), 1,
                           fill=theme.MINT_DIM, width=2)

    def _apply_dark_titlebar(self) -> None:
        if not self._destroyed:
            theme.enable_dark_titlebar(self)

    def _fade_in(self, value: float = 0.0) -> None:
        if self._destroyed:
            return
        value = min(1.0, value + 0.18)
        try:
            self.attributes("-alpha", value)
        except tk.TclError:
            return
        if value < 1.0:
            self.after(16, lambda: self._fade_in(value))

    def _ui_state_path(self):
        return config.jmb_home() / "state" / "ui.json"

    def _restore_ui_state(self) -> None:
        try:
            data = json.loads(self._ui_state_path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        chat = data.get("chat")
        if isinstance(chat, str):
            match = re.match(r"^(\d{3,4})x(\d{3,4})([+-]\d+)([+-]\d+)$", chat)
            if match:
                width, height, x, y = (int(match.group(i)) for i in range(1, 5))
                screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
                if (720 <= width <= screen_w and 560 <= height <= screen_h
                        and -width + 100 <= x <= screen_w - 100
                        and -height + 100 <= y <= screen_h - 100):
                    self.geometry(chat)
        pet = data.get("pet")
        if isinstance(pet, list) and len(pet) == 2:
            try:
                self.pet.move_to(int(pet[0]), int(pet[1]))
            except (TypeError, ValueError):
                pass
        if data.get("pet_hidden"):
            self.pet.hide()

    def _save_ui_state(self) -> None:
        chat = (f"{self.winfo_width()}x{self.winfo_height()}"
                f"+{self.winfo_x()}+{self.winfo_y()}")
        state = {"chat": chat,
                 "pet": [self.pet.win.winfo_x(), self.pet.win.winfo_y()],
                 "pet_hidden": self.pet.hidden}
        try:
            path = self._ui_state_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def _show_menu(self) -> None:
        menu = tk.Menu(self, tearoff=0, bg=theme.PANEL, fg=TEXT,
                       activebackground=theme.MINT_DIM, activeforeground=TEXT,
                       bd=0, relief="flat")
        menu.add_command(label="今日清单", command=self.show_brief)
        menu.add_command(label="复制最后一条回复", command=self._copy_last)
        menu.add_command(label="撤销上一轮", command=self.undo)
        menu.add_command(label="模型设置…", command=self._open_model_config)
        menu.add_command(label="显示桌宠" if self.pet.hidden else "隐藏桌宠",
                         command=self._toggle_pet)
        menu.add_separator()
        menu.add_command(label="关于 jmb", command=lambda: show_message(
            self, "关于 jmb", "jmb · 江慕白\n本地会话 · Tkinter 壳"))
        menu.add_command(label="退出", command=self.close)
        x = self.more_button.winfo_rootx()
        y = self.more_button.winfo_rooty() + self.more_button.winfo_height() + 4
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _start_worker(self) -> None:
        self.worker = ChatWorker()
        self.worker.start()

    def _append(self, text: str, tag: str = "assistant") -> None:
        text = (text or "").strip("\n")
        for prefix in ("你> ", "jmb> "):
            if text.startswith(prefix):
                text = text[len(prefix):]
        role = tag if tag in ("user", "assistant", "meta", "warn", "edit", "error",
                              "notice") else "assistant"
        if text.strip():
            self.chat.append(text, role)

    def send(self) -> None:
        self._begin_turn(self.input.get().strip())

    def _begin_turn(self, text: str) -> None:
        if not text or self.busy or self.worker is None:
            return
        self.input.clear()
        self.chat.append(text, "user")
        self.busy = True
        self.input.set_state("disabled")
        self.button.set_state("disabled")
        # 立即允许停止；停止位在一轮结束才清，所以哪怕 worker 还没进 send 也能生效。
        self.stop_button.set_state("normal")
        self.undo_button.set_state("disabled")
        self.chat.show_typing(True)
        self.pet.set_state("thinking")
        self.status.config(text="在想了…")
        self.worker.send(text)

    def edit_user(self, index: int, text: str) -> None:
        if self.worker is None:
            return
        if self.busy:
            self.chat.append("先停止当前回复，再编辑这一条。", "warn")
            return
        new_text = ask_text(self, "编辑并重发", text)
        if new_text is None:
            return
        new_text = new_text.strip()
        if not new_text:
            return
        # 回退由 worker 先确认；成功后用 rewound 事件再动 UI，避免压缩后序号对不上时白删。
        self.busy = True
        self.input.set_state("disabled")
        self.button.set_state("disabled")
        self.stop_button.set_state("disabled")
        self.undo_button.set_state("disabled")
        self.status.config(text="正在重发…")
        self.pet.set_state("thinking")
        self.worker.edit_resend(index, new_text, text)

    def stop_generation(self) -> None:
        if not self.busy or self.worker is None:
            return
        self.worker.cancel_generation()
        self.stop_button.set_state("disabled")
        self.status.config(text="正在停止…")
        self.pet.set_state("waiting")

    def _on_escape(self, _event=None) -> None:
        if self.busy:
            self.stop_generation()

    def undo(self) -> None:
        if self.busy or self.worker is None:
            return
        self.undo_button.set_state("disabled")
        self.worker.undo()

    def _show_chat(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()
        self.input.focus_set()

    def _toggle_pet(self) -> None:
        if self.pet.hidden:
            self.pet.show()
        else:
            self.pet.hide()

    def _open_model_config(self) -> None:
        from .widgets import ask_model_config

        jmb_config = config.load_model_config()
        effective = config.resolve_model()
        values = ask_model_config(self, {
            "model": jmb_config.get("model", ""),
            "base_url": jmb_config.get("base_url", ""),
            "token_len": len(config.resolve_token().value),
            "effective": effective.value,
            "source": effective.source,
        })
        if values is None:
            return
        config.save_model_config(values["model"], values["base_url"], values["token"])
        show_message(self, "已保存", "模型设置已写进 jmb 自己的配置，重启 jmb app 后生效。")

    def _brief_paths(self) -> tuple:
        today = date.today()
        return (config.brief_state_path(today),
                config.jmb_home() / "state" / f"brief-{today.isoformat()}.md",
                config.jmb_home() / "state" / "brief-seen.json")

    def _check_brief_loop(self) -> None:
        if self._destroyed:
            return
        try:
            self._check_brief()
        except OSError:
            pass
        self._brief_id = self.after(60_000, self._check_brief_loop)

    def _check_brief(self) -> None:
        state, _md, seen_path = self._brief_paths()
        if not state.exists():
            return
        seen: dict = {}
        if seen_path.exists():
            try:
                seen = json.loads(seen_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                seen = {}
        mtime = state.stat().st_mtime
        if seen.get("file") == state.name and seen.get("mtime") == mtime:
            return
        count = ""
        try:
            count = str(json.loads(state.read_text(encoding="utf-8")).get("items", ""))
        except (OSError, ValueError):
            pass
        head = f"{count} 条新项目" if count else "清单已生成"
        self.chat.append(f"今天的清单好了（{head}）。点这条气泡或顶部「清单」看全文。",
                         "assistant")
        self.pet.bubble("今天的清单好了，点我看全文", 7000, on_click=self.show_brief)
        try:
            seen_path.parent.mkdir(parents=True, exist_ok=True)
            seen_path.write_text(json.dumps({"file": state.name, "mtime": mtime}),
                                 encoding="utf-8")
        except OSError:
            pass

    def show_brief(self) -> None:
        _state, md, _seen = self._brief_paths()
        if not md.exists():
            self.pet.bubble("今天还没有清单（10:00 那次没跑成，或还没到点）。", 5000)
            return
        if hasattr(os, "startfile"):
            try:
                os.startfile(str(md))
                return
            except OSError:
                pass
        self._append("\n[今日清单]\n" + md.read_text(encoding="utf-8") + "\n", "meta")

    def _poll(self) -> None:
        try:
            while True:
                kind, data = self.events_get()
                self._on_event(kind, data)
        except queue.Empty:
            pass
        if not self._destroyed:
            self._poll_id = self.after(50, self._poll)

    def events_get(self) -> tuple[str, object]:
        if self.worker is None:
            raise queue.Empty
        return self.worker.events.get_nowait()

    def _on_event(self, kind: str, data) -> None:
        if kind == "ready":
            self.header.config(text="江慕白")
            self.subtitle.config(text="jmb · 本地会话 · 在线")
            self.status.config(text="在线 · 本地会话")
            self.usage_label.config(text="")
            self.pet.set_state("idle")
            if not self.busy:
                self.input.set_state("normal")
                self.button.set_state("normal")
                self.stop_button.set_state("disabled")
                self.undo_button.set_state("normal")
                self.input.focus_set()
        elif kind == "text_start":
            self.chat.show_typing(False)
            self.chat.begin_stream()
            self.stop_button.set_state("normal")
            self.pet.set_state("working")
            self.status.config(text="在写…")
        elif kind == "text":
            self.chat.stream(str(data))
        elif kind == "text_end":
            self.chat.end_stream()
        elif kind == "thinking":
            self.stop_button.set_state("normal")
            self.pet.set_state("thinking")
            self.status.config(text="在想…")
        elif kind == "search":
            self.stop_button.set_state("normal")
            self.pet.set_state("searching")
            self.status.config(text="联网搜索中…")
        elif kind == "usage":
            self.usage_label.config(
                text=f"in {data.get('input', 0)} · cache {data.get('cache_read', 0)} "
                     f"· out {data.get('output', 0)}")
        elif kind == "activity":
            self.stop_button.set_state("normal")
            self.chat.append(str(data), "meta")
            self.pet.set_state("working")
        elif kind == "compacting":
            self.status.config(text="压缩上下文…")
            self.pet.set_state("working")
        elif kind == "compacted":
            self.chat.append(f"上下文已压缩：{data.get('before')} → {data.get('after')} 条",
                             "meta")
            self.status.config(text="在线 · 本地会话")
            self.pet.set_state("idle")
        elif kind == "warning":
            self.chat.append(str(data), "warn")
        elif kind == "self_edit":
            note = str(data.get("note", ""))
            self.chat.append(
                f"我改了自己的记录（{data.get('target', '?')}）"
                f"{('：' + note) if note else ''}，undo 可撤。", "edit")
            self.pet.set_state("waving")
            self.pet.bubble("我改了自己的记录，undo 可撤。", 3500, on_click=self._show_chat)
        elif kind == "code":
            receipt = str(data.get("receipt", ""))
            self.stop_button.set_state("normal")
            self.chat.append(f"{data.get('name')}\n{receipt[:2000]}", "meta")
            self.pet.set_state("working")
        elif kind == "undo":
            self.chat.append(f"已撤销：{data}", "edit")
            self.pet.set_state("waving")
            self.undo_button.set_state("normal")
        elif kind == "rewound":
            index = int(data.get("ordinal", -1))
            text = str(data.get("text", ""))
            self.chat.truncate_from_user(index)
            self.chat.append(text, "user")
            self.chat.show_typing(True)
            self.status.config(text="在想了…")
            self.pet.set_state("thinking")
        elif kind == "stopped":
            self.stop_button.set_state("disabled")
            self.chat.end_stream()
            self.chat.show_typing(False)
            self.chat.append("（已停止生成）", "meta")
            self.pet.set_state("idle")
            self.status.config(text="已停止")
        elif kind == "error":
            self.chat.end_stream()
            self.chat.show_typing(False)
            self.chat.append(f"这一轮出错：{data}", "error")
            self.stop_button.set_state("disabled")
            self.pet.set_state("failed")
        elif kind == "permission":
            self.pet.set_state("waiting")
            ok = ask_yes_no(self, "需要授权", str(data.get("text", "")), "允许", "拒绝")
            if self.worker is not None:
                self.worker.answer_permission(str(data.get("id", "")), ok)
            self.pet.set_state("thinking" if ok else "idle")
        elif kind == "confirm":
            items = data.get("items", [])
            more = data.get("more", 0)
            text = "\n".join(f"{i}) {body}" for i, body in enumerate(items, 1))
            if more:
                text += f"\n（还有 {more} 条下次再问）"
            text += "\n\n全部记进长期记忆吗？选“否”会全部不要。"
            self.pet.set_state("waiting")
            ok = ask_yes_no(self, "会话收尾", text, "全部记", "全部不要")
            if self.worker is not None:
                self.worker.answer_confirmation("ok" if ok else "no")
            self.pet.set_state("idle")
        elif kind == "closed":
            if self.worker is not None:
                self.worker.join(timeout=1)
            self._finish_close()
        elif kind == "turn_end":
            if self.worker is not None:
                self.worker.clear_cancel()
            self.busy = False
            self.chat.show_typing(False)
            self.chat.end_stream()
            self.input.set_state("normal")
            self.button.set_state("normal")
            self.stop_button.set_state("disabled")
            self.undo_button.set_state("normal")
            self.input.focus_set()
            self.pet.set_state("idle")
            self.status.config(text="在线 · 本地会话")
        elif kind == "fatal":
            self.chat.append(f"启动失败：{data}", "error")
            self.pet.set_state("failed")
            show_message(self, "启动失败", str(data))

    def close(self) -> None:
        if self._destroyed or self._closing:
            return
        self._closing = True
        if self.worker is not None and self.worker.is_alive():
            self.status.config(text="收尾中…")
            self.input.set_state("disabled")
            self.button.set_state("disabled")
            self.stop_button.set_state("disabled")
            self.undo_button.set_state("disabled")
            self.pet.set_state("waiting")
            self.worker.request_stop()
            return
        self._finish_close()

    def _finish_close(self) -> None:
        if self._destroyed:
            return
        if self._persist:
            self._save_ui_state()
        self._destroyed = True
        if self._poll_id is not None:
            try:
                self.after_cancel(self._poll_id)
            except tk.TclError:
                pass
        if self._brief_id is not None:
            try:
                self.after_cancel(self._brief_id)
            except tk.TclError:
                pass
        if self._titlebar_id is not None:
            try:
                self.after_cancel(self._titlebar_id)
            except tk.TclError:
                pass
        self.pet.close()
        self.destroy()


def run() -> int:
    window = MainWindow()
    window.mainloop()
    return 0

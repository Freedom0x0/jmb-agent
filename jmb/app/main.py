"""jmb 桌面 app 壳（Tkinter）：聊天窗口 + 内置桌宠事件流。"""
from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
import uuid
from tkinter import messagebox

from .pet import PetWindow

BG = "#1e1f22"
PANEL = "#26282c"
TEXT = "#e6e6e6"
MUTED = "#9aa0a6"


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

    def undo(self) -> None:
        self.inbox.put(("__undo__", None))

    def request_stop(self) -> None:
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
        self.title("jmb")
        self.geometry("860x640+140+80")
        self.minsize(640, 480)
        self.configure(bg=BG)
        self.busy = False
        self._closing = False
        self._destroyed = False
        self._poll_id: str | None = None
        self.worker: ChatWorker | None = None
        self.pet = PetWindow(self)
        self._build_ui()
        menubar = tk.Menu(self)
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="撤销", command=self.undo)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        self.config(menu=menubar)
        if start_worker:
            self._start_worker()
        else:
            self.header.config(text="jmb · UI 预览")
            self.status.config(text="未启动 worker")
            self.entry.config(state="normal")
            self.button.config(state="normal")
            self.undo_button.config(state="normal")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self._poll_id = self.after(50, self._poll)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.header = tk.Label(
            self, text="jmb · 启动中…", bg=BG, fg=TEXT, anchor="w",
            font=("Microsoft YaHei UI", 12, "bold"))
        self.header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 6))

        body = tk.Frame(self, bg=BG)
        body.grid(row=1, column=0, sticky="nsew", padx=16)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        self.text = tk.Text(
            body, bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="flat",
            wrap="word", state="disabled", padx=10, pady=10,
            font=("Microsoft YaHei UI", 10), spacing1=2, spacing3=2)
        scroll = tk.Scrollbar(body, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.text.tag_configure("user", foreground="#8ab4f8")
        self.text.tag_configure("assistant", foreground=TEXT)
        self.text.tag_configure("meta", foreground=MUTED)
        self.text.tag_configure("warn", foreground="#fdd663")
        self.text.tag_configure("edit", foreground="#c58af9")
        self.text.tag_configure("error", foreground="#f28b82")

        bottom = tk.Frame(self, bg=BG)
        bottom.grid(row=2, column=0, sticky="ew", padx=16, pady=10)
        bottom.grid_columnconfigure(0, weight=1)
        self.entry = tk.Entry(
            bottom, bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="flat",
            font=("Microsoft YaHei UI", 10), state="disabled")
        self.entry.grid(row=0, column=0, sticky="ew", ipady=8)
        self.entry.bind("<Return>", lambda _event: self.send())
        self.button = tk.Button(
            bottom, text="发送", command=self.send, state="disabled",
            bg="#3b82f6", fg="white", activebackground="#2563eb",
            activeforeground="white", relief="flat", padx=18, pady=6,
            font=("Microsoft YaHei UI", 10))
        self.button.grid(row=0, column=1, padx=(8, 0))
        self.undo_button = tk.Button(
            bottom, text="撤销", command=self.undo, state="disabled",
            bg="#3a3d42", fg=TEXT, activebackground="#4a4d52",
            activeforeground=TEXT, relief="flat", padx=14, pady=6,
            font=("Microsoft YaHei UI", 10))
        self.undo_button.grid(row=0, column=2, padx=(8, 0))

        self.status = tk.Label(
            self, text="准备中…", bg=BG, fg=MUTED, anchor="w",
            font=("Microsoft YaHei UI", 9))
        self.status.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 10))

    def _start_worker(self) -> None:
        self.worker = ChatWorker()
        self.worker.start()

    def _append(self, text: str, tag: str = "assistant") -> None:
        self.text.configure(state="normal")
        self.text.insert("end", text, tag)
        self.text.see("end")
        self.text.configure(state="disabled")

    def send(self) -> None:
        text = self.entry.get().strip()
        if not text or self.busy or self.worker is None:
            return
        self.entry.delete(0, "end")
        self._append(f"你> {text}\n", "user")
        self.busy = True
        self.entry.config(state="disabled")
        self.button.config(state="disabled")
        self.undo_button.config(state="disabled")
        self.pet.set_state("thinking")
        self.status.config(text="它收到了，在想…")
        self.worker.send(text)

    def undo(self) -> None:
        if self.busy or self.worker is None:
            return
        self.undo_button.config(state="disabled")
        self.worker.undo()

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
            self.header.config(text=f"jmb · 会话 {data['tid']} · 线路 {data['profile']}")
            self.status.config(text=f"转录：{data['transcript']}")
            if not self.busy:
                self.entry.config(state="normal")
                self.button.config(state="normal")
                self.undo_button.config(state="normal")
                self.entry.focus_set()
        elif kind == "text_start":
            self._append("jmb> ", "assistant")
            self.pet.set_state("working")
        elif kind == "text":
            self._append(str(data), "assistant")
        elif kind == "text_end":
            self._append("\n", "assistant")
        elif kind == "thinking":
            self.pet.set_state("thinking")
            self.status.config(text="它在想…")
        elif kind == "search":
            self.pet.set_state("searching")
            self.status.config(text="联网搜索中…")
        elif kind == "usage":
            self.status.config(
                text=f"in={data.get('input', 0)} cache={data.get('cache_read', 0)} "
                     f"out={data.get('output', 0)}")
        elif kind == "activity":
            self._append(f"{data}\n", "meta")
            self.pet.set_state("working")
        elif kind == "warning":
            self._append(f"{data}\n", "warn")
        elif kind == "self_edit":
            note = str(data.get("note", ""))
            self._append(
                f"[它改了 {data.get('target', '?')}，undo 可撤]"
                f"{('：' + note) if note else ''}\n", "edit")
            self.pet.set_state("waving")
            self.pet.bubble("我改了自己的记录，undo 可撤。", 3500)
        elif kind == "code":
            receipt = str(data.get("receipt", ""))
            self._append(f"[{data.get('name')}]\n{receipt[:2000]}\n", "meta")
            self.pet.set_state("working")
        elif kind == "undo":
            self._append(f"[undo] {data}\n", "edit")
            self.pet.set_state("waving")
            self.undo_button.config(state="normal")
        elif kind == "error":
            self._append(f"[这一轮出错：{data}]\n", "error")
            self.pet.set_state("failed")
        elif kind == "permission":
            ok = messagebox.askyesno("jmb 需要授权", str(data.get("text", "")), parent=self)
            if self.worker is not None:
                self.worker.answer_permission(str(data.get("id", "")), ok)
        elif kind == "confirm":
            items = data.get("items", [])
            more = data.get("more", 0)
            text = "\n".join(f"{i}) {body}" for i, body in enumerate(items, 1))
            if more:
                text += f"\n（还有 {more} 条下次再问）"
            text += "\n\n全部记进长期记忆吗？选“否”会全部不要。"
            ok = messagebox.askyesno("jmb 会话收尾", text, parent=self)
            if self.worker is not None:
                self.worker.answer_confirmation("ok" if ok else "no")
        elif kind == "closed":
            if self.worker is not None:
                self.worker.join(timeout=1)
            self._finish_close()
        elif kind == "turn_end":
            self.busy = False
            self.entry.config(state="normal")
            self.button.config(state="normal")
            self.undo_button.config(state="normal")
            self.entry.focus_set()
            self.pet.set_state("idle")
        elif kind == "fatal":
            self._append(f"[启动失败：{data}]\n", "error")
            self.pet.set_state("failed")
            messagebox.showerror("jmb 启动失败", str(data))

    def close(self) -> None:
        if self._destroyed or self._closing:
            return
        self._closing = True
        if self.worker is not None and self.worker.is_alive():
            self.status.config(text="收尾中…")
            self.entry.config(state="disabled")
            self.button.config(state="disabled")
            self.undo_button.config(state="disabled")
            self.pet.set_state("waiting")
            self.worker.request_stop()
            return
        self._finish_close()

    def _finish_close(self) -> None:
        if self._destroyed:
            return
        self._destroyed = True
        if self._poll_id is not None:
            try:
                self.after_cancel(self._poll_id)
            except tk.TclError:
                pass
        self.pet.close()
        self.destroy()


def run() -> int:
    window = MainWindow()
    window.mainloop()
    return 0

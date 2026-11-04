"""滚动会话（D53）：conversation.json 存取 + 文件权威同步 + 渲染上限。"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jmb import chat


class ConversationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name) / "home"
        self.home.mkdir()
        self._env = mock.patch.dict(os.environ, {"JMB_HOME": str(self.home)}, clear=False)
        self._env.start()
        self.addCleanup(self._env.stop)

    def test_save_load_roundtrip(self) -> None:
        history = [{"role": "user", "content": "hi"},
                   {"role": "assistant", "content": [{"type": "text", "text": "在"}]}]
        render = [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "在"}]
        ts = chat.save_conversation(history, render)
        self.assertGreater(ts, 0)
        saved = chat.load_conversation()
        self.assertEqual(saved["history"], history)
        self.assertEqual(saved["render"], render)

    def test_sync_adopts_newer_file(self) -> None:
        theirs = [{"role": "user", "content": "手机聊的"}]
        chat.save_conversation(theirs, [{"role": "user", "text": "手机聊的"}])
        # since=0 ⟹ 文件更新 ⟹ 采用文件的（另一入口刚聊的轮次进上下文）
        adopted, _, ts = chat.conversation_sync(
            [{"role": "user", "content": "本地的"}], [], 0.0)
        self.assertEqual(adopted, theirs)
        # 自己刚落盘的文件不再被采纳（mtime == ts），undo/压缩后的内存状态不被回滚
        kept, _, _ = chat.conversation_sync(
            [{"role": "user", "content": "本地的"}], [], ts)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["content"], "本地的")

    def test_render_capped_at_500(self) -> None:
        render = [{"role": "user", "text": str(i)} for i in range(600)]
        chat.save_conversation([], render)
        saved = chat.load_conversation()
        self.assertEqual(len(saved["render"]), 500)
        self.assertEqual(saved["render"][0]["text"], "100")  # 留最后 500 条

    def test_load_ignores_broken_json(self) -> None:
        path = chat.conversation_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{oops", encoding="utf-8")
        self.assertEqual(chat.load_conversation(), {})


if __name__ == "__main__":
    unittest.main()

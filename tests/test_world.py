from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from jmb import chat, prefix, world


def _payload() -> dict:
    return {
        "current": {
            "time": "2026-10-31T19:45",
            "temperature_2m": 9.6,
            "relative_humidity_2m": 62,
            "apparent_temperature": 7.6,
            "weather_code": 3,
            "wind_speed_10m": 2.4,
        },
        "daily": {
            "temperature_2m_max": [11.3],
            "temperature_2m_min": [4.8],
            "sunrise": ["2026-10-31T06:41"],
            "sunset": ["2026-10-31T17:14"],
        },
    }


def _weather(city: str = "北京", fetched_at: float | None = None):
    return world.parse_weather(_payload(), city, fetched_at or time.time())


class WorldFactsTest(unittest.TestCase):
    def test_parse_weather_and_code(self) -> None:
        parsed = _weather()
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.description, "阴")
        self.assertAlmostEqual(parsed.temperature, 9.6)
        self.assertAlmostEqual(parsed.high, 11.3)
        self.assertAlmostEqual(parsed.low, 4.8)

    def test_context_has_time_place_and_weather(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            facts = world.WorldFacts(
                city="北京", timezone="Asia/Shanghai", cache_path=Path(tmp) / "w.json",
                auto_refresh=False, fetcher=lambda *_: _weather(fetched_at=time.time()))
            self.assertIsNotNone(facts.refresh())
            text = facts.context(now=dt.datetime(
                2026, 10, 31, 19, 58, tzinfo=ZoneInfo("Asia/Shanghai")))
        self.assertIn("2026-10-31 星期六 19:58", text)
        self.assertIn("UTC+08:00", text)
        self.assertIn("地点：北京", text)
        self.assertIn("阴，9.6°C", text)
        self.assertIn("4.8–11.3°C", text)
        self.assertIn("日出 06:41 / 日落 17:14", text)
        self.assertIn("世界事实", text)

    def test_no_weather_is_reported_honestly(self) -> None:
        def broken(*_args):
            raise RuntimeError("offline")

        with tempfile.TemporaryDirectory() as tmp:
            facts = world.WorldFacts(
                city="北京", timezone="Asia/Shanghai", cache_path=Path(tmp) / "w.json",
                auto_refresh=False, fetcher=broken)
            self.assertIsNone(facts.refresh())
            text = facts.context(now=dt.datetime(
                2026, 10, 31, 19, 58, tzinfo=ZoneInfo("Asia/Shanghai")))
        self.assertIn("天气：暂未取到", text)
        self.assertNotIn("°C", text)

    def test_cache_roundtrip_and_city_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "w.json"
            facts = world.WorldFacts(
                city="北京", timezone="Asia/Shanghai", cache_path=cache,
                auto_refresh=False, fetcher=lambda *_: _weather())
            facts.refresh()
            self.assertTrue(cache.exists())
            data = json.loads(cache.read_text(encoding="utf-8"))
            self.assertEqual(data["city"], "北京")
            self.assertEqual(data["description"], "阴")

            other = world.WorldFacts(
                city="上海", timezone="Asia/Shanghai", cache_path=cache,
                auto_refresh=False, fetcher=lambda *_: None)
            self.assertIsNone(other._weather)

    def test_surface_mentions_world_facts(self) -> None:
        self.assertIn("世界事实", prefix._SURFACE)

    def test_chat_injects_world_facts_into_system(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"JMB_HOME": tmp}):
                # D49 起凭据只认 jmb/config.json；这里塞假 token 即可，_stream_turn 已被 mock
                (Path(tmp) / "config.json").write_text(
                    json.dumps({"token": "sk-test"}), encoding="utf-8")
                session = chat.ChatSession(lambda *_args: None)
                session.world = world.WorldFacts(
                    city="北京", timezone="Asia/Shanghai",
                    cache_path=Path(tmp) / "w.json", auto_refresh=False,
                    fetcher=lambda *_: _weather(fetched_at=time.time()))
                session.world.refresh()
                captured: dict = {}

                def fake_stream(profile, count_fn, system, tools, history, log,
                                fact_memory, code_session, emit, budget=0, cancel=None):
                    captured["system"] = system
                    return {}

                with mock.patch("jmb.chat._stream_turn", side_effect=fake_stream):
                    session.send("现在几点？今天北京天气怎么样？")
                session.close()
        self.assertIn("世界事实", captured["system"])
        self.assertIn("地点：北京", captured["system"])
        self.assertIn("阴，9.6°C", captured["system"])


if __name__ == "__main__":
    unittest.main()

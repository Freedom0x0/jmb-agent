from __future__ import annotations

import datetime as dt
import unittest

from jmb import brief

TODAY = dt.date(2026, 10, 29)


HDX_LISTING = """
<div class="search-tab-content-item-mesh" style="position: relative;">
  <a href="/event/111?utm_source=x" target="_blank">
    <img class="item-logo" src="x.jpg" alt="AI 开发者沙龙" />
  </a>
  <div class="item-mesh-conter">
    <a class="item-title" href="/event/111?utm_source=x" target="_blank">
      <span style="vertical-align: middle;">AI 开发者沙龙</span>
    </a>
    <div class="item-dress flex">
      <p>11/01 周日 14:00</p>
      <span><span class="item-dress-pp">北京海淀</span></span>
    </div>
    <p class="user-name">某社区</p>
  </div>
</div>
<div class="search-tab-content-item-mesh" style="position: relative;">
  <a href="/event/222?utm_source=x" target="_blank">
    <img class="item-logo" src="y.jpg" alt="上海设计展" />
  </a>
  <div class="item-mesh-conter">
    <a class="item-title" href="/event/222?utm_source=x" target="_blank">
      <span style="vertical-align: middle;">上海设计展</span>
    </a>
    <div class="item-dress flex">
      <p>明天 09:00</p>
      <span><span class="item-dress-pp">上海静安</span></span>
    </div>
  </div>
</div>
"""


HDX_DETAIL = """
<script>
var ativityJson = {"Title":"AI 开发者沙龙","Start":"/Date(%d)/","IsFree":true,
"City":"海淀","Address":"中关村大街 1 号"};
</script>
"""


LIANPU_LISTING = """
<article class="bg-white py-4">
  <a href="/event/free-ai"><img alt="大模型技术沙龙" /></a>
  <div class="flex flex-wrap items-center gap-2"><span>免费</span></div>
  <h3><a href="/event/free-ai">大模型技术沙龙</a></h3>
  <p class="mt-2 line-clamp-1 text-sm leading-6">AI 模型技术分享</p>
  <div><span><time dateTime="2026-10-30T06:00:00.000Z">10月30日 14:00</time></span></div>
  <p class="line-clamp-1">北京 / 北京 海淀区某地</p>
</article>
<article class="bg-white py-4">
  <a href="/event/paid"><img alt="AI 营销大会" /></a>
  <div class="flex flex-wrap items-center gap-2"><div>¥99</div></div>
  <h3><a href="/event/paid">AI 营销大会</a></h3>
  <p class="mt-2 line-clamp-1 text-sm leading-6">免费茶歇，营销增长</p>
  <div><span><time dateTime="2026-11-01T06:00:00.000Z">11月1日 14:00</time></span></div>
  <p class="line-clamp-1">北京 / 北京 朝阳区某地</p>
</article>
"""


class BriefEventTest(unittest.TestCase):
    def test_hdx_when_formats(self) -> None:
        self.assertEqual(brief._parse_hdx_when("11/01 周日 14:00", TODAY),
                         dt.datetime(2026, 11, 1, 14, 0))
        self.assertEqual(brief._parse_hdx_when("明天 09:00", TODAY),
                         dt.datetime(2026, 10, 30, 9, 0))
        self.assertEqual(brief._parse_hdx_when("今天 18:30", TODAY),
                         dt.datetime(2026, 10, 29, 18, 30))
        self.assertEqual(brief._parse_hdx_when("11/19 周四 ~ 11/21 周六", TODAY),
                         dt.datetime(2026, 11, 19, 0, 0))
        self.assertEqual(brief._parse_hdx_when("12/30 周三 09:00", TODAY),
                         dt.datetime(2026, 12, 30, 9, 0))

    def test_hdx_listing_uses_alt_title_and_district(self) -> None:
        cards = brief._parse_hdx_listing(HDX_LISTING, TODAY)
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]["title"], "AI 开发者沙龙")
        self.assertEqual(cards[0]["district"], "北京海淀")
        self.assertEqual(cards[0]["start"], dt.datetime(2026, 11, 1, 14, 0))
        self.assertEqual(cards[1]["start"], dt.datetime(2026, 10, 30, 9, 0))

    def test_hdx_detail_parses_date_string_and_free(self) -> None:
        stamp = int(dt.datetime(2026, 11, 1, 14, 0).timestamp() * 1000)
        detail = brief._parse_hdx_detail(HDX_DETAIL % stamp)
        self.assertIsNotNone(detail)
        self.assertTrue(detail["is_free"])
        self.assertEqual(detail["title"], "AI 开发者沙龙")
        self.assertEqual(detail["start"], dt.datetime(2026, 11, 1, 14, 0))
        self.assertEqual(detail["city"], "海淀")

    def test_lianpu_free_badge_and_venue(self) -> None:
        cards = brief._parse_lianpu_listing(LIANPU_LISTING)
        self.assertEqual(len(cards), 2)
        free = [c for c in cards if c["free"]]
        self.assertEqual(len(free), 1)
        self.assertEqual(free[0]["title"], "大模型技术沙龙")
        self.assertTrue(free[0]["venue"].startswith("北京"))
        expected = dt.datetime.fromisoformat("2026-10-30T06:00:00+00:00")
        expected = expected.astimezone().replace(tzinfo=None)
        self.assertEqual(free[0]["start"], expected)

    def test_relevant_event_blocks_marketing(self) -> None:
        self.assertTrue(brief._relevant_event("大模型技术沙龙"))
        self.assertTrue(brief._relevant_event("AI 开发者大会"))
        self.assertFalse(brief._relevant_event("AI 营销实战训练营"))
        self.assertFalse(brief._relevant_event("设计周"))

    def test_event_line_keeps_beijing_city_name(self) -> None:
        start = dt.datetime(2026, 10, 30, 14, 0)
        base = {"title": "AI 技术沙龙", "url": "u", "start": start, "source": "lianpu（补充）"}
        self.assertIn("北京 · 北京市海淀区某地",
                      brief._event_line({**base, "venue": "北京 · 北京市海淀区某地"}))
        self.assertIn("北京 · 218视觉工厂",
                      brief._event_line({**base, "venue": "北京 · 北京 218视觉工厂"}))

    def test_dedupe_same_slot_and_similar_title(self) -> None:
        start = dt.datetime(2026, 10, 31, 13, 0)
        events = [
            {"title": "快手技术沙龙第6期——从研发效能走向企业AI生产力",
             "start": start, "url": "a", "venue": "北京", "source": "活动行"},
            {"title": "从研发效能走向企业 AI 生产力 — 快手技术沙龙第 6 期",
             "start": start, "url": "b", "venue": "北京", "source": "lianpu（补充）"},
            {"title": "另一场 AI 大会", "start": start, "url": "c",
             "venue": "北京", "source": "活动行"},
        ]
        out = brief._dedupe(events)
        self.assertEqual([e["url"] for e in out], ["a", "c"])


if __name__ == "__main__":
    unittest.main()

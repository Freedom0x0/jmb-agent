"""一次性探测：这台机器上，哪些"活动源"真的抓得到、页面里有没有日期。

只读，不写任何状态。判据三条：
  1) 能不能连上（status / 异常）
  2) 正文里有没有 "2026-xx-xx" 这种日期
  3) 正文里有几个 "开始时间" / "/event/" 这种锚点（判断是不是详情链接/日期就在 HTML 里）
"""
from __future__ import annotations

import re
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) jmb-probe/0.1",
      "Accept-Language": "zh-CN,zh;q=0.9"}

CANDIDATES = [
    ("lianpu-北京", "https://lianpu.com/city/beijing"),
    ("lianpu-AI分类", "https://lianpu.com/category/ai"),
    ("lianpu-科技分类", "https://lianpu.com/category/tech"),
    ("GDG-北京", "https://gdg.community.dev/gdg-beijing/"),
    ("GDG-北京-events", "https://gdg.community.dev/gdg-beijing/events/"),
    ("PyConChina", "https://cn.pycon.org"),
    ("GOSIM", "https://www.gosim.org"),
    ("昇腾社区", "https://www.hiascend.com"),
    ("活动行", "https://www.huodongxing.com"),
    ("掘金活动", "https://juejin.cn/events"),
    ("开源中国", "https://www.oschina.net"),
    ("Meetup", "https://www.meetup.com/find/?keywords=agent&location=cn--Beijing"),
    ("Bing搜索", "https://cn.bing.com/search?q=%E5%8C%97%E4%BA%AC+AI+%E6%B2%99%E9%BE%99+%E5%85%8D%E8%B4%B9"),
    ("GitHub-API", "https://api.github.com/repos/Project-HAMi/HAMi"),
]

DATE_RE = re.compile(r"20\d{2}-\d{2}-\d{2}")


def probe(name: str, url: str) -> str:
    try:
        request = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(request, timeout=15) as response:
            status = response.status
            body = response.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001 —— 探测就是要看各种失败长什么样
        return f"{name:<16} ERR  {type(exc).__name__}: {exc}"
    dates = len(set(DATE_RE.findall(body)))
    anchors = body.count("开始时间") + body.count("/event/") + body.count('Event"')
    return (f"{name:<16} {status}  len={len(body):<7} 不同日期={dates:<4} "
            f"锚点={anchors}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for name, url in CANDIDATES:
        print(probe(name, url), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Phase 7：每日清单（10:00，D30：错过不补、无开机触发器）。

全程零模型调用（2026-10-27 评审定）：一句话介绍一律来自现成字段，没有就写
"（无介绍）"，不许编。榜单两源：GitHub 新高星（search API）+ star-history 周榜。
北京活动：活动行北京列表（详情页 IsFree 确认免费）+ GDG 北京（主办方页，报名页确认）
+ lianpu（补充，只认"免费"标签）。只留未来 45 天、北京、线下、AI/软件相关。
幂等：state/brief-<日期>.json 存在即不重跑。
"""
from __future__ import annotations

import datetime as _dt
import difflib
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from html import unescape

from . import config

_GITHUB_HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "jmb/0.1",
                   "X-GitHub-Api-Version": "2022-11-28"}
EVENT_WINDOW_DAYS = 45
_EVENT_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) jmb/0.1",
             "Accept-Language": "zh-CN,zh;q=0.9"}
_EVENT_ASCII = ("ai", "openai", "llm", "agent", "rag", "gpu", "copilot", "chatgpt",
                "deepseek", "kimi", "codex", "claude", "gemini", "mcp")
_EVENT_CN = ("人工智能", "大模型", "智能体", "机器学习", "深度学习", "多模态", "生成式",
             "模型", "算法", "算力", "开源", "开发者", "编程", "软件", "技术", "架构",
             "数据", "云原生", "机器人", "具身智能", "推理", "微调")
_CN_WEEKDAYS = "一二三四五六日"
_EVENT_BLOCK = re.compile(r"营销|获客|变现|增长|私域|招商|路演|融资|投资|咨询|训练营|"
                          r"实战营|对接会|生态伙伴|企业管理|IP\s*矩阵")
_RATE_LIMIT_MARK = "访问太快"


def _github_headers() -> dict:
    """env GITHUB_TOKEN/GH_TOKEN → `gh auth token` → 匿名（匿名 60/h 容易被打满，登录态 5000/h）。"""
    import os
    import subprocess
    headers = dict(_GITHUB_HEADERS)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    if not token:
        try:
            token = subprocess.run(["gh", "auth", "token"], capture_output=True,
                                   text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            token = ""
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_json(url: str, headers: dict | None = None, timeout: int = 25):
    request = urllib.request.Request(url, headers=headers or _github_headers())
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def _clean(text) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()[:160]


# ---- 源 1：GitHub 最近新建且星数高（没有官方 trending API，语义要写明，别让他以为是榜单）----

def github_trending(days: int = 14, min_stars: int = 80, limit: int = 12) -> list[dict]:
    since = (_dt.date.today() - _dt.timedelta(days=days)).isoformat()
    query = urllib.parse.quote(f"created:>{since} stars:>{min_stars}")
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page={limit}"
    try:
        data = _fetch_json(url, timeout=30)
    except (OSError, ValueError):
        return []
    items = []
    for repo in data.get("items", []):
        desc = _clean(repo.get("description")) or "（无介绍）"
        items.append({"repo": repo.get("full_name", ""), "url": repo.get("html_url", ""),
                      "intro": f"{desc}（★{repo.get('stargazers_count', '?')}）"})
    return [i for i in items if i["repo"]]


# ---- 源 2：star-history 周榜（抄 SkillAbout build_digest.py 的抓取/解析，布局变了就空手而归）----

def star_history_weekly(limit: int = 10) -> list[dict]:
    try:
        request = urllib.request.Request("https://www.star-history.com/",
                                         headers={"User-Agent": "Mozilla/5.0 jmb/0.1"})
        with urllib.request.urlopen(request, timeout=30) as response:
            page = response.read().decode("utf-8", "replace")
    except OSError:
        return []
    normalized = page.replace("&amp;", "&")
    weekly: list[dict] = []
    seen: set[str] = set()
    for row in re.findall(r'<li class="relative group">.*?</li>', normalized, re.S):
        repo_match = re.search(r'href="/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"', row)
        if not repo_match or repo_match.group(1) in seen:
            continue
        seen.add(repo_match.group(1))
        delta = re.search(r'title="(Up|Down)\s+(\d+)"', row, re.I)
        trend = "–"
        if delta:
            trend = "▲" if delta.group(1).lower() == "up" else "▼"
        weekly.append({"repo": repo_match.group(1), "trend": trend})
    return weekly[:limit]


def repo_description(repo: str) -> str:
    """GitHub API 取简介，失败退回抓 og:description（抄 SkillAbout）。"""
    try:
        data = _fetch_json(f"https://api.github.com/repos/{repo}", timeout=15)
        if isinstance(data, dict) and data.get("description"):
            return _clean(data["description"])
    except (OSError, ValueError):
        pass
    try:
        request = urllib.request.Request(f"https://github.com/{repo}",
                                         headers={"User-Agent": "Mozilla/5.0 jmb/0.1"})
        with urllib.request.urlopen(request, timeout=15) as response:
            page = response.read().decode("utf-8", "replace")
        match = re.search(r'property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', page, re.I)
        if match:
            text = unescape(match.group(1)).strip()
            if "contribute to" not in text.lower():
                return _clean(text)
    except OSError:
        pass
    return "（无介绍）"


def _load_cooldown() -> dict[str, str]:
    path = config.jmb_home() / "state" / "cooldown.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("shown", {}) if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_cooldown(shown: dict[str, str]) -> None:
    path = config.jmb_home() / "state" / "cooldown.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    keep = {url: day for url, day in shown.items()
            if (_dt.date.today() - _dt.date.fromisoformat(day)).days <= 30}
    path.write_text(json.dumps({"version": 1, "shown": keep}, ensure_ascii=False), encoding="utf-8")


# ---- 源 3：北京近期免费 AI/软件活动（社区/主办方为主，lianpu 只做补充）----

def _fetch_text(url: str, timeout: int = 25) -> str:
    request = urllib.request.Request(url, headers=_EVENT_UA)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def _fetch_hdx(url: str) -> tuple[str, bool]:
    """活动行连续请求会返回“访问太快”；等 6 秒重试一次，仍限流就如实返回。"""
    html = _fetch_text(url)
    if _RATE_LIMIT_MARK not in html:
        return html, False
    time.sleep(6)
    html = _fetch_text(url)
    return html, _RATE_LIMIT_MARK in html


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", text or ""))).strip()


def _looks_relevant(text: str) -> bool:
    low = (text or "").lower()
    for key in _EVENT_ASCII:
        if re.search(rf"(?<![a-z]){re.escape(key)}(?![a-z])", low):
            return True
    return any(key in (text or "") for key in _EVENT_CN)


def _relevant_event(text: str) -> bool:
    return _looks_relevant(text) and not _EVENT_BLOCK.search(text or "")


def _local(iso: str) -> _dt.datetime | None:
    if not iso:
        return None
    try:
        parsed = _dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone().replace(tzinfo=None)


def _weekday_cn(day: _dt.date) -> str:
    return _CN_WEEKDAYS[day.weekday()]


def _venue(city: str, address: str) -> str:
    city = (city or "").strip()
    if city and not city.startswith("北京"):
        city = "北京" + city
    if not city:
        city = "北京"
    return f"{city} · {address}" if address else city


def _parse_hdx_when(text: str, today: _dt.date) -> _dt.datetime | None:
    first = re.split(r"[~～]", text or "")[0].strip()
    match = re.match(r"(今天|明天|后天)\s*(?:周[一二三四五六日])?\s*(\d{1,2}):(\d{2})", first)
    if match:
        offset = {"今天": 0, "明天": 1, "后天": 2}[match.group(1)]
        day = today + _dt.timedelta(days=offset)
        return _dt.datetime.combine(day, _dt.time(int(match.group(2)), int(match.group(3))))
    match = re.match(r"(\d{1,2})/(\d{1,2})(?:\s*周[一二三四五六日])?(?:\s*(\d{1,2}):(\d{2}))?",
                     first)
    if not match:
        return None
    month, day = int(match.group(1)), int(match.group(2))
    hour = int(match.group(3)) if match.group(3) else 0
    minute = int(match.group(4)) if match.group(4) else 0
    try:
        start = _dt.datetime(today.year, month, day, hour, minute)
    except ValueError:
        return None
    if start.date() < today - _dt.timedelta(days=30):
        try:
            start = start.replace(year=today.year + 1)
        except ValueError:
            return None
    return start


def _parse_hdx_listing(html: str, today: _dt.date) -> list[dict]:
    """活动行北京列表页：服务端渲染的卡片，拿标题/时间/商圈/主办方。"""
    cards: list[dict] = []
    seen: set[str] = set()
    for block in re.split(r'<div class="search-tab-content-item-mesh"', html)[1:]:
        link = re.search(r'<a class="item-title" href="(/event/(\d+)[^"]*)"', block)
        title = (re.search(r'<img class="item-logo"[^>]*alt="([^"]*)"', block)
                 or re.search(r'<a class="item-title".*?<span[^>]*>(.*?)</span>', block, re.S))
        when = re.search(r'<div class="item-dress flex">\s*<p>\s*(.*?)\s*</p>', block, re.S)
        district = re.search(r'<span class="item-dress-pp">\s*(.*?)\s*</span>', block, re.S)
        org = re.search(r'<p class="user-name">\s*(.*?)\s*</p>', block, re.S)
        if not (link and title and when and district):
            continue
        event_id = link.group(2)
        if event_id in seen:
            continue
        seen.add(event_id)
        start = _parse_hdx_when(_plain(when.group(1)), today)
        if start is None:
            continue
        cards.append({"id": event_id,
                      "url": f"https://www.huodongxing.com/event/{event_id}",
                      "title": _plain(title.group(1)),
                      "start": start,
                      "district": _plain(district.group(1)),
                      "org": _plain(org.group(1)) if org else ""})
    return cards


def _parse_hdx_detail(html: str) -> dict | None:
    """活动行详情页里的 ativityJson：开始时间、是否免费、城市/地址。"""
    key = "var ativityJson = "
    index = html.find(key)
    if index < 0:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(html[index + len(key):])
        raw_start = data["Start"]
        if isinstance(raw_start, str):
            stamp = re.search(r"/Date\((\d+)\)/", raw_start)
            ms = int(stamp.group(1)) if stamp else 0
        else:
            ms = int(raw_start)
        start = _dt.datetime.fromtimestamp(ms / 1000)
    except (ValueError, KeyError, TypeError, OSError):
        return None
    return {"title": str(data.get("Title") or ""),
            "start": start,
            "is_free": bool(data.get("IsFree")),
            "city": str(data.get("City") or ""),
            "address": str(data.get("Address") or "")}


def huodongxing_beijing(limit: int = 5) -> tuple[list[dict], str]:
    try:
        html, limited = _fetch_hdx("https://www.huodongxing.com/events?city="
                                   + urllib.parse.quote("北京"))
    except OSError:
        return [], "活动行北京：抓取失败"
    if limited:
        return [], "活动行北京：被限流（访问太快）"
    now = _dt.datetime.now()
    horizon = now + _dt.timedelta(days=EVENT_WINDOW_DAYS)
    cards = _parse_hdx_listing(html, _dt.date.today())
    picked = [card for card in cards
              if card["district"].startswith("北京") and _relevant_event(card["title"])
              and now <= card["start"] <= horizon]
    events: list[dict] = []
    limited_details = 0
    time.sleep(0.5)
    for card in picked[:limit]:
        try:
            detail_html, limited = _fetch_hdx(card["url"])
        except OSError:
            continue
        if limited:
            limited_details += 1
            continue
        detail = _parse_hdx_detail(detail_html)
        time.sleep(0.8)
        if not detail or not detail["is_free"] or not (now <= detail["start"] <= horizon):
            continue
        events.append({"title": detail["title"] or card["title"],
                       "url": card["url"],
                       "start": detail["start"],
                       "venue": _venue(detail["city"], detail["address"]),
                       "source": "活动行"})
    note = f"活动行北京：列表 {len(cards)} 条，免费 {len(events)} 条"
    if limited_details:
        note += f"（详情限流 {limited_details} 条）"
    return events, note


def gdg_beijing(limit: int = 4) -> tuple[list[dict], str]:
    """GDG 北京主办方页；报名页在活动行，用 ativityJson.IsFree 确认免费。"""
    try:
        html = _fetch_text("https://gdg.community.dev/gdg-beijing/")
    except OSError:
        return [], "GDG 北京：抓取失败"
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not match:
        return [], "GDG 北京：页面结构变了"
    try:
        data = json.loads(match.group(1))
        rows = data["props"]["pageProps"]["prerenderData"]["upcomingEvents"]["results"]
    except (ValueError, KeyError, TypeError):
        return [], "GDG 北京：数据解析失败"
    now = _dt.datetime.now()
    horizon = now + _dt.timedelta(days=EVENT_WINDOW_DAYS)
    events: list[dict] = []
    limited_tickets = 0
    for row in rows[:limit]:
        start = _local(row.get("start_date", ""))
        if start is None or not (now <= start <= horizon):
            continue
        title, url = str(row.get("title") or ""), str(row.get("url") or "")
        try:
            detail_html = _fetch_text(url)
            detail_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                                     detail_html, re.S)
            detail = json.loads(detail_match.group(1)) if detail_match else {}
            ticket = (detail.get("props", {}).get("pageProps", {})
                      .get("customBlockData", {}).get("eventData", {})
                      .get("custom_tickets_url"))
            if not ticket:
                continue
            ticket_html, limited = _fetch_hdx(ticket)
            if limited:
                limited_tickets += 1
                continue
            ticket_detail = _parse_hdx_detail(ticket_html)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if not ticket_detail or not ticket_detail["is_free"]:
            continue
        events.append({"title": title, "url": url, "start": start,
                       "venue": _venue(ticket_detail["city"], ticket_detail["address"]),
                       "source": "GDG 北京"})
    note = f"GDG 北京：upcoming {len(rows)} 场，免费 {len(events)} 场"
    if limited_tickets:
        note += f"（报名页限流 {limited_tickets} 场）"
    return events, note


def _parse_lianpu_listing(html: str) -> list[dict]:
    cards: list[dict] = []
    for card in re.findall(r"<article\b.*?</article>", html, re.S):
        url = re.search(r'href="(/event/[^"]+)"', card)
        title = re.search(r'alt="([^"]+)"', card)
        stamp = re.search(r'<time dateTime="([^"]+)"', card)
        venue = re.search(r'<p class="line-clamp-1">([^<]+)</p>', card)
        desc = re.search(r'<p class="mt-2 line-clamp-1[^"]*">([^<]+)</p>', card)
        start = _local(stamp.group(1)) if stamp else None
        if not (url and title and start):
            continue
        cards.append({"title": _plain(title.group(1)),
                      "url": "https://lianpu.com" + url.group(1),
                      "start": start,
                      "venue": _plain(venue.group(1)) if venue else "",
                      "desc": _plain(desc.group(1)) if desc else "",
                      "free": bool(re.search(r">\s*免费\s*</(?:div|span)>", card))})
    return cards


def lianpu_beijing() -> tuple[list[dict], str]:
    cards: list[dict] = []
    failed = False
    for url in ("https://lianpu.com/city/beijing", "https://lianpu.com/category/ai"):
        try:
            cards += _parse_lianpu_listing(_fetch_text(url))
        except OSError:
            failed = True
    now = _dt.datetime.now()
    horizon = now + _dt.timedelta(days=EVENT_WINDOW_DAYS)
    events: list[dict] = []
    seen: set[str] = set()
    for card in cards:
        if card["url"] in seen:
            continue
        seen.add(card["url"])
        if not card["free"] or not card["venue"].startswith("北京"):
            continue
        if not (now <= card["start"] <= horizon):
            continue
        if not _relevant_event(card["title"] + " " + card["desc"]):
            continue
        events.append({"title": card["title"], "url": card["url"], "start": card["start"],
                       "venue": card["venue"].replace(" / ", " · "),
                       "source": "lianpu（补充）"})
    note = f"lianpu：免费北京 {len(events)} 条" + ("（部分页面抓取失败）" if failed else "")
    return events, note


def _norm_title(text: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", (text or "").lower())


def _dedupe(events: list[dict]) -> list[dict]:
    out: list[dict] = []
    for event in events:
        key = _norm_title(event["title"])
        if not key:
            continue
        duplicate = False
        for old in out:
            old_key = _norm_title(old["title"])
            if (key == old_key
                    or (len(key) >= 8 and len(old_key) >= 8
                        and (key in old_key or old_key in key))):
                duplicate = True
                break
            if abs((event["start"] - old["start"]).total_seconds()) <= 3600:
                match = difflib.SequenceMatcher(None, key, old_key).find_longest_match(
                    0, len(key), 0, len(old_key))
                if match.size >= 8:
                    duplicate = True
                    break
        if not duplicate:
            out.append(event)
    return out


def collect_events() -> tuple[list[dict], list[str]]:
    events: list[dict] = []
    notes: list[str] = []
    for source in (gdg_beijing, huodongxing_beijing, lianpu_beijing):
        try:
            found, note = source()
        except Exception as exc:  # noqa: BLE001 —— 单个源挂了不拖垮整份清单
            notes.append(f"{source.__name__}：{type(exc).__name__}")
            continue
        events.extend(found)
        notes.append(note)
    events = _dedupe(events)
    events.sort(key=lambda item: item["start"])
    return events[:10], notes


def _event_line(event: dict) -> str:
    start = event["start"]
    when = f"{start:%m/%d}（周{_weekday_cn(start.date())}）{start:%H:%M}"
    venue = re.sub(r"^北京 · 北京\s*", "北京 · ", event["venue"])
    return (f"{when} · {event['title'][:80]} · {venue[:60]} · 免费 · "
            f"{event['source']} · {event['url']}")


# ---- 组装 ----

def build() -> tuple[str, int]:
    today = _dt.date.today().isoformat()
    cooldown = _load_cooldown()
    gh = github_trending()
    gh_repos = {i["repo"] for i in gh}
    hot: list[dict] = []
    for row in star_history_weekly():
        if row["repo"] in gh_repos or row["repo"] in cooldown:
            continue
        hot.append({"repo": row["repo"], "url": f"https://github.com/{row['repo']}",
                    "intro": f"{repo_description(row['repo'])}（周榜{row['trend']}）"})
        cooldown[row["repo"]] = today
    _save_cooldown(cooldown)
    merged = (gh + hot)[:8]
    lines = [f"{i}) {m['repo']}  {m['url']}  {m['intro']}" for i, m in enumerate(merged, 1)]
    events, notes = collect_events()

    md = [f"# jmb 每日清单 {today}", "",
          "## 榜单（GitHub 最近新建高星 + star-history 周榜；按发现顺序，不是替你挑的）"]
    md += lines or ["（今天两个榜单源都没抓到，不编。）"]
    md += ["", f"## 北京 · 近期免费 AI/软件活动（未来 {EVENT_WINDOW_DAYS} 天）"]
    md += [f"- {_event_line(event)}" for event in events] or ["- 今天没抓到符合条件的活动。"]
    md += ["", f"> 来源：{'；'.join(notes)}"]
    md += ["", f"—— 生成于 {_dt.datetime.now().strftime('%H:%M')}，零模型调用。"]
    return "\n".join(md), len(merged)


def _notify_done(count: int) -> None:
    """Windows 通知：app 没开也能收到（app 开着时另有聊天窗口消息）。"""
    if sys.platform != "win32":
        return
    body = f"今天的清单好了（{count} 条新项目）。打开 jmb 看全文。"
    script = (
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
        "ContentType=WindowsRuntime] | Out-Null;"
        "$t=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
        "[Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
        "$x=$t.GetElementsByTagName('text');"
        "$x.Item(0).AppendChild($t.CreateTextNode('jmb')) | Out-Null;"
        f"$x.Item(1).AppendChild($t.CreateTextNode('{body}')) | Out-Null;"
        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('jmb')"
        ".Show([Windows.UI.Notifications.ToastNotification]::new($t))"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                       timeout=15, capture_output=True)
    except (OSError, subprocess.SubprocessError):
        pass


def run() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    today = _dt.date.today().isoformat()
    state_path = config.brief_state_path(_dt.date.today())
    md_path = config.jmb_home() / "state" / f"brief-{today}.md"
    if state_path.exists():
        print(f"今天已跑过（{state_path.name}），不再重跑（幂等）。内容：")
        print(md_path.read_text(encoding="utf-8") if md_path.exists() else "（内容文件不在了）")
        return 0
    text, count = build()
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(text, encoding="utf-8")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"ok": True, "items": count,
                                      "at": _dt.datetime.now().isoformat(timespec="seconds")},
                                     ensure_ascii=False), encoding="utf-8")
    print(text)
    print(f"\n已写入 {md_path}")
    _notify_done(count)
    return 0


def today_text() -> str:
    path = config.jmb_home() / "state" / f"brief-{_dt.date.today().isoformat()}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "今天还没跑日报（10:00 定时，或手动 `jmb brief`）。错过不补（D30）。"

"""Phase 7：每日清单（10:00，D30：错过不补、无开机触发器）。

全程零模型调用（2026-10-27 评审定）：一句话介绍一律来自现成字段，没有就写
"（无介绍）"，不许编。三源：GitHub 新高星（search API）+ star-history 周榜
（抓取件抄 SkillAbout build_digest.py，布局变了如实报）+ AI 会议（ccfddl 走
api.github.com 的 raw Accept，不碰 github 的 raw 直链域——本机实测超时）。
幂等：state/brief-<日期>.json 存在即不重跑。
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from html import unescape

from . import config

_GITHUB_HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "jmb/0.1",
                   "X-GitHub-Api-Version": "2022-11-28"}
_DISCLAIMER = ("大陆同城的活动我拿不到（活动行有验证码和登录墙，中文科技媒体的活动页是空壳或被拦）。"
               "以下是能确认时间地点的大会和港澳/新加坡的活动。")


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


# ---- 源 3：AI 会议（ccfddl 主内容 + GDG 兜一点；Meetup 未文档化端点，挂了只少一段）----

def _latest_conf_chunk(text: str) -> tuple[int, str] | None:
    """ccfddl 的 yml 是 记录级 title + confs: 列表（每年一条，含 date/place）。
    取年份最大的那一场。date/place 在 confs 条目里，先 year 后 place 后 date 或乱序都有。"""
    best: tuple[int, str] | None = None
    for chunk in re.split(r"\n\s+- year:", text)[1:]:
        year_match = re.match(r"\s*(\d{4})", chunk)
        if not year_match:
            continue
        year = int(year_match.group(1))
        if best is None or year > best[0]:
            best = (year, chunk)
    return best


def ccfddl_meetings(limit: int = 6) -> list[str]:
    try:
        entries = _fetch_json("https://api.github.com/repos/ccfddl/ccf-deadlines/contents/conference/AI",
                              headers=_github_headers(), timeout=30)
    except (OSError, ValueError):
        return []
    this_year = _dt.date.today().year
    out: list[str] = []
    for entry in entries:
        if len(out) >= limit or not str(entry.get("name", "")).endswith(".yml"):
            continue
        try:
            request = urllib.request.Request(entry["url"],
                                             headers={**_github_headers(), "Accept": "application/vnd.github.raw"})
            text = urllib.request.urlopen(request, timeout=20).read().decode("utf-8", "replace")
        except OSError:
            continue
        title = re.search(r"^\s*-?\s*title:\s*(.+)$", text, re.M)  # 文件是列表项：`- title: AAAI`
        best = _latest_conf_chunk(text)
        if not title or not best or best[0] < this_year:
            continue  # 只留今年及以后的场
        year, chunk = best
        date = re.search(r'^\s*date:\s*"?([^"\n]+)', chunk, re.M)
        place = re.search(r'^\s*place:\s*"?([^"\n]+)', chunk, re.M)
        when = f"{year} " + (date.group(1).strip() if date else "")
        where = place.group(1).strip() if place else "地点见官网"
        out.append(f"{title.group(1).strip()} — {when} · {where}（时间以官网为准）")
    return out


def gdg_meetings(cities=("beijing", "shanghai", "shenzhen", "hangzhou"), limit: int = 3) -> list[str]:
    """⚠️ 2026-10-28 三次尝试后标注未通：GDG 页面的活动数据已改由客户端渲染，
    __NEXT_DATA__ 里只剩站点元数据（20 个 2025 时间戳、0 个 /e/ 事件链接）。
    D27 本来就定位 ccfddl 是这一栏的主内容；GDG 留着函数壳，哪天页面回退再接。"""
    return []
    today = _dt.date.today().isoformat()  # noqa: E305 —— 上面 return 后的旧实现留作将来参考
    out: list[str] = []
    for city in cities:
        try:
            request = urllib.request.Request(f"https://gdg.community.dev/gdg-{city}/",
                                             headers={"User-Agent": "Mozilla/5.0 jmb/0.1"})
            with urllib.request.urlopen(request, timeout=20) as response:
                page = response.read().decode("utf-8", "replace")
        except OSError:
            continue
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
        if not match:
            continue
        for node in re.finditer(r'"title":"([^"]{4,120})","[^"]{0,40}?start_date":"(\d{4}-\d{2}-\d{2})',
                                match.group(1)):
            title, day = node.group(1), node.group(2)
            if day >= today and len(out) < limit:
                out.append(f"{title} — {day} · GDG {city}（时间以官网为准）")
    return out


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
    meetings = ccfddl_meetings() + gdg_meetings()

    md = [f"# jmb 每日清单 {today}", "",
          "## 榜单（GitHub 最近新建高星 + star-history 周榜；按发现顺序，不是替你挑的）"]
    md += lines or ["（今天两个榜单源都没抓到，不编。）"]
    md += ["", "## AI 线下会议", f"> {_DISCLAIMER}"]
    md += [f"- {m}" for m in meetings] or ["- 今天没抓到有日期地点的会。"]
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

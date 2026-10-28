"""联网读正文（spec §5.5）与兜底搜索（§5.4 第二层）。

fetch_page：直接抓 → HTML 走 trafilatura 提正文 → 提取过短时试 host 的
/llms.txt（里面常有指向 .md 的直链）→ 仍无则如实报"读不到正文"。
JS 渲染页提出来的导航残渣按 spec 一律算"读不到"。

bing_search：cn.bing.com 是本机唯一实测通的搜索腿（spec §5.4）。
只在 provider 不支持服务端搜索时作为客户端工具声明（Phase 2 providers）。
"""
from __future__ import annotations

import ipaddress
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from html import unescape

_UA = {"User-Agent": "Mozilla/5.0 jmb/0.1"}
_READ_UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "Chrome/126 Safari/537.36"), "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6"}
READ_CHAR_BUDGET = 6000
MIN_EXTRACT = 200  # spec §5.5 评审补：短于这个数按"读不到"
# 机器人墙特征：命中就当"读不到"，别把拦截页当正文讲
_BOT_WALL = ("enable javascript", "just a moment", "verify you are human", "access denied",
             "请开启 javascript", "请启用 javascript", "captcha")


def url_is_public(url: str) -> bool:
    """只允许公网 http(s)：拒绝 localhost、内网、回环、链路本地、保留地址。"""
    parts = urllib.parse.urlparse(url)
    if parts.scheme not in {"http", "https"}:
        return False
    host = (parts.hostname or "").strip().strip("[]").lower()
    if not host:
        return False
    if (host in {"localhost", "localhost.localdomain"}
            or host.endswith(".local") or host.endswith(".internal")):
        return False
    try:
        port = parts.port or (443 if parts.scheme == "https" else 80)
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (OSError, ValueError):
        return False
    for info in infos:
        address = str(info[4][0]).split("%")[0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return False
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_multicast or ip.is_reserved or ip.is_unspecified):
            return False
    return True


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not url_is_public(newurl):
            raise urllib.error.URLError(f"重定向到非公网地址：{newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_SafeRedirectHandler())


def _get(url: str, timeout: int = 25, headers: dict | None = None) -> tuple[str, str]:
    if not url_is_public(url):
        raise urllib.error.URLError(f"非公网地址：{url}")
    request = urllib.request.Request(url, headers=headers or _UA)
    with _OPENER.open(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, "replace"), response.headers.get("content-type", "")


def _extract_html(page: str) -> str:
    try:
        import trafilatura
    except ImportError:
        return ""
    return (trafilatura.extract(page) or "").strip()


def _llms_probe(url: str) -> str:
    """host 的 /llms.txt 里若有指向同路径的 .md 直链就抓它（实测 docs.github.com 等有）。"""
    parts = urllib.parse.urlparse(url)
    root = f"{parts.scheme}://{parts.netloc}"
    try:
        index, _ = _get(f"{root}/llms.txt", timeout=15)
    except OSError:
        return ""
    target = parts.path.rstrip("/")
    if not target:
        return ""
    for link in re.findall(r"\(([^)\s]+\.md)\)", index):
        candidate = link if link.startswith("http") else root + (link if link.startswith("/") else "/" + link)
        if target in urllib.parse.unquote(link):
            try:
                body, _ = _get(candidate, timeout=20)
            except OSError:
                continue
            if body.strip():
                return body
    return ""


def _looks_like_bot_wall(text: str) -> bool:
    head = text[:600].lower()
    return any(marker in head for marker in _BOT_WALL)


def fetch_page(url: str) -> str:
    url = url.strip()
    if not re.match(r"^https?://", url):
        return f"读不到：不是 http(s) 链接（{url[:60]}）。"
    if not url_is_public(url):
        return "读不到正文：只允许公网 http(s) 地址（localhost/内网被拒）。"
    try:
        page, ctype = _get(url, headers=_READ_UA)
    except urllib.error.URLError as exc:
        return f"读不到正文：{exc}"
    except OSError as exc:
        kind = "超时" if isinstance(exc, TimeoutError) or "timed out" in str(exc) else "抓取失败"
        return f"读不到正文：{kind}（{type(exc).__name__}）——404/403/超时都是正常结果，不是异常。"
    text = page
    if "html" in ctype.lower() or "<html" in page[:400].lower():
        text = _extract_html(page)
    if len(text) < MIN_EXTRACT or _looks_like_bot_wall(text):
        text = _llms_probe(url)
    if len(text) < MIN_EXTRACT or _looks_like_bot_wall(text):
        return "读不到正文：页面可能是 JS 渲染、反爬或机器人墙，提取不到真内容。我知道标题层面，不编内容。"
    if len(text) > READ_CHAR_BUDGET:
        text = text[:READ_CHAR_BUDGET] + f"\n…[已截断：原文约 {len(text)} 字符，要后续段落再说一声]"
    return text


# Bing 的选择器照抄 SkillAbout domestic_search.py（本机唯一实测通的搜索腿，别自创）
_BING_BLOCK_RE = re.compile(r'<li\b[^>]*class="[^"]*b_algo[^"]*"[^>]*>(?P<body>.*?)</li>', re.I | re.S)
_BING_TITLE_RE = re.compile(
    r'<h2\b[^>]*>\s*<a\b[^>]*href="(?P<href>https?://[^"]+)"[^>]*>(?P<title>.*?)</a>', re.I | re.S)
_BING_SNIPPET_RE = re.compile(r'<p\b[^>]*>(?P<text>.*?)</p>', re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(_TAG_RE.sub(" ", value or ""))).strip()


def _unwrap_bing(href: str) -> str:
    """Bing 的 /ck/a 跳转链里，真实地址 base64url 藏在 u=a1 参数——解开它。"""
    match = re.search(r"[?&]u=a1([A-Za-z0-9_-]+)", href)
    if not match:
        return href
    raw = match.group(1) + "=" * (-len(match.group(1)) % 4)
    try:
        import base64
        real = base64.urlsafe_b64decode(raw).decode("utf-8", "replace")
        return real if real.startswith("http") else href
    except Exception:  # noqa: BLE001
        return href


def bing_search(query: str, count: int = 5) -> str:
    """兜底搜索。⚠️ 2026-10-27 复测：cn.bing.com 已改成 JS 空壳（SkillAbout 当时的实测过期），
    www.bing.com 的 HTML 仍有 b_algo 块——用 www。布局再变就如实报，不编结果。"""
    try:
        page, _ = _get("https://www.bing.com/search?q=" + urllib.parse.quote(query),
                       timeout=20, headers=_READ_UA)
    except OSError as exc:
        return f"兜底搜索失败：{type(exc).__name__}（本机到 bing 的网络问题）。"
    lines: list[str] = []
    for block_match in _BING_BLOCK_RE.finditer(page):
        body = block_match.group("body")
        title_match = _BING_TITLE_RE.search(body)
        if not title_match:
            continue
        snippet = _BING_SNIPPET_RE.search(body[title_match.end():])
        summary = _strip_tags(snippet.group("text")) if snippet else ""
        real_href = _unwrap_bing(unescape(title_match.group("href")))
        lines.append(f"- {_strip_tags(title_match.group('title'))}\n  {real_href}"
                     + (f"\n  {_strip_tags(summary)[:160]}" if summary else ""))
        if len(lines) >= count:
            break
    if not lines:
        return "兜底搜索失败：结果块解析不出（Bing 改版了）。不编结果。"
    return "\n".join(lines)

"""世界事实：当前时间 + 城市天气。

每轮把一小段【世界事实】追加到 system 末尾（不动稳定前缀），让江慕白知道
“现在几点、今天几号、外面什么天气”。天气走 Open-Meteo（无需 key），后台刷新、
本地缓存；取不到就如实写“暂未取到”，绝不阻塞对话或编数据。
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from . import config

DEFAULT_CITY = "北京"
DEFAULT_LAT = 39.9042
DEFAULT_LON = 116.4074
DEFAULT_TIMEZONE = "Asia/Shanghai"
REFRESH_AFTER_SECONDS = 10 * 60
REQUEST_TIMEOUT = 6
_WEEKDAYS = "一二三四五六日"
_API = "https://api.open-meteo.com/v1/forecast"

_WMO = {
    0: "晴", 1: "晴间多云", 2: "多云", 3: "阴",
    45: "雾", 48: "雾凇",
    51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
    56: "冻毛毛雨", 57: "强冻毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    66: "冻雨", 67: "强冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "阵雨", 81: "强阵雨", 82: "暴雨",
    85: "阵雪", 86: "强阵雪",
    95: "雷阵雨", 96: "雷暴伴冰雹", 99: "强雷暴伴冰雹",
}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip() or default


def _zone():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(_env("JMB_TIMEZONE", DEFAULT_TIMEZONE))
    except Exception:  # noqa: BLE001 —— 时区名写错就退回系统本地时区
        return _dt.datetime.now().astimezone().tzinfo


def _now(now: _dt.datetime | None = None) -> _dt.datetime:
    zone = _zone()
    if now is None:
        return _dt.datetime.now(zone)
    if now.tzinfo is None:
        return now.replace(tzinfo=zone)
    return now.astimezone(zone)


def describe_code(code: int) -> str:
    return _WMO.get(int(code), f"天气代码 {code}")


@dataclass(frozen=True)
class Weather:
    city: str
    temperature: float
    feels_like: float
    humidity: int
    wind: float
    code: int
    high: float
    low: float
    sunrise: str
    sunset: str
    observed_at: str
    fetched_at: float
    description: str = ""

    def as_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Weather":
        return cls(
            city=str(data.get("city", "")),
            temperature=float(data["temperature"]),
            feels_like=float(data["feels_like"]),
            humidity=int(data["humidity"]),
            wind=float(data["wind"]),
            code=int(data["code"]),
            high=float(data["high"]),
            low=float(data["low"]),
            sunrise=str(data.get("sunrise", "")),
            sunset=str(data.get("sunset", "")),
            observed_at=str(data.get("observed_at", "")),
            fetched_at=float(data.get("fetched_at", 0)),
            description=str(data.get("description") or describe_code(int(data["code"]))),
        )


def parse_weather(payload: dict, city: str, fetched_at: float | None = None) -> Weather | None:
    try:
        current = payload["current"]
        daily = payload["daily"]
        code = int(current["weather_code"])
        return Weather(
            city=city,
            temperature=float(current["temperature_2m"]),
            feels_like=float(current["apparent_temperature"]),
            humidity=int(current["relative_humidity_2m"]),
            wind=float(current["wind_speed_10m"]),
            code=code,
            high=float(daily["temperature_2m_max"][0]),
            low=float(daily["temperature_2m_min"][0]),
            sunrise=str(daily["sunrise"][0]),
            sunset=str(daily["sunset"][0]),
            observed_at=str(current.get("time", "")),
            fetched_at=time.time() if fetched_at is None else fetched_at,
            description=describe_code(code),
        )
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def fetch_weather(city: str, lat: float, lon: float, timezone: str) -> Weather | None:
    query = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                   "weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,sunrise,sunset",
        "timezone": timezone,
        "forecast_days": 1,
    })
    request = urllib.request.Request(
        f"{_API}?{query}", headers={"User-Agent": "jmb-world/0.1"})
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return parse_weather(payload, city)


def _cache_path() -> Path:
    return config.jmb_home() / "state" / "world-weather.json"


def _clock(value: str) -> str:
    text = str(value or "")
    return text.split("T")[-1][:5] if "T" in text else text[:5]


def _offset(now: _dt.datetime) -> str:
    offset = now.utcoffset() or _dt.timedelta(0)
    total = int(offset.total_seconds())
    sign = "+" if total >= 0 else "-"
    hours, minutes = divmod(abs(total) // 60, 60)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


class WorldFacts:
    def __init__(self, city: str | None = None, lat: float | None = None,
                 lon: float | None = None, timezone: str | None = None,
                 cache_path: Path | None = None, fetcher=fetch_weather,
                 auto_refresh: bool = True) -> None:
        self.city = city or _env("JMB_CITY", DEFAULT_CITY)
        self.lat = _env_float("JMB_LAT", DEFAULT_LAT) if lat is None else lat
        self.lon = _env_float("JMB_LON", DEFAULT_LON) if lon is None else lon
        self.timezone = timezone or _env("JMB_TIMEZONE", DEFAULT_TIMEZONE)
        self.cache_path = Path(cache_path) if cache_path else _cache_path()
        self.auto_refresh = auto_refresh
        self._fetcher = fetcher
        self._lock = threading.Lock()
        self._refreshing = False
        self._last_attempt = 0.0
        self._weather = self._load_cache()

    def _load_cache(self) -> Weather | None:
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            weather = Weather.from_dict(data)
            if weather.city != self.city:
                return None
            return weather
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _save_cache(self, weather: Weather) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.cache_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(weather.as_dict(), ensure_ascii=False),
                           encoding="utf-8")
            tmp.replace(self.cache_path)
        except OSError:
            pass

    def refresh(self) -> Weather | None:
        """同步刷新一次（测试和后台线程共用）；失败返回 None，保留旧缓存。"""
        try:
            weather = self._fetcher(self.city, self.lat, self.lon, self.timezone)
        except Exception:  # noqa: BLE001 —— 网络/解析失败都不该影响对话
            return None
        if weather is None:
            return None
        with self._lock:
            self._weather = weather
        self._save_cache(weather)
        return weather

    def refresh_async(self) -> None:
        if not self.auto_refresh:
            return
        now = time.monotonic()
        with self._lock:
            if self._weather and time.time() - self._weather.fetched_at < REFRESH_AFTER_SECONDS:
                return
            if self._refreshing or now - self._last_attempt < 60:
                return
            self._refreshing = True
            self._last_attempt = now
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        try:
            self.refresh()
        finally:
            with self._lock:
                self._refreshing = False

    def _weather_line(self) -> str:
        weather = self._weather
        if weather is None:
            with self._lock:
                refreshing = self._refreshing
            return ("天气：正在获取（下一轮会更新）" if refreshing
                    else "天气：暂未取到（网络不可用；需要时再用联网搜索查）")
        age = max(0, int((time.time() - weather.fetched_at) // 60))
        if age <= 30:
            age_text = "刚刚更新" if age < 1 else f"更新于 {age} 分钟前"
        elif age <= 180:
            age_text = f"缓存 {age} 分钟前，仅供参考"
        else:
            age_text = f"缓存已过期（{age // 60} 小时前），仅供参考"
        return (
            f"天气：{weather.description}，{weather.temperature:.1f}°C"
            f"（体感 {weather.feels_like:.1f}°C），湿度 {weather.humidity}%，"
            f"风 {weather.wind:.1f} km/h；今日 {weather.low:.1f}–{weather.high:.1f}°C；"
            f"日出 {_clock(weather.sunrise)} / 日落 {_clock(weather.sunset)}；"
            f"观测 {_clock(weather.observed_at)}，{age_text}"
        )

    def context(self, now: _dt.datetime | None = None) -> str:
        if self.auto_refresh:
            self.refresh_async()
        current = _now(now)
        lines = [
            "【世界事实·实时】",
            f"现在：{current:%Y-%m-%d} 星期{_WEEKDAYS[current.weekday()]} "
            f"{current:%H:%M}（{_offset(current)}）",
            f"地点：{self.city}",
            self._weather_line(),
            "用法：回答时间、日期、天气时以这里为准；天气标了“缓存/过期”就照实说，"
            "不要编造此刻的数据。",
        ]
        return "\n".join(lines)

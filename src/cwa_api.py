"""中央氣象署（CWA）開放資料 API 的取得與解析邏輯。

資料集：F-C0032-001「一般天氣預報-今明 36 小時天氣預報」
文件：https://opendata.cwa.gov.tw/dist/opendata-swagger.html

本模組只負責「拿資料」與「整理資料」，不含任何 Streamlit UI 程式碼，
方便單獨測試與重複使用。
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests

API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"
REQUEST_TIMEOUT = 15  # 秒
TAIWAN_TZ = timezone(timedelta(hours=8))  # 台灣沒有日光節約時間，固定 UTC+8

# 22 個縣市（CWA 使用「臺」而非「台」）
CITIES = [
    "臺北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣",
    "苗栗縣", "臺中市", "彰化縣", "南投縣", "雲林縣", "嘉義市",
    "嘉義縣", "臺南市", "高雄市", "屏東縣", "宜蘭縣", "花蓮縣",
    "臺東縣", "澎湖縣", "金門縣", "連江縣",
]

# 地圖上每個縣市的標記位置（都在縣市境內；北部、嘉義、中部等密集處
# 刻意錯開，避免溫度標籤互相重疊，因此不一定是縣市政府所在地）
CITY_COORDS = {
    "臺北市": (25.04, 121.53), "新北市": (24.87, 121.62),
    "基隆市": (25.14, 121.78), "桃園市": (24.93, 121.22),
    "新竹市": (24.80, 120.95), "新竹縣": (24.62, 121.18),
    "苗栗縣": (24.50, 120.85), "臺中市": (24.24, 120.85),
    "彰化縣": (24.03, 120.50), "南投縣": (23.85, 120.95),
    "雲林縣": (23.70, 120.43), "嘉義市": (23.48, 120.45),
    "嘉義縣": (23.30, 120.58), "臺南市": (23.05, 120.25),
    "高雄市": (23.00, 120.68), "屏東縣": (22.55, 120.58),
    "宜蘭縣": (24.65, 121.70), "花蓮縣": (23.75, 121.40),
    "臺東縣": (22.80, 121.10), "澎湖縣": (23.57, 119.58),
    "金門縣": (24.44, 118.36), "連江縣": (26.16, 119.95),
}

# 依國家發展委員會的區域劃分；金門縣、連江縣屬離島，不列入四區平均
REGIONS = {
    "北部": ["臺北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣", "宜蘭縣"],
    "中部": ["苗栗縣", "臺中市", "彰化縣", "南投縣", "雲林縣"],
    "南部": ["嘉義市", "嘉義縣", "臺南市", "高雄市", "屏東縣", "澎湖縣"],
    "東部": ["花蓮縣", "臺東縣"],
}

# API 回傳的天氣要素代碼 -> 本專案使用的欄位名稱
ELEMENT_FIELDS = {
    "Wx": "weather",      # 天氣現象
    "PoP": "pop",         # 降雨機率（%）
    "MinT": "min_temp",   # 最低溫（°C）
    "MaxT": "max_temp",   # 最高溫（°C）
    "CI": "comfort",      # 舒適度
}


class CWAError(Exception):
    """呼叫或解析 CWA API 失敗時拋出，讓 UI 層可以顯示友善訊息。"""


@dataclass
class ForecastPeriod:
    """單一預報時段（F-C0032-001 每個縣市共 3 個時段，各 12 小時）。"""

    start_time: str
    end_time: str
    weather: str
    min_temp: Optional[int]
    max_temp: Optional[int]
    pop: Optional[int]
    comfort: str

    @property
    def period_label(self) -> str:
        """產生易讀的時段標籤，例如「10/06 18:00 ~ 10/07 06:00」。"""
        return f"{_short_time(self.start_time)} ~ {_short_time(self.end_time)}"

    def as_row(self) -> dict[str, Any]:
        """轉成適合放進 pandas DataFrame 的一列資料。"""
        return {
            "預報時段": self.period_label,
            "天氣狀況": self.weather,
            "最低溫 (°C)": self.min_temp,
            "最高溫 (°C)": self.max_temp,
            "降雨機率 (%)": self.pop,
            "舒適度": self.comfort,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_api_key() -> Optional[str]:
    """依序從環境變數、.env、Streamlit secrets 取得 API 金鑰。

    金鑰一律不寫在程式碼裡，找不到時回傳 None 由 UI 層提示使用者設定。
    """
    key = os.environ.get("CWA_API_KEY")
    if key:
        return key.strip()

    # 支援專案根目錄的 .env（需安裝 python-dotenv，未安裝則略過）
    try:
        from dotenv import load_dotenv

        load_dotenv()
        key = os.environ.get("CWA_API_KEY")
        if key:
            return key.strip()
    except ImportError:
        pass

    # 支援 .streamlit/secrets.toml，僅在 Streamlit 環境下可用
    try:
        import streamlit as st

        if "CWA_API_KEY" in st.secrets:
            return str(st.secrets["CWA_API_KEY"]).strip()
    except Exception:
        pass

    return None


def normalize_city(city: str) -> str:
    """把常見的「台北市」寫法轉為 API 使用的「臺北市」。"""
    return city.strip().replace("台", "臺")


def fetch_forecast(api_key: str, city: Optional[str] = None) -> dict[str, Any]:
    """向 CWA API 查詢 36 小時預報，回傳原始 JSON。

    city 省略時一次取得全部 22 縣市（地圖需要全部資料）。
    """
    if not api_key:
        raise CWAError("尚未設定 CWA API 金鑰。")

    params = {
        "Authorization": api_key,
        "elementName": ",".join(ELEMENT_FIELDS),
    }
    if city:
        params["locationName"] = normalize_city(city)

    try:
        response = requests.get(API_URL, params=params, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.Timeout as exc:
        raise CWAError("連線 CWA API 逾時，請稍後再試。") from exc
    except requests.exceptions.RequestException as exc:
        raise CWAError(f"無法連線到 CWA API：{exc}") from exc

    if response.status_code == 401:
        raise CWAError("API 金鑰無效或已失效（HTTP 401），請確認金鑰設定。")
    if response.status_code != 200:
        raise CWAError(f"CWA API 回應異常，HTTP 狀態碼 {response.status_code}。")

    try:
        payload = response.json()
    except ValueError as exc:
        raise CWAError("CWA API 回應不是合法的 JSON 格式。") from exc

    # success 欄位在 API 中是字串 "true" / "false"
    if str(payload.get("success", "")).lower() not in ("true", "1"):
        raise CWAError("CWA API 回報查詢失敗，請確認金鑰與查詢條件。")

    return payload


def _locations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """取出回應中的縣市清單。

    F-C0032-001 使用 records.location；部分 CWA 資料集改用
    records.locations[].location，這裡兩種都支援。
    """
    records = payload.get("records")
    if not isinstance(records, dict):
        raise CWAError("CWA API 回應缺少 records 欄位。")

    if isinstance(records.get("location"), list):
        return records["location"]

    grouped = records.get("locations")
    if isinstance(grouped, list):
        locations: list[dict[str, Any]] = []
        for group in grouped:
            if isinstance(group, dict) and isinstance(group.get("location"), list):
                locations.extend(group["location"])
        if locations:
            return locations

    raise CWAError("CWA API 回應中找不到縣市預報資料。")


def _to_int(value: Any) -> Optional[int]:
    """把 API 的字串數值轉成 int，無法轉換（如「-」）則回傳 None。"""
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _short_time(timestamp: str) -> str:
    """"2026-10-06 18:00:00" -> "10/06 18:00"。格式不符時原樣回傳。"""
    try:
        date_part, time_part = timestamp.split(" ")
        _, month, day = date_part.split("-")
        hour, minute, *_ = time_part.split(":")
        return f"{month}/{day} {hour}:{minute}"
    except (AttributeError, ValueError):
        return str(timestamp)


def _parse_location(location: dict[str, Any]) -> list[ForecastPeriod]:
    """把單一縣市的 weatherElement 整理成依時間排序的 ForecastPeriod 清單。"""
    # 以 (開始時間, 結束時間) 為 key 把各天氣要素併成同一個時段
    periods: dict[tuple[str, str], dict[str, Any]] = {}
    for element in location.get("weatherElement", []):
        field = ELEMENT_FIELDS.get(element.get("elementName"))
        if field is None:
            continue

        for slot in element.get("time", []):
            key = (slot.get("startTime", ""), slot.get("endTime", ""))
            value = (slot.get("parameter") or {}).get("parameterName")
            periods.setdefault(key, {})[field] = value

    return [
        ForecastPeriod(
            start_time=start,
            end_time=end,
            weather=values.get("weather") or "無資料",
            min_temp=_to_int(values.get("min_temp")),
            max_temp=_to_int(values.get("max_temp")),
            pop=_to_int(values.get("pop")),
            comfort=values.get("comfort") or "無資料",
        )
        for (start, end), values in sorted(periods.items())
    ]


def parse_forecast(payload: dict[str, Any], city: str) -> list[ForecastPeriod]:
    """從原始 JSON 取出指定縣市的預報。"""
    target = normalize_city(city)
    location = next(
        (loc for loc in _locations(payload) if loc.get("locationName") == target),
        None,
    )
    if location is None:
        raise CWAError(f"CWA API 回應中沒有「{city}」的預報資料。")

    forecasts = _parse_location(location)
    if not forecasts:
        raise CWAError(f"「{city}」目前沒有可用的預報時段資料。")
    return forecasts


def parse_all_forecasts(payload: dict[str, Any]) -> dict[str, list[ForecastPeriod]]:
    """從原始 JSON 取出所有縣市的預報，回傳 {縣市名稱: 預報清單}。

    沒有時段資料的縣市會被略過，由 UI 層顯示「查無資料」。
    """
    all_forecasts = {}
    for location in _locations(payload):
        name = location.get("locationName")
        forecasts = _parse_location(location)
        if name and forecasts:
            all_forecasts[name] = forecasts

    if not all_forecasts:
        raise CWAError("CWA API 回應中沒有任何可用的預報資料。")
    return all_forecasts


def get_all_forecasts(api_key: str) -> dict[str, list[ForecastPeriod]]:
    """一次取得並解析全部縣市的預報（只呼叫一次 API）。"""
    return parse_all_forecasts(fetch_forecast(api_key))


def _average(values: list[Optional[int]]) -> Optional[float]:
    """忽略缺值後取平均（四捨五入到小數一位），全部缺值時回傳 None。"""
    valid = [v for v in values if v is not None]
    return round(sum(valid) / len(valid), 1) if valid else None


def regional_averages(
    all_forecasts: dict[str, list[ForecastPeriod]], period_index: int = 0
) -> list[dict[str, Any]]:
    """計算北、中、南、東四區在指定時段的平均氣溫與降雨機率。

    回傳每區一筆：region、cities（實際有資料的縣市）、avg_min、avg_max、avg_temp、avg_pop。
    """
    results = []
    for region, cities in REGIONS.items():
        periods = [
            all_forecasts[city][period_index]
            for city in cities
            if len(all_forecasts.get(city, [])) > period_index
        ]
        avg_min = _average([p.min_temp for p in periods])
        avg_max = _average([p.max_temp for p in periods])
        results.append(
            {
                "region": region,
                "cities": [city for city in cities if city in all_forecasts],
                "avg_min": avg_min,
                "avg_max": avg_max,
                # 平均溫度 = 平均最低溫與平均最高溫的中間值
                "avg_temp": None if avg_min is None or avg_max is None
                else round((avg_min + avg_max) / 2, 1),
                "avg_pop": _average([p.pop for p in periods]),
            }
        )
    return results


def get_city_forecast(api_key: str, city: str) -> list[ForecastPeriod]:
    """取得並解析單一縣市的預報。"""
    return parse_forecast(fetch_forecast(api_key, city), city)


def weather_kind(weather: str) -> str:
    """把 CWA 的天氣描述歸類，供 UI 選擇圖示與配色。

    回傳 thunder / rain / snow / fog / partly / sunny / cloudy 其中之一。
    """
    text = weather or ""
    if "雷" in text:
        return "thunder"
    if "雨" in text:
        return "rain"
    if "雪" in text:
        return "snow"
    if "霧" in text:
        return "fog"
    if "晴" in text and ("雲" in text or "陰" in text):
        return "partly"
    if "晴" in text:
        return "sunny"
    return "cloudy"


def describe_period(start_time: str, now: Optional[datetime] = None) -> str:
    """把時段開始時間轉成口語名稱，例如「今天白天」「今晚」「明天白天」。"""
    try:
        start = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return "預報時段"

    today = (now or datetime.now(TAIWAN_TZ)).date()
    day_offset = (start.date() - today).days
    day_names = {0: "今天", 1: "明天", 2: "後天"}
    day = day_names.get(day_offset, f"{start.month}/{start.day}")

    if start.hour >= 18:
        return {"今天": "今晚", "明天": "明晚"}.get(day, f"{day}晚上")
    if start.hour < 6:
        return f"{day}凌晨"
    return f"{day}白天"

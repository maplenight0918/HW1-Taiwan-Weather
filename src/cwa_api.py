"""中央氣象署（CWA）開放資料 API 的取得與解析邏輯。

資料集：F-C0032-001「一般天氣預報-今明 36 小時天氣預報」
文件：https://opendata.cwa.gov.tw/dist/opendata-swagger.html

本模組只負責「拿資料」與「整理資料」，不含任何 Streamlit UI 程式碼，
方便單獨測試與重複使用。
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any, Optional

import requests

API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"
REQUEST_TIMEOUT = 15  # 秒

# 22 個縣市（CWA 使用「臺」而非「台」）
CITIES = [
    "臺北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣",
    "苗栗縣", "臺中市", "彰化縣", "南投縣", "雲林縣", "嘉義市",
    "嘉義縣", "臺南市", "高雄市", "屏東縣", "宜蘭縣", "花蓮縣",
    "臺東縣", "澎湖縣", "金門縣", "連江縣",
]

# 用於 Streamlit 地圖的縣市政府所在地座標
CITY_COORDS = {
    "臺北市": (25.0330, 121.5654), "新北市": (25.0169, 121.4627),
    "基隆市": (25.1276, 121.7392), "桃園市": (24.9937, 121.3010),
    "新竹市": (24.8039, 120.9647), "新竹縣": (24.8387, 121.0177),
    "苗栗縣": (24.5602, 120.8214), "臺中市": (24.1477, 120.6736),
    "彰化縣": (24.0518, 120.5161), "南投縣": (23.9609, 120.9719),
    "雲林縣": (23.7092, 120.4313), "嘉義市": (23.4801, 120.4491),
    "嘉義縣": (23.4518, 120.2555), "臺南市": (22.9999, 120.2269),
    "高雄市": (22.6273, 120.3014), "屏東縣": (22.5519, 120.5487),
    "宜蘭縣": (24.7021, 121.7378), "花蓮縣": (23.9872, 121.6015),
    "臺東縣": (22.7583, 121.1444), "澎湖縣": (23.5655, 119.5663),
    "金門縣": (24.4321, 118.3171), "連江縣": (26.1608, 119.9496),
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


def fetch_forecast(api_key: str, city: str) -> dict[str, Any]:
    """向 CWA API 查詢指定縣市的 36 小時預報，回傳原始 JSON。"""
    if not api_key:
        raise CWAError("尚未設定 CWA API 金鑰。")

    params = {
        "Authorization": api_key,
        "locationName": normalize_city(city),
        "elementName": ",".join(ELEMENT_FIELDS),
    }

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


def parse_forecast(payload: dict[str, Any], city: str) -> list[ForecastPeriod]:
    """把原始 JSON 整理成依時間排序的 ForecastPeriod 清單。"""
    target = normalize_city(city)
    locations = _locations(payload)

    location = next(
        (loc for loc in locations if loc.get("locationName") == target),
        None,
    )
    if location is None:
        raise CWAError(f"CWA API 回應中沒有「{city}」的預報資料。")

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

    if not periods:
        raise CWAError(f"「{city}」目前沒有可用的預報時段資料。")

    forecasts = [
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
    return forecasts


def get_city_forecast(api_key: str, city: str) -> list[ForecastPeriod]:
    """取得並解析指定縣市的預報，是 UI 層唯一需要呼叫的函式。"""
    return parse_forecast(fetch_forecast(api_key, city), city)


def weather_icon(weather: str) -> str:
    """依天氣描述給一個對應的 emoji，讓畫面更好讀。"""
    text = weather or ""
    if "雷" in text:
        return "⛈️"
    if "雨" in text:
        return "🌧️"
    if "雪" in text:
        return "❄️"
    if "霧" in text:
        return "🌫️"
    if "晴" in text and "雲" in text:
        return "🌤️"
    if "晴" in text:
        return "☀️"
    if "陰" in text:
        return "☁️"
    if "雲" in text:
        return "⛅"
    return "🌡️"

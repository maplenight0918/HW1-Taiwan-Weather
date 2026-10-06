"""解析邏輯的基本測試，使用 tests/sample_response.json 當作假資料。

執行方式（兩種皆可）：
    python3 tests/test_cwa_api.py
    pytest
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cwa_api import (
    CITIES,
    REGIONS,
    CWAError,
    ForecastPeriod,
    normalize_city,
    parse_all_forecasts,
    parse_forecast,
    describe_period,
    regional_averages,
    weather_kind,
)

SAMPLE = json.loads((Path(__file__).parent / "sample_response.json").read_text("utf-8"))


def test_parse_forecast_returns_three_periods():
    forecasts = parse_forecast(SAMPLE, "臺中市")
    assert len(forecasts) == 3
    assert [f.start_time for f in forecasts] == sorted(f.start_time for f in forecasts)


def test_parse_forecast_fields():
    first = parse_forecast(SAMPLE, "臺中市")[0]
    assert first.weather == "晴時多雲"
    assert first.min_temp == 23
    assert first.max_temp == 29
    assert first.pop == 10
    assert first.comfort == "舒適至悶熱"
    assert first.period_label == "10/06 18:00 ~ 10/07 06:00"


def test_missing_numeric_value_becomes_none():
    # 第三個時段的 PoP 在假資料中是空白，應轉成 None 而不是讓程式崩潰
    third = parse_forecast(SAMPLE, "臺中市")[2]
    assert third.pop is None


def test_normalize_city_accepts_tai_variant():
    assert normalize_city("台中市") == "臺中市"
    assert parse_forecast(SAMPLE, "台中市")[0].weather == "晴時多雲"


def test_unknown_city_raises_cwa_error():
    try:
        parse_forecast(SAMPLE, "高雄市")
    except CWAError:
        pass
    else:
        raise AssertionError("查無縣市時應拋出 CWAError")


def test_parse_all_forecasts_groups_by_city():
    all_forecasts = parse_all_forecasts(SAMPLE)
    assert list(all_forecasts) == ["臺中市"]
    assert all_forecasts["臺中市"][0].max_temp == 29


def test_regions_cover_main_island_cities_once():
    assigned = [city for cities in REGIONS.values() for city in cities]
    assert len(assigned) == len(set(assigned))
    assert set(CITIES) - set(assigned) == {"金門縣", "連江縣"}


def _period(min_temp, max_temp, pop):
    return ForecastPeriod("2026-10-06 18:00:00", "2026-10-07 06:00:00", "晴", min_temp, max_temp, pop, "舒適")


def test_regional_averages_ignore_missing_values():
    all_forecasts = {
        "花蓮縣": [_period(24, 28, 10)],
        "臺東縣": [_period(26, None, None)],
    }
    east = next(r for r in regional_averages(all_forecasts) if r["region"] == "東部")
    assert east["avg_min"] == 25.0
    assert east["avg_max"] == 28.0  # 臺東縣缺最高溫，只用花蓮縣
    assert east["avg_temp"] == 26.5
    assert east["avg_pop"] == 10.0
    north = next(r for r in regional_averages(all_forecasts) if r["region"] == "北部")
    assert north["avg_temp"] is None  # 完全沒有資料


def test_weather_kind_mapping():
    assert weather_kind("多雲短暫陣雨") == "rain"
    assert weather_kind("多雲午後短暫雷陣雨") == "thunder"
    assert weather_kind("晴時多雲") == "partly"
    assert weather_kind("晴天") == "sunny"
    assert weather_kind("陰天") == "cloudy"


def test_describe_period_uses_relative_day_names():
    from datetime import datetime

    now = datetime(2026, 10, 6, 13, 0)
    assert describe_period("2026-10-06 12:00:00", now) == "今天白天"
    assert describe_period("2026-10-06 18:00:00", now) == "今晚"
    assert describe_period("2026-10-07 06:00:00", now) == "明天白天"
    assert describe_period("2026-10-07 18:00:00", now) == "明晚"
    assert describe_period("2026-10-07 00:00:00", now) == "明天凌晨"
    assert describe_period("壞掉的時間", now) == "預報時段"


def test_error_message_never_contains_api_key():
    import requests
    import src.cwa_api as api

    secret = "CWA-SECRET-KEY-SHOULD-NOT-LEAK"

    def failing_get(*args, **kwargs):
        # 模擬 requests 的錯誤訊息裡帶有完整網址與金鑰的情況
        raise requests.exceptions.SSLError(f"Max retries exceeded with url: /x?Authorization={secret}")

    original_get = api._session.get
    api._session.get = failing_get
    try:
        api.fetch_forecast(secret)
    except CWAError as error:
        assert secret not in str(error)
    else:
        raise AssertionError("應拋出 CWAError")
    finally:
        api._session.get = original_get


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS  {test.__name__}")
    print(f"\n{len(tests)} 個測試全部通過。")

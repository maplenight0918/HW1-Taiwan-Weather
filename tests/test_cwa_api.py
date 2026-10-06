"""解析邏輯的基本測試，使用 tests/sample_response.json 當作假資料。

執行方式（兩種皆可）：
    python3 tests/test_cwa_api.py
    pytest
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cwa_api import CWAError, normalize_city, parse_forecast, weather_icon

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


def test_weather_icon_mapping():
    assert weather_icon("多雲短暫陣雨") == "🌧️"
    assert weather_icon("晴時多雲") == "🌤️"
    assert weather_icon("陰天") == "☁️"


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS  {test.__name__}")
    print(f"\n{len(tests)} 個測試全部通過。")

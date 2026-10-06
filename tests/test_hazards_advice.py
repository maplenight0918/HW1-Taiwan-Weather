"""天氣特報解析與出門建議規則的測試。

執行方式（兩種皆可）：
    python3 tests/test_hazards_advice.py
    pytest
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.advice import build_advice
from src.cwa_api import ForecastPeriod, Hazard, parse_hazards

HAZARDS = json.loads((Path(__file__).parent / "sample_hazards.json").read_text("utf-8"))
NOW = datetime(2026, 10, 6, 13, 0)


def _period(start, min_temp, max_temp, pop, comfort="舒適"):
    return ForecastPeriod(start, "", "多雲", min_temp, max_temp, pop, comfort)


def _forecasts(lows=(24, 24, 24), highs=(27, 27, 27), pops=(10, 10, 10), comforts=("舒適",) * 3):
    starts = ["2026-10-06 12:00:00", "2026-10-06 18:00:00", "2026-10-07 06:00:00"]
    return [_period(*args) for args in zip(starts, lows, highs, pops, comforts)]


# ---- 天氣特報 ----

def test_parse_hazards_skips_cities_without_hazards():
    hazards = parse_hazards(HAZARDS, NOW)
    assert "臺北市" not in hazards
    assert [h.title for h in hazards["臺南市"]] == ["大雨特報", "陸上強風特報"]


def test_parse_hazards_drops_expired_and_puts_severe_first():
    pingtung = parse_hazards(HAZARDS, NOW)["屏東縣"]
    titles = [h.title for h in pingtung]
    assert "大雨特報" not in titles          # 10/05 已結束
    assert titles[0] == "颱風警報"           # 嚴重的排最前面
    assert pingtung[0].is_severe and not pingtung[1].is_severe


# ---- 出門建議 ----

def _kinds(advice):
    return [a.kind for a in advice]


def test_calm_weather_gives_single_ok_advice():
    advice = build_advice(_forecasts(), now=NOW)
    assert _kinds(advice) == ["ok"]


def test_rain_thresholds_and_wettest_period_named():
    likely = build_advice(_forecasts(pops=(10, 70, 20)), now=NOW)
    assert likely[0].title == "記得帶傘" and "今晚降雨機率 70%" in likely[0].detail
    possible = build_advice(_forecasts(pops=(30, 10, 10)), now=NOW)
    assert possible[0].title == "包包放把折傘"
    assert "umbrella" not in _kinds(build_advice(_forecasts(pops=(29, 0, 0)), now=NOW))


def test_cold_and_cool():
    assert build_advice(_forecasts(lows=(12, 9, 12), highs=(14, 12, 14)), now=NOW)[0].title == "天氣寒冷"
    assert build_advice(_forecasts(lows=(17, 15, 17), highs=(19, 18, 19)), now=NOW)[0].title == "帶件外套"


def test_heat_overrides_muggy():
    advice = build_advice(_forecasts(highs=(34, 28, 33), comforts=("悶熱",) * 3), now=NOW)
    assert "heat" in _kinds(advice) and "humid" not in _kinds(advice)
    muggy = build_advice(_forecasts(comforts=("舒適", "悶熱", "舒適")), now=NOW)
    assert muggy[0].kind == "humid" and muggy[0].detail.startswith("今晚")


def test_temperature_swing():
    advice = build_advice(_forecasts(lows=(22, 20, 22), highs=(28, 24, 29)), now=NOW)
    swing = next(a for a in advice if a.kind == "layers")
    assert "相差 9 度" in swing.detail


def test_hazards_come_first_with_matching_advice():
    hazards = [
        Hazard("陸上強風", "特報", "2026-10-06 16:50:00", "2026-10-07 23:00:00"),
        Hazard("颱風", "警報", "2026-10-06 11:30:00", "2026-10-08 00:00:00"),
    ]
    advice = build_advice(_forecasts(pops=(80, 80, 80)), hazards, now=NOW)
    assert _kinds(advice)[:3] == ["wind", "alert", "umbrella"]
    assert "（至 10/07 23:00）" in advice[0].detail
    assert "停班停課" in advice[1].detail


def test_missing_values_do_not_crash():
    advice = build_advice(_forecasts(lows=(None,) * 3, highs=(None,) * 3, pops=(None,) * 3), now=NOW)
    assert _kinds(advice) == ["ok"]


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS  {test.__name__}")
    print(f"\n{len(tests)} 個測試全部通過。")

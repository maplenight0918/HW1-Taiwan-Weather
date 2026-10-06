"""出門建議：把預報數字翻譯成口語的提醒。

規則都寫成門檻常數，方便調整；每條建議會說出「哪個時段、多少數值」，
讓使用者知道建議從何而來。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from .cwa_api import ForecastPeriod, Hazard, describe_period

RAIN_LIKELY = 50        # 降雨機率 ≥ 50%：帶傘
RAIN_POSSIBLE = 30      # 降雨機率 ≥ 30%：帶折傘備用
TEMP_SWING = 8          # 36 小時內最高與最低溫差 ≥ 8 度：洋蔥式穿搭
COOL = 15               # 低溫 ≤ 15°C：帶外套
COLD = 10               # 低溫 ≤ 10°C：注意保暖
HOT = 33                # 高溫 ≥ 33°C：防曬補水

MAX_ADVICE = 5

# 特報現象關鍵字 -> (建議類型, 說明)
HAZARD_ADVICE = [
    ("颱風", "alert", "留意颱風動態與停班停課公告，非必要不外出"),
    ("豪雨", "alert", "避免前往山區、河邊，留意積淹水"),
    ("大雨", "alert", "避免前往山區、河邊，留意積淹水"),
    ("強風", "wind", "騎車、行走留意強陣風，雨傘可能不好撐"),
    ("低溫", "cold", "注意保暖，長輩與心血管疾病患者尤其小心"),
    ("高溫", "heat", "減少中午外出，多補充水分"),
    ("濃霧", "alert", "開車放慢速度、開啟霧燈"),
]


@dataclass
class Advice:
    kind: str    # umbrella / layers / cold / heat / humid / wind / alert / ok，UI 依此選圖示
    title: str
    detail: str


def _short_end(end_time: str) -> str:
    """「2026-10-07 23:00:00」->「10/07 23:00」"""
    try:
        return f"{end_time[5:7]}/{end_time[8:10]} {end_time[11:16]}"
    except (TypeError, IndexError):
        return ""


def _hazard_advice(hazard: Hazard) -> Advice:
    kind, detail = "alert", "請留意中央氣象署最新發布的資訊"
    for keyword, matched_kind, matched_detail in HAZARD_ADVICE:
        if keyword in hazard.phenomena:
            kind, detail = matched_kind, matched_detail
            break
    if hazard.end_time:
        detail += f"（至 {_short_end(hazard.end_time)}）"
    return Advice(kind, hazard.title, detail)


def build_advice(
    forecasts: list[ForecastPeriod],
    hazards: Iterable[Hazard] = (),
    now: Optional[datetime] = None,
) -> list[Advice]:
    """依 36 小時預報與特報產生出門建議，依重要性排序。"""
    advice = [_hazard_advice(hazard) for hazard in hazards]

    def name(period: ForecastPeriod) -> str:
        return describe_period(period.start_time, now)

    # 降雨：找降雨機率最高的時段
    with_pop = [p for p in forecasts if p.pop is not None]
    if with_pop:
        wettest = max(with_pop, key=lambda p: p.pop)
        if wettest.pop >= RAIN_LIKELY:
            advice.append(Advice("umbrella", "記得帶傘", f"{name(wettest)}降雨機率 {wettest.pop}%"))
        elif wettest.pop >= RAIN_POSSIBLE:
            advice.append(Advice("umbrella", "包包放把折傘", f"{name(wettest)}降雨機率 {wettest.pop}%"))

    with_low = [p for p in forecasts if p.min_temp is not None]
    with_high = [p for p in forecasts if p.max_temp is not None]
    coldest = min(with_low, key=lambda p: p.min_temp) if with_low else None
    hottest = max(with_high, key=lambda p: p.max_temp) if with_high else None

    # 氣溫：先看冷熱，再看溫差
    if coldest and coldest.min_temp <= COLD:
        advice.append(Advice("cold", "天氣寒冷", f"{name(coldest)}低溫 {coldest.min_temp}°，穿厚外套注意保暖"))
    elif coldest and coldest.min_temp <= COOL:
        advice.append(Advice("cold", "帶件外套", f"{name(coldest)}低溫 {coldest.min_temp}°"))

    if hottest and hottest.max_temp >= HOT:
        advice.append(Advice("heat", "高溫炎熱", f"{name(hottest)}高溫 {hottest.max_temp}°，注意防曬、多補充水分"))
    elif any("悶熱" in (p.comfort or "") for p in forecasts):
        muggy = next(p for p in forecasts if "悶熱" in (p.comfort or ""))
        advice.append(Advice("humid", "天氣悶熱", f"{name(muggy)}體感悶熱，穿透氣的衣服"))

    if coldest and hottest:
        swing = hottest.max_temp - coldest.min_temp
        if swing >= TEMP_SWING:
            advice.append(Advice(
                "layers", "早晚溫差大",
                f"未來 36 小時從 {coldest.min_temp}° 到 {hottest.max_temp}°，相差 {swing} 度，建議洋蔥式穿搭",
            ))

    if not advice:
        advice.append(Advice("ok", "天氣穩定，適合出門", "未來 36 小時沒有明顯降雨，氣溫也很舒適"))

    return advice[:MAX_ADVICE]

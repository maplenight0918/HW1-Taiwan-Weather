"""網頁外觀：CSS、天氣圖示與自訂 HTML 區塊。

app.py 負責「放什麼」，這個檔案負責「長什麼樣子」。
所有來自 API 的文字都先經過 html.escape，避免破壞版面。
"""

from html import escape
from typing import Optional

from .advice import Advice
from .cwa_api import ForecastPeriod, Hazard, describe_period, weather_kind

# 顏色集中在這裡，圖表與地圖也共用同一組
INK = "#17202A"
MUTED = "#5F6B7A"
LINE = "#E3E7EC"
ACCENT = "#2F6FDE"
WARM = "#E07B39"

# 地圖與區域溫度條的配色：15°C 藍 → 35°C 紅
TEMP_SCALE_DOMAIN = [15, 20, 25, 30, 35]
TEMP_SCALE_RANGE = ["#3B7DD8", "#A9CBE8", "#F3DFB6", "#EE9A5B", "#D2493A"]

# 線條圖示（改繪自 Feather / Lucide，MIT / ISC 授權）
_ICON_PATHS = {
    "sunny": '<circle cx="12" cy="12" r="4.5"/><path d="M12 1.5v2.5M12 20v2.5M4.6 4.6l1.8 1.8M17.6 17.6l1.8 1.8M1.5 12H4M20 12h2.5M4.6 19.4l1.8-1.8M17.6 6.4l1.8-1.8"/>',
    "partly": '<path d="M8 2.5v1.8M3.1 4.6l1.3 1.3M1.5 9.5h1.8M12.9 4.6l-1.3 1.3"/><path d="M11.7 9.2A4 4 0 0 0 4.6 11.4"/><path d="M17.5 21H8a4.5 4.5 0 1 1 1.3-8.8A5.5 5.5 0 0 1 19.8 13 4 4 0 0 1 17.5 21z"/>',
    "cloudy": '<path d="M17.5 19H8a5 5 0 1 1 1.4-9.8A6 6 0 0 1 20.8 11 4 4 0 0 1 17.5 19z"/>',
    "rain": '<path d="M17.5 15H8a5 5 0 1 1 1.4-9.8A6 6 0 0 1 20.8 7 4 4 0 0 1 17.5 15z"/><path d="M8 18l-1 3M12.5 18l-1 3M17 18l-1 3"/>',
    "thunder": '<path d="M17.5 15H8a5 5 0 1 1 1.4-9.8A6 6 0 0 1 20.8 7 4 4 0 0 1 17.5 15z"/><path d="M13 15l-2.5 4h4L12 23"/>',
    "fog": '<path d="M17.5 13H8a5 5 0 1 1 1.4-9.8A6 6 0 0 1 20.8 5 4 4 0 0 1 17.5 13z"/><path d="M4 17h16M7 21h10"/>',
    "snow": '<path d="M17.5 15H8a5 5 0 1 1 1.4-9.8A6 6 0 0 1 20.8 7 4 4 0 0 1 17.5 15z"/><path d="M8 19h.01M12 19h.01M16 19h.01M10 22h.01M14 22h.01"/>',
}
# 出門建議的圖示與顏色
_ADVICE_ICONS = {
    "umbrella": ('<path d="M22 12a10 10 0 0 0-20 0z"/><path d="M12 12v7a2.5 2.5 0 0 1-5 0"/>', "#2F6FDE"),
    "layers": ('<path d="M20.4 3.5 16 2a4 4 0 0 1-8 0L3.6 3.5a2 2 0 0 0-1.3 2.2l.6 3.5a1 1 0 0 0 1 .8H6v10a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V10h2.1a1 1 0 0 0 1-.8l.6-3.5a2 2 0 0 0-1.3-2.2z"/>', "#7A5AF8"),
    "cold": ('<path d="M14 14.8V3.5a2.5 2.5 0 0 0-5 0v11.3a4.5 4.5 0 1 0 5 0z"/>', "#3B7DD8"),
    "heat": (_ICON_PATHS["sunny"], "#E07B39"),
    "humid": ('<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/><path d="M9.5 14.5a2.5 2.5 0 0 0 2.5 2.5"/>', "#D98A2B"),
    "wind": ('<path d="M9.6 4.6A2 2 0 1 1 11 8H2M12.6 19.4A2 2 0 1 0 14 16H2M17.7 7.7A2.5 2.5 0 1 1 19.5 12H2"/>', "#0E8A7E"),
    "alert": ('<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>', "#C2410C"),
    "ok": ('<circle cx="12" cy="12" r="9.5"/><path d="m8 12.5 2.7 2.7L16.5 9.5"/>', "#2E9E5B"),
}

_RAIN_DROP = '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>'

# 不同天氣的主卡片底色與圖示顏色
_KIND_COLORS = {
    "sunny": ("#FFF3E2", "#E08A1E"),
    "partly": ("#FFF6EA", "#D98A2B"),
    "cloudy": ("#EDF1F5", "#6B7A8C"),
    "rain": ("#E5EDF8", "#2F6FDE"),
    "thunder": ("#ECE9F5", "#5B4FB3"),
    "fog": ("#EFF0F2", "#7A8491"),
    "snow": ("#EDF4FA", "#5E9CD3"),
}

CSS = f"""
<style>
[data-testid="stHeader"] {{ background: transparent; }}
.block-container, [data-testid="stMainBlockContainer"] {{
    max-width: 1180px; padding-top: 2.2rem; padding-bottom: 3rem;
}}
.brand {{ display: flex; flex-direction: column; gap: 2px; }}
.brand-title {{ font-size: 1.55rem; font-weight: 700; color: {INK}; letter-spacing: .02em; }}
.brand-sub {{ font-size: .86rem; color: {MUTED}; }}

.section-title {{ display: flex; align-items: baseline; gap: .75rem; margin: 2.2rem 0 .8rem; }}
.section-title h3 {{ font-size: 1.12rem; font-weight: 700; margin: 0; padding: 0; color: {INK}; }}
.section-title span {{ font-size: .84rem; color: {MUTED}; }}

.hero {{
    display: grid; grid-template-columns: 1fr auto; gap: 1.5rem; align-items: center;
    padding: 1.9rem 2.2rem; border: 1px solid {LINE}; border-radius: 20px;
    background: linear-gradient(120deg, var(--tint) 0%, #FFFFFF 78%);
}}
.hero-place {{ font-size: 1.05rem; font-weight: 700; color: {INK}; }}
.hero-period {{ font-size: .86rem; color: {MUTED}; margin-top: .15rem; }}
.hero-temps {{ display: flex; gap: 2.2rem; margin: 1.1rem 0 .5rem; }}
.hero-temps .lbl {{ display: block; font-size: .78rem; color: {MUTED}; margin-bottom: .1rem; }}
.hero-temps .num {{ font-size: 3.4rem; font-weight: 500; line-height: 1; color: {INK};
    font-variant-numeric: tabular-nums; letter-spacing: -.02em; }}
.hero-cond {{ font-size: 1.15rem; font-weight: 500; color: {INK}; }}
.hero-side {{ display: flex; flex-direction: column; align-items: flex-end; gap: 1rem; }}
.hero-stats {{ display: flex; gap: 1.6rem; margin: 0; }}
.hero-stats div {{ text-align: right; }}
.hero-stats dt {{ font-size: .78rem; color: {MUTED}; }}
.hero-stats dd {{ margin: 0; font-size: 1.05rem; font-weight: 500; color: {INK}; }}

.fc-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: .9rem; }}
.fc-card {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 16px; padding: 1.1rem 1.25rem; }}
.fc-card.is-now {{ border-color: {ACCENT}; box-shadow: inset 0 3px 0 {ACCENT}; }}
.fc-head {{ display: flex; justify-content: space-between; align-items: flex-start; }}
.fc-name {{ font-weight: 700; color: {INK}; }}
.fc-time {{ font-size: .78rem; color: {MUTED}; margin-top: .1rem; }}
.fc-cond {{ margin: .85rem 0 .35rem; color: {INK}; font-size: .95rem; min-height: 1.4em; }}
.fc-foot {{ display: flex; justify-content: space-between; align-items: baseline; }}
.fc-temp {{ font-variant-numeric: tabular-nums; }}
.fc-temp b {{ font-size: 1.45rem; font-weight: 500; color: {INK}; }}
.fc-temp span {{ font-size: 1.05rem; color: {MUTED}; margin-left: .35rem; }}
.fc-rain {{ display: flex; align-items: center; gap: .25rem; font-size: .88rem; color: {ACCENT}; }}

.range-track {{ position: relative; height: 6px; border-radius: 3px; background: #EEF1F4; margin: .55rem 0 .35rem; }}
.range-fill {{ position: absolute; top: 0; height: 6px; border-radius: 3px; }}
.range-text {{ display: flex; justify-content: space-between; font-size: .78rem; color: {MUTED};
    font-variant-numeric: tabular-nums; }}
.region-cities {{ font-size: .78rem; color: {MUTED}; margin: .5rem 0 .35rem; line-height: 1.5; }}

[data-testid="stMetricLabel"] p {{ font-size: .9rem; font-weight: 700; color: {INK}; }}
[data-testid="stMetricValue"] {{ font-size: 1.9rem; font-weight: 500; font-variant-numeric: tabular-nums; }}

.alert-banner {{ display: flex; gap: .9rem; align-items: flex-start; padding: .95rem 1.2rem;
    border-radius: 14px; border: 1px solid #F3C98B; background: #FFF6E8; color: #7A3E06; margin-bottom: 1rem; }}
.alert-banner.is-severe {{ border-color: #F4B4AE; background: #FEF0EF; color: #8E1F14; }}
.alert-banner svg {{ flex-shrink: 0; margin-top: .1rem; }}
.alert-title {{ font-weight: 700; }}
.alert-items {{ display: flex; flex-wrap: wrap; gap: .4rem .5rem; margin-top: .4rem; }}
.alert-chip {{ font-size: .82rem; padding: .12rem .6rem; border-radius: 999px; background: rgba(255,255,255,.75);
    border: 1px solid currentColor; }}
.alert-note {{ font-size: .84rem; color: {MUTED}; margin: -.2rem 0 1rem; }}

.advice-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: .75rem; }}
.advice-item {{ display: flex; gap: .85rem; align-items: flex-start; background: #FFFFFF;
    border: 1px solid {LINE}; border-radius: 14px; padding: .9rem 1.1rem; }}
.advice-icon {{ flex-shrink: 0; width: 38px; height: 38px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center; }}
.advice-title {{ font-weight: 700; color: {INK}; }}
.advice-detail {{ font-size: .86rem; color: {MUTED}; margin-top: .15rem; line-height: 1.55; }}

.footnote {{ margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid {LINE};
    font-size: .8rem; color: {MUTED}; }}
.footnote a {{ color: {MUTED}; }}

@media (max-width: 720px) {{
    .hero {{ grid-template-columns: 1fr; padding: 1.4rem; }}
    .hero-side {{ align-items: flex-start; }}
    .hero-side svg {{ width: 60px; height: 60px; }}
    .hero-stats div {{ text-align: left; }}
    .hero-temps .num {{ font-size: 2.6rem; }}
    .fc-grid {{ grid-template-columns: 1fr; }}
}}
</style>
"""


def _compact(markup: str) -> str:
    """移除每行開頭空白，避免 Markdown 把縮排的 HTML 當成程式碼區塊。"""
    return "".join(line.strip() for line in markup.splitlines())


def icon(kind: str, size: int = 28, color: str = INK) -> str:
    return icon_path(_ICON_PATHS.get(kind, _ICON_PATHS["cloudy"]), size, color)


def icon_path(paths: str, size: int = 28, color: str = INK) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.6" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{paths}</svg>'
    )


def _temp(value: Optional[int]) -> str:
    return "–" if value is None else f"{value}°"


def time_range(period: ForecastPeriod) -> str:
    """同一天只寫一次日期：「10/06 12:00–18:00」；跨日則完整顯示兩端。"""
    start, end = period.period_label.split(" ~ ")
    if start[:5] == end[:5]:
        return f"{start}–{end[6:]}"
    return f"{start} – {end}"


def section_title(title: str, subtitle: str = "") -> str:
    sub = f"<span>{escape(subtitle)}</span>" if subtitle else ""
    return f'<div class="section-title"><h3>{escape(title)}</h3>{sub}</div>'


def brand_html() -> str:
    return _compact("""
        <div class="brand">
            <div class="brand-title">台灣天氣預報</div>
            <div class="brand-sub">中央氣象署 今明 36 小時預報 · 全台 22 縣市</div>
        </div>
    """)


def hero_html(city: str, period: ForecastPeriod) -> str:
    """頁面最上方的主卡片：所選縣市目前時段的天氣。"""
    kind = weather_kind(period.weather)
    tint, icon_color = _KIND_COLORS[kind]
    pop = "–" if period.pop is None else f"{period.pop}%"
    return _compact(f"""
        <div class="hero" style="--tint:{tint}">
            <div>
                <div class="hero-place">{escape(city)}</div>
                <div class="hero-period">{describe_period(period.start_time)} · {time_range(period)}</div>
                <div class="hero-temps">
                    <div><span class="lbl">最低溫 °C</span><span class="num">{_temp(period.min_temp)}</span></div>
                    <div><span class="lbl">最高溫 °C</span><span class="num">{_temp(period.max_temp)}</span></div>
                </div>
                <div class="hero-cond">{escape(period.weather)}</div>
            </div>
            <div class="hero-side">
                {icon(kind, 92, icon_color)}
                <dl class="hero-stats">
                    <div><dt>降雨機率</dt><dd>{pop}</dd></div>
                    <div><dt>體感</dt><dd>{escape(period.comfort)}</dd></div>
                </dl>
            </div>
        </div>
    """)


def forecast_cards_html(forecasts: list[ForecastPeriod]) -> str:
    """三個時段並排的預報卡片，第一張標示為目前時段。"""
    cards = []
    for index, period in enumerate(forecasts):
        kind = weather_kind(period.weather)
        pop = "–" if period.pop is None else f"{period.pop}%"
        cards.append(f"""
            <div class="fc-card{' is-now' if index == 0 else ''}">
                <div class="fc-head">
                    <div>
                        <div class="fc-name">{describe_period(period.start_time)}</div>
                        <div class="fc-time">{time_range(period)}</div>
                    </div>
                    {icon(kind, 30, _KIND_COLORS[kind][1])}
                </div>
                <div class="fc-cond">{escape(period.weather)}</div>
                <div class="fc-foot">
                    <div class="fc-temp"><b>{_temp(period.max_temp)}</b><span>{_temp(period.min_temp)}</span></div>
                    <div class="fc-rain"><svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                        stroke="{ACCENT}" stroke-width="2">{_RAIN_DROP}</svg>{pop}</div>
                </div>
            </div>
        """)
    return _compact(f'<div class="fc-grid">{"".join(cards)}</div>')


def temp_color(value: float) -> str:
    """依 TEMP_SCALE_DOMAIN / TEMP_SCALE_RANGE 線性內插出溫度對應的顏色。"""
    stops = list(zip(TEMP_SCALE_DOMAIN, TEMP_SCALE_RANGE))
    value = min(max(value, stops[0][0]), stops[-1][0])
    for (t1, c1), (t2, c2) in zip(stops, stops[1:]):
        if value <= t2:
            ratio = (value - t1) / (t2 - t1)
            rgb = [
                round(int(c1[i:i + 2], 16) + (int(c2[i:i + 2], 16) - int(c1[i:i + 2], 16)) * ratio)
                for i in (1, 3, 5)
            ]
            return "#{:02X}{:02X}{:02X}".format(*rgb)
    return stops[-1][1]


def range_bar_html(low: Optional[float], high: Optional[float]) -> str:
    """區域卡片下方的溫度區間條，刻度固定 15–35°C，方便各區互相比較。"""
    if low is None or high is None:
        return ""
    scale_min, scale_max = TEMP_SCALE_DOMAIN[0], TEMP_SCALE_DOMAIN[-1]

    def position(value: float) -> float:
        clamped = min(max(value, scale_min), scale_max)
        return (clamped - scale_min) / (scale_max - scale_min) * 100

    left = position(low)
    width = max(position(high) - left, 2)
    return _compact(f"""
        <div class="range-track">
            <div class="range-fill" style="left:{left:.1f}%; width:{width:.1f}%;
                background:linear-gradient(90deg, {temp_color(low)}, {temp_color(high)});"></div>
        </div>
        <div class="range-text"><span>低 {low}°</span><span>高 {high}°</span></div>
    """)


def hazard_banner_html(city: str, city_hazards: list[Hazard], all_hazards: dict) -> str:
    """頁面上方的特報提示。所選縣市有特報時顯示醒目橫幅，否則只顯示一行全台概況。"""
    if city_hazards:
        severe = any(h.is_severe for h in city_hazards)
        color = "#B42318" if severe else "#B45309"
        chips = "".join(
            f'<span class="alert-chip">{escape(h.title)}・至 {escape(h.end_time[5:16].replace("-", "/"))}</span>'
            for h in city_hazards
        )
        return _compact(f"""
            <div class="alert-banner{' is-severe' if severe else ''}">
                {icon_path(_ADVICE_ICONS["alert"][0], 22, color)}
                <div>
                    <div class="alert-title">{escape(city)}目前有 {len(city_hazards)} 則天氣特報</div>
                    <div class="alert-items">{chips}</div>
                </div>
            </div>
        """)
    if all_hazards:
        kinds = sorted({h.title for hazards in all_hazards.values() for h in hazards})
        return (
            f'<div class="alert-note">{escape(city)}目前沒有天氣特報。全台另有 {len(all_hazards)} 個縣市發布'
            f'{escape("、".join(kinds))}，地圖上以虛線框標示。</div>'
        )
    return ""


def advice_html(advice: list[Advice]) -> str:
    """出門建議：每則一張小卡，左邊是圖示，右邊是標題與原因。"""
    items = []
    for item in advice:
        paths, color = _ADVICE_ICONS.get(item.kind, _ADVICE_ICONS["ok"])
        items.append(f"""
            <div class="advice-item">
                <div class="advice-icon" style="background:{color}14">{icon_path(paths, 22, color)}</div>
                <div>
                    <div class="advice-title">{escape(item.title)}</div>
                    <div class="advice-detail">{escape(item.detail)}</div>
                </div>
            </div>
        """)
    return _compact(f'<div class="advice-grid">{"".join(items)}</div>')


def region_detail_html(pop_text: str) -> str:
    """區域卡片底部的小字：平均降雨機率。"""
    return f'<div class="region-cities">平均降雨機率 {escape(pop_text)}</div>'


def footnote_html(updated_at: str) -> str:
    return _compact(f"""
        <div class="footnote">
            資料來源：<a href="https://opendata.cwa.gov.tw/" target="_blank">交通部中央氣象署 氣象開放資料平臺</a>
            （F-C0032-001 預報、W-C0033-001 天氣特報）· 資料每 10 分鐘更新 · 本頁取得時間 {escape(updated_at)}
        </div>
    """)

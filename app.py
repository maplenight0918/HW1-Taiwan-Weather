"""HW1：使用 CWA 開放資料的台灣天氣預報網站（Streamlit 介面）。

執行方式：
    streamlit run app.py
"""

from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

from src import ui
from src.cwa_api import (
    CITIES,
    CITY_COORDS,
    REGIONS,
    TAIWAN_TZ,
    CWAError,
    describe_period,
    get_all_forecasts,
    get_api_key,
    regional_averages,
)

DEFAULT_CITY = "臺中市"
CACHE_TTL_SECONDS = 600  # 預報每 10 分鐘才重新向 API 查詢一次

# 台灣縣市邊界（TopoJSON，來源：npm 套件 taiwan-atlas）
TAIWAN_TOPOJSON_URL = "https://cdn.jsdelivr.net/npm/taiwan-atlas@1/counties-10t.json"

st.set_page_config(page_title="台灣天氣預報", page_icon="🌦️", layout="wide")


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_all_forecasts(api_key: str):
    """一次取得全部縣市的預報並快取，切換縣市時不必重新呼叫 API。"""
    fetched_at = datetime.now(TAIWAN_TZ).strftime("%m/%d %H:%M")
    return get_all_forecasts(api_key), fetched_at


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def style_chart(chart: alt.TopLevelMixin) -> alt.TopLevelMixin:
    """讓 Altair 圖表的字型、格線與整頁設計一致。"""
    return (
        chart.configure(font="Noto Sans TC", background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(
            labelColor=ui.MUTED,
            titleColor=ui.MUTED,
            labelFontSize=12,
            titleFontWeight="normal",
            gridColor="#EEF1F4",
            domain=False,
            ticks=False,
        )
        .configure_legend(labelColor=ui.MUTED, titleColor=ui.MUTED, titleFontWeight="normal")
    )


def show_api_key_help() -> None:
    """金鑰未設定時顯示設定說明。"""
    st.error("找不到 CWA API 金鑰，請先完成設定後重新整理頁面。")
    st.markdown(
        """
        **設定方式（任選一種）**

        1. 環境變數：`export CWA_API_KEY="你的金鑰"`
        2. 專案根目錄的 `.env` 檔：`CWA_API_KEY=你的金鑰`
        3. Streamlit secrets（`.streamlit/secrets.toml`）：`CWA_API_KEY = "你的金鑰"`

        金鑰可在 [CWA 氣象開放資料平臺](https://opendata.cwa.gov.tw/user/authkey) 註冊後免費取得。
        """
    )


def render_header():
    """頁首：左邊是網站名稱，右邊是縣市選單與重新整理按鈕。回傳選擇的縣市。"""
    brand_col, select_col, button_col = st.columns([3, 1.3, 0.55], vertical_alignment="bottom")
    with brand_col:
        html(ui.brand_html())
    with select_col:
        city = st.selectbox(
            "縣市", CITIES, index=CITIES.index(DEFAULT_CITY), label_visibility="collapsed"
        )
    with button_col:
        if st.button("重新整理", width="stretch", help="清除快取並重新向 CWA 取得資料"):
            load_all_forecasts.clear()
    return city


def render_charts(forecasts) -> None:
    """氣溫以「最低溫 ~ 最高溫」浮動長條呈現，降雨機率以 0–100% 長條呈現。"""
    chart_data = pd.DataFrame(
        {
            "period": [describe_period(p.start_time) for p in forecasts],
            "time_range": [ui.time_range(p) for p in forecasts],
            "min_temp": [p.min_temp for p in forecasts],
            "max_temp": [p.max_temp for p in forecasts],
            "pop": [p.pop for p in forecasts],
        }
    )
    # X 軸用「今天白天、今晚…」這類短名稱；sort=None 保留時間順序
    x_axis = alt.X("period:N", sort=None, title=None, axis=alt.Axis(labelAngle=0, labelFontSize=13))
    bar_style = dict(size=34, cornerRadiusTopLeft=5, cornerRadiusTopRight=5)

    temp_col, pop_col = st.columns(2, gap="large")

    with temp_col:
        st.caption("氣溫區間（°C）")
        temps = chart_data.dropna(subset=["min_temp", "max_temp"])
        base = alt.Chart(temps).encode(x=x_axis)
        bars = base.mark_bar(size=34, cornerRadius=5, color=ui.WARM, opacity=0.9).encode(
            y=alt.Y("min_temp:Q", title=None, scale=alt.Scale(zero=False, padding=14)),
            y2="max_temp:Q",
            tooltip=[
                alt.Tooltip("time_range:N", title="時段"),
                alt.Tooltip("min_temp:Q", title="最低溫"),
                alt.Tooltip("max_temp:Q", title="最高溫"),
            ],
        )
        low = base.mark_text(dy=13, color=ui.MUTED).encode(y="min_temp:Q", text="min_temp:Q")
        high = base.mark_text(dy=-9, color=ui.INK, fontWeight="bold").encode(
            y="max_temp:Q", text="max_temp:Q"
        )
        st.altair_chart(
            style_chart((bars + low + high).properties(height=260)), theme=None, use_container_width=True
        )

    with pop_col:
        st.caption("降雨機率（%）")
        pop = chart_data.dropna(subset=["pop"])
        base = alt.Chart(pop).encode(x=x_axis)
        bars = base.mark_bar(**bar_style, color=ui.ACCENT, opacity=0.85).encode(
            y=alt.Y("pop:Q", title=None, scale=alt.Scale(domain=[0, 100])),
            tooltip=[
                alt.Tooltip("time_range:N", title="時段"),
                alt.Tooltip("pop:Q", title="降雨機率 (%)"),
            ],
        )
        labels = base.mark_text(dy=-9, color=ui.INK, fontWeight="bold").encode(
            y="pop:Q", text="pop:Q"
        )
        st.altair_chart(
            style_chart((bars + labels).properties(height=260)), theme=None, use_container_width=True
        )


def render_forecast_table(forecasts) -> None:
    """完整數字表格，放在可展開區塊裡，需要時再看。"""
    with st.expander("查看完整預報表格"):
        table = pd.DataFrame([period.as_row() for period in forecasts])
        st.dataframe(table, width="stretch", hide_index=True)


def build_map_data(all_forecasts) -> pd.DataFrame:
    """整理每個縣市「最近時段」的預報，作為地圖的資料。"""
    rows = []
    for city, forecasts in all_forecasts.items():
        if city not in CITY_COORDS or not forecasts:
            continue
        period = forecasts[0]
        latitude, longitude = CITY_COORDS[city]
        low = "-" if period.min_temp is None else period.min_temp
        high = "-" if period.max_temp is None else period.max_temp
        rows.append(
            {
                "city": city,
                "lat": latitude,
                "lon": longitude,
                "max_temp": period.max_temp,
                "label": f"{low}~{high}°",
                "weather": period.weather,
                "pop": "-" if period.pop is None else period.pop,
            }
        )
    return pd.DataFrame(rows)


def render_map(all_forecasts, selected_city: str) -> None:
    """全台縣市地圖：區塊顏色代表最高溫，標籤為「最低~最高」溫度。"""
    map_data = build_map_data(all_forecasts)
    if map_data.empty:
        return

    tooltip = [
        alt.Tooltip("city:N", title="縣市"),
        alt.Tooltip("weather:N", title="天氣"),
        alt.Tooltip("label:N", title="氣溫"),
        alt.Tooltip("pop:N", title="降雨機率 (%)"),
    ]
    counties = (
        alt.Chart(alt.topo_feature(TAIWAN_TOPOJSON_URL, "counties"))
        # 邊界檔使用「台」，CWA 使用「臺」，統一後才能對應
        .transform_calculate(city="replace(datum.properties.COUNTYNAME, '台', '臺')")
        .transform_lookup(
            lookup="city",
            from_=alt.LookupData(map_data, "city", ["max_temp", "label", "weather", "pop"]),
        )
    )
    fill = counties.mark_geoshape(stroke="white", strokeWidth=1).encode(
        color=alt.Color(
            "max_temp:Q",
            title="最高溫 °C",
            scale=alt.Scale(domain=ui.TEMP_SCALE_DOMAIN, range=ui.TEMP_SCALE_RANGE, clamp=True),
            legend=alt.Legend(orient="bottom-left", direction="horizontal", gradientLength=140),
        ),
        tooltip=tooltip,
    )
    highlight = counties.transform_filter(alt.datum.city == selected_city).mark_geoshape(
        fill=None, stroke=ui.INK, strokeWidth=2.2
    )

    points = alt.Chart(map_data).encode(longitude="lon:Q", latitude="lat:Q", tooltip=tooltip)
    dots = points.mark_circle(size=16, color=ui.INK, opacity=0.75)
    halo = points.mark_text(
        dy=-10, fontSize=11, fontWeight="bold", stroke="white", strokeWidth=3, strokeOpacity=0.9
    ).encode(text="label:N")
    labels = points.mark_text(dy=-10, fontSize=11, fontWeight="bold", color=ui.INK).encode(
        text="label:N"
    )

    chart = alt.layer(fill, highlight, dots, halo, labels).project(type="mercator").properties(
        height=640
    )
    st.altair_chart(style_chart(chart), theme=None, use_container_width=True)


def render_regions(all_forecasts) -> None:
    """北、中、南、東四區的平均溫度，2×2 排列。"""
    regions = regional_averages(all_forecasts)
    for row in (regions[:2], regions[2:]):
        for column, region in zip(st.columns(2), row):
            with column, st.container(border=True):
                if region["avg_temp"] is None:
                    st.metric(region["region"], "無資料")
                    continue
                pop = "–" if region["avg_pop"] is None else f"{region['avg_pop']:.0f}%"
                st.metric(
                    region["region"],
                    f"{region['avg_temp']}°C",
                    help="包含：" + "、".join(REGIONS[region["region"]]),
                )
                html(ui.range_bar_html(region["avg_min"], region["avg_max"]))
                html(ui.region_detail_html(pop))


def main() -> None:
    html(ui.CSS)
    city = render_header()

    api_key = get_api_key()
    if not api_key:
        show_api_key_help()
        return

    try:
        with st.spinner("正在取得全台天氣預報…"):
            all_forecasts, fetched_at = load_all_forecasts(api_key)
    except CWAError as error:
        st.error(f"取得預報失敗：{error}")
        st.caption("請確認網路連線與 API 金鑰是否正確，或稍後按「重新整理」再試一次。")
        return

    forecasts = all_forecasts.get(city)
    if not forecasts:
        st.warning(f"目前查不到「{city}」的預報資料。")
    else:
        st.write("")
        html(ui.hero_html(city, forecasts[0]))
        html(ui.section_title("未來 36 小時", "每 12 小時一個時段"))
        html(ui.forecast_cards_html(forecasts))
        html(ui.section_title("氣溫與降雨趨勢"))
        render_charts(forecasts)
        render_forecast_table(forecasts)

    first_period = next(iter(all_forecasts.values()))[0]
    html(ui.section_title("全台概況", f"{ui.time_range(first_period)} · 顏色代表最高溫，黑框為目前選擇的縣市"))
    map_col, region_col = st.columns([1.35, 1], gap="large")
    with map_col:
        render_map(all_forecasts, city)
    with region_col:
        st.caption("各區域平均溫度（金門、連江為離島，不列入）")
        render_regions(all_forecasts)

    html(ui.footnote_html(fetched_at))


if __name__ == "__main__":
    main()

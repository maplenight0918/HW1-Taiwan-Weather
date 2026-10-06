"""HW1：使用 CWA 開放資料的台灣天氣預報網站（Streamlit 介面）。

執行方式：
    streamlit run app.py
"""

import altair as alt
import pandas as pd
import streamlit as st

from src.cwa_api import (
    CITIES,
    CITY_COORDS,
    CWAError,
    get_all_forecasts,
    get_api_key,
    weather_icon,
)

DEFAULT_CITY = "臺中市"
CACHE_TTL_SECONDS = 600  # 預報每 10 分鐘才重新向 API 查詢一次

# 台灣縣市邊界（TopoJSON，來源：npm 套件 taiwan-atlas）
TAIWAN_TOPOJSON_URL = "https://cdn.jsdelivr.net/npm/taiwan-atlas@1/counties-10t.json"
# 地圖顏色固定在 15–35°C，不同天之間的顏色才能互相比較
MAP_TEMP_RANGE = [15, 35]

st.set_page_config(page_title="台灣天氣預報", page_icon="🌦️", layout="wide")


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_all_forecasts(api_key: str):
    """一次取得全部縣市的預報並快取，切換縣市時不必重新呼叫 API。"""
    return get_all_forecasts(api_key)


def show_api_key_help() -> None:
    """金鑰未設定時顯示設定說明。"""
    st.error("找不到 CWA API 金鑰，請先完成設定後重新整理頁面。")
    st.markdown(
        """
        **設定方式（任選一種）**

        1. 環境變數：
           ```bash
           export CWA_API_KEY="你的金鑰"
           ```
        2. 專案根目錄的 `.env` 檔：
           ```
           CWA_API_KEY=你的金鑰
           ```
        3. Streamlit secrets（`.streamlit/secrets.toml`）：
           ```toml
           CWA_API_KEY = "你的金鑰"
           ```

        金鑰可在 [CWA 氣象開放資料平臺](https://opendata.cwa.gov.tw/user/authkey)
        註冊後免費取得。
        """
    )


def format_temp(value) -> str:
    return "無資料" if value is None else f"{value} °C"


def render_current_weather(period) -> None:
    """用 metric 卡片顯示最近一個時段的預報。"""
    st.subheader(f"{weather_icon(period.weather)} 最近時段預報")
    st.caption(f"預報時段：{period.period_label}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("天氣狀況", period.weather)
    col2.metric("最低溫", format_temp(period.min_temp))
    col3.metric("最高溫", format_temp(period.max_temp))
    col4.metric("降雨機率", "無資料" if period.pop is None else f"{period.pop} %")

    if period.comfort and period.comfort != "無資料":
        st.info(f"體感舒適度：{period.comfort}")


def render_forecast_table(forecasts) -> None:
    """以表格呈現全部三個預報時段。"""
    table = pd.DataFrame([period.as_row() for period in forecasts])
    st.subheader("📋 36 小時預報明細")
    st.dataframe(table, width="stretch", hide_index=True)


def render_charts(forecasts) -> None:
    """氣溫以「最低溫 ~ 最高溫」浮動長條呈現，降雨機率以 0–100% 長條呈現。"""
    st.subheader("📈 趨勢圖")
    chart_data = pd.DataFrame(
        {
            "period": [p.period_label for p in forecasts],
            "min_temp": [p.min_temp for p in forecasts],
            "max_temp": [p.max_temp for p in forecasts],
            "pop": [p.pop for p in forecasts],
        }
    )
    # 時段標籤太長，在「~」處換行；sort=None 保留時間順序
    x_axis = alt.X(
        "period:N",
        sort=None,
        title=None,
        axis=alt.Axis(labelAngle=0, labelExpr="split(datum.label, ' ~ ')"),
    )

    col_temp, col_pop = st.columns(2)

    with col_temp:
        st.caption("氣溫區間（°C）：長條底部為最低溫、頂部為最高溫")
        temps = chart_data.dropna(subset=["min_temp", "max_temp"])
        base = alt.Chart(temps).encode(x=x_axis)
        bars = base.mark_bar(size=36, cornerRadius=6, color="#f28e2b").encode(
            y=alt.Y("min_temp:Q", title="°C", scale=alt.Scale(zero=False, padding=12)),
            y2="max_temp:Q",
            tooltip=[
                alt.Tooltip("period:N", title="時段"),
                alt.Tooltip("min_temp:Q", title="最低溫"),
                alt.Tooltip("max_temp:Q", title="最高溫"),
            ],
        )
        low_labels = base.mark_text(dy=12).encode(y="min_temp:Q", text="min_temp:Q")
        high_labels = base.mark_text(dy=-8).encode(y="max_temp:Q", text="max_temp:Q")
        st.altair_chart(bars + low_labels + high_labels, use_container_width=True)

    with col_pop:
        st.caption("降雨機率（%）")
        pop = chart_data.dropna(subset=["pop"])
        base = alt.Chart(pop).encode(x=x_axis)
        bars = base.mark_bar(size=36, cornerRadius=6, color="#4c78a8").encode(
            y=alt.Y("pop:Q", title="%", scale=alt.Scale(domain=[0, 100])),
            tooltip=[
                alt.Tooltip("period:N", title="時段"),
                alt.Tooltip("pop:Q", title="降雨機率 (%)"),
            ],
        )
        labels = base.mark_text(dy=-8).encode(y="pop:Q", text="pop:Q")
        st.altair_chart(bars + labels, use_container_width=True)


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

    period_label = next(iter(all_forecasts.values()))[0].period_label
    st.subheader("🗺️ 全台氣溫分布")
    st.caption(f"時段：{period_label}　｜　顏色代表最高溫，標籤為「最低~最高」溫度，黑框為目前選擇的縣市")

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
    fill = counties.mark_geoshape(stroke="white", strokeWidth=0.8).encode(
        color=alt.Color(
            "max_temp:Q",
            title="最高溫 (°C)",
            scale=alt.Scale(scheme="redyellowblue", reverse=True, domain=MAP_TEMP_RANGE, clamp=True),
        ),
        tooltip=tooltip,
    )
    highlight = (
        counties.transform_filter(alt.datum.city == selected_city)
        .mark_geoshape(fill=None, stroke="black", strokeWidth=2.5)
    )

    points = alt.Chart(map_data).encode(longitude="lon:Q", latitude="lat:Q", tooltip=tooltip)
    dots = points.mark_circle(size=30, color="black")
    labels = points.mark_text(
        dy=-11, fontSize=11, fontWeight="bold", stroke="white", strokeWidth=3
    ).encode(text="label:N")
    labels_fill = points.mark_text(dy=-11, fontSize=11, fontWeight="bold").encode(text="label:N")

    chart = (
        alt.layer(fill, highlight, dots, labels, labels_fill)
        .project(type="mercator")
        .properties(height=720)
    )
    st.altair_chart(chart, use_container_width=True)


def main() -> None:
    st.title("🌦️ 台灣天氣預報")
    st.caption("資料來源：交通部中央氣象署開放資料平臺（F-C0032-001 今明 36 小時天氣預報）")

    api_key = get_api_key()

    with st.sidebar:
        st.header("查詢設定")
        city = st.selectbox("選擇縣市", CITIES, index=CITIES.index(DEFAULT_CITY))
        if st.button("🔄 重新取得資料", width="stretch"):
            load_all_forecasts.clear()
        st.divider()
        st.caption("API 金鑰狀態：" + ("✅ 已設定" if api_key else "❌ 未設定"))

    if not api_key:
        show_api_key_help()
        return

    try:
        with st.spinner("正在取得全台天氣預報…"):
            all_forecasts = load_all_forecasts(api_key)
    except CWAError as error:
        st.error(f"取得預報失敗：{error}")
        st.caption("請確認網路連線與 API 金鑰是否正確，或稍後再試一次。")
        return

    forecasts = all_forecasts.get(city)
    if not forecasts:
        st.warning(f"目前查不到「{city}」的預報資料。")
    else:
        st.header(city)
        render_current_weather(forecasts[0])
        st.divider()
        render_forecast_table(forecasts)
        render_charts(forecasts)

    st.divider()
    render_map(all_forecasts, city)


if __name__ == "__main__":
    main()

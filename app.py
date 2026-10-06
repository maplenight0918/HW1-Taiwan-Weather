"""HW1：使用 CWA 開放資料的台灣天氣預報網站（Streamlit 介面）。

執行方式：
    streamlit run app.py
"""

import pandas as pd
import streamlit as st

from src.cwa_api import (
    CITIES,
    CITY_COORDS,
    CWAError,
    get_api_key,
    get_city_forecast,
    weather_icon,
)

DEFAULT_CITY = "臺中市"
CACHE_TTL_SECONDS = 600  # 預報每 10 分鐘才重新向 API 查詢一次

st.set_page_config(page_title="台灣天氣預報", page_icon="🌦️", layout="wide")


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_forecast(api_key: str, city: str):
    """包一層快取，避免每次互動都重新呼叫 CWA API。"""
    return get_city_forecast(api_key, city)


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


def render_current_weather(period) -> None:
    """用 metric 卡片顯示最近一個時段的預報。"""
    st.subheader(f"{weather_icon(period.weather)} 最近時段預報")
    st.caption(f"預報時段：{period.period_label}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("天氣狀況", period.weather)
    col2.metric(
        "最低溫",
        "無資料" if period.min_temp is None else f"{period.min_temp} °C",
    )
    col3.metric(
        "最高溫",
        "無資料" if period.max_temp is None else f"{period.max_temp} °C",
    )
    col4.metric(
        "降雨機率",
        "無資料" if period.pop is None else f"{period.pop} %",
    )

    if period.comfort and period.comfort != "無資料":
        st.info(f"體感舒適度：{period.comfort}")


def render_forecast_table(forecasts) -> pd.DataFrame:
    """以表格呈現全部三個預報時段，並回傳整理後的 DataFrame。"""
    table = pd.DataFrame([period.as_row() for period in forecasts])
    st.subheader("📋 36 小時預報明細")
    st.dataframe(table, width="stretch", hide_index=True)
    return table


def render_charts(table: pd.DataFrame) -> None:
    """用簡單的長條圖呈現氣溫區間與降雨機率。"""
    st.subheader("📈 趨勢圖")
    chart_data = table.set_index("預報時段")

    col_temp, col_pop = st.columns(2)
    with col_temp:
        st.caption("氣溫區間（°C）")
        st.bar_chart(chart_data[["最低溫 (°C)", "最高溫 (°C)"]])
    with col_pop:
        st.caption("降雨機率（%）")
        st.bar_chart(chart_data[["降雨機率 (%)"]])


def render_map(city: str) -> None:
    """在地圖上標出所選縣市的位置。"""
    coords = CITY_COORDS.get(city)
    if coords is None:
        return

    st.subheader("🗺️ 查詢位置")
    latitude, longitude = coords
    st.map(
        pd.DataFrame({"lat": [latitude], "lon": [longitude]}),
        zoom=8,
    )


def main() -> None:
    st.title("🌦️ 台灣天氣預報")
    st.caption("資料來源：交通部中央氣象署開放資料平臺（F-C0032-001 今明 36 小時天氣預報）")

    api_key = get_api_key()

    with st.sidebar:
        st.header("查詢設定")
        city = st.selectbox(
            "選擇縣市",
            CITIES,
            index=CITIES.index(DEFAULT_CITY),
        )
        if st.button("🔄 重新取得資料", width="stretch"):
            load_forecast.clear()
        st.divider()
        st.caption("API 金鑰狀態：" + ("✅ 已設定" if api_key else "❌ 未設定"))

    if not api_key:
        show_api_key_help()
        return

    try:
        with st.spinner(f"正在取得「{city}」的天氣預報…"):
            forecasts = load_forecast(api_key, city)
    except CWAError as error:
        st.error(f"取得預報失敗：{error}")
        st.caption("請確認網路連線與 API 金鑰是否正確，或稍後再試一次。")
        return

    if not forecasts:
        st.warning(f"目前查不到「{city}」的預報資料。")
        return

    st.header(f"{city}")
    render_current_weather(forecasts[0])
    st.divider()

    table = render_forecast_table(forecasts)
    render_charts(table)
    render_map(city)


if __name__ == "__main__":
    main()

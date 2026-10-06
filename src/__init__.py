"""CWA 天氣預報網站的資料存取層。"""

from .cwa_api import (
    CITIES,
    CITY_COORDS,
    CWAError,
    ForecastPeriod,
    describe_period,
    get_all_forecasts,
    get_api_key,
    get_city_forecast,
    regional_averages,
    weather_kind,
)

__all__ = [
    "CITIES",
    "CITY_COORDS",
    "CWAError",
    "ForecastPeriod",
    "describe_period",
    "get_all_forecasts",
    "get_api_key",
    "get_city_forecast",
    "regional_averages",
    "weather_kind",
]

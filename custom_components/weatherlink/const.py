"""Constants for the Weatherlink integration."""
from enum import StrEnum

DOMAIN = "weatherlink"
VERSION = "0.9.2"

CONF_API_VERSION = "api_version"
CONF_API_KEY_V2 = "api_key_v2"
CONF_API_SECRET = "api_secret"
CONF_API_TOKEN = "apitoken"
CONF_STATION_ID = "station_id"


class ApiVersion(StrEnum):
    """Supported API versions."""

    API_V1 = "api_v1"
    API_V2 = "api_v2"


class DataKey(StrEnum):
    """Keys for normalized observation data."""

    BAR_SEA_LEVEL = "bar_sea_level"
    BAR_TREND = "bar_trend"
    DATA_STRUCTURE = "data_structure"
    DEWPOINT = "dewpoint"
    HUM_IN = "hum_in"
    HUM_OUT = "hum_out"
    RAIN_DAY = "rain_day"
    RAIN_MONTH = "rain_month"
    RAIN_RATE = "rain_rate"
    RAIN_YEAR = "rain_year"
    SOLAR_PANEL_VOLT = "solar_panel_volt"
    SUPERCAP_VOLT = "supercap_volt"
    TEMP_IN = "temp_in"
    TEMP_OUT = "temp_out"
    TRANS_BATTERY_FLAG = "trans_battery_flag"
    TRANS_BATTERY_VOLT = "trans_battery_volt"
    UUID = "station_id_uuid"
    WIND_DIR = "wind_dir"
    WIND_MPH = "wind_mph"

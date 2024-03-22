"""Constants for the Weatherlink integration."""

from enum import StrEnum

DOMAIN = "weatherlink"
VERSION = "2024.1.1"

MANUFACTURER = "Davis Instruments"
CONFIG_URL = "https://www.weatherlink.com/"

CONF_API_VERSION = "api_version"
CONF_API_KEY_V2 = "api_key_v2"
CONF_API_SECRET = "api_secret"
CONF_API_TOKEN = "apitoken"
CONF_STATION_ID = "station_id"

DISCONNECTED_AFTER_SECONDS = 1830
UNAVAILABLE_AFTER_SECONDS = 3630


class ApiVersion(StrEnum):
    """Supported API versions."""

    API_V1 = "api_v1"
    API_V2 = "api_v2"


class DataKey(StrEnum):
    """Keys for normalized observation data."""

    AQI_VAL = "aqi_val"
    AQI_NOWCAST_VAL = "aqi_nowcast_val"
    BAR_SEA_LEVEL = "bar_sea_level"
    BAR_TREND = "bar_trend"
    DATA_STRUCTURE = "data_structure"
    DEWPOINT = "dewpoint"
    ET_DAY = "et_day"
    ET_MONTH = "et_month"
    ET_YEAR = "et_year"
    HEAT_INDEX = "heat_index"
    HUM = "hum"
    HUM_EXTRA = "hum_extra"
    HUM_IN = "hum_in"
    HUM_OUT = "hum_out"
    MOIST_SOIL = "moist_soil"
    PM_1 = "pm_1"
    PM_2P5 = "pm_2p5"
    PM_10 = "pm_10"
    RAIN_DAY = "rain_day"
    RAIN_MONTH = "rain_month"
    RAIN_RATE = "rain_rate"
    RAIN_STORM = "rain_storm"
    RAIN_STORM_LAST = "rain_storm_last"
    RAIN_STORM_LAST_END = "rain_storm_last_end"
    RAIN_STORM_LAST_START = "rain_storm_last_start"
    RAIN_STORM_START = "rain_storm_start"
    RAIN_YEAR = "rain_year"
    SENSOR_TYPE = "sensor_type"
    SOLAR_PANEL_VOLT = "solar_panel_volt"
    SOLAR_RADIATION = "solar_radiation"
    SUPERCAP_VOLT = "supercap_volt"
    TEMP = "temp"
    TEMP_EXTRA = "temp_extra"
    TEMP_SOIL = "temp_soil"
    TEMP_IN = "temp_in"
    TEMP_OUT = "temp_out"
    TIMESTAMP = "timestamp"
    THW_INDEX = "thw_index"
    THSW_INDEX = "thsw_index"
    TRANS_BATTERY_FLAG = "trans_battery_flag"
    TRANS_BATTERY_VOLT = "trans_battery_volt"
    UUID = "station_id_uuid"
    UV_INDEX = "uv_index"
    WET_BULB = "wet_bulb"
    WET_LEAF = "wet_leaf"
    WIND_CHILL = "wind_chill"
    WIND_DIR = "wind_dir"
    WIND_MPH = "wind_mph"
    WIND_GUST_MPH = "wind_gust_mph"

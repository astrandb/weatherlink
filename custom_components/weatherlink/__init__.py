"""The Weatherlink integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from aiohttp import ClientResponseError
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_API_KEY_V2,
    CONF_API_SECRET,
    CONF_API_TOKEN,
    CONF_API_VERSION,
    CONF_STATION_ID,
    DOMAIN,
    ApiVersion,
    DataKey,
)
from .pyweatherlink import WLHub, WLHubV2

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]
SENSOR_TYPE_VUE_AND_VANTAGE_PRO = (
    23,
    24,
    27,
    28,
    37,
    43,
    44,
    45,
    46,
    48,
    49,
    50,
    51,
    76,
    77,
    78,
    79,
    80,
    81,
    82,
    83,
    84,
    85,
    87,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Weatherlink from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}
    if entry.data[CONF_API_VERSION] == ApiVersion.API_V1:
        hass.data[DOMAIN][entry.entry_id]["api"] = WLHub(
            websession=async_get_clientsession(hass),
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            apitoken=entry.data[CONF_API_TOKEN],
        )

    if entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
        hass.data[DOMAIN][entry.entry_id]["api"] = WLHubV2(
            websession=async_get_clientsession(hass),
            station_id=entry.data[CONF_STATION_ID],
            api_key_v2=entry.data[CONF_API_KEY_V2],
            api_secret=entry.data[CONF_API_SECRET],
        )
        hass.data[DOMAIN][entry.entry_id]["station_data"] = await hass.data[DOMAIN][
            entry.entry_id
        ]["api"].get_station()

    coordinator = await get_coordinator(hass, entry)
    if not coordinator.last_update_success:
        await coordinator.async_config_entry_first_refresh()
    _LOGGER.debug("First data: %s", coordinator.data)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def get_coordinator(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> DataUpdateCoordinator:
    """Get the data update coordinator."""
    if "coordinator" in hass.data[DOMAIN][entry.entry_id]:
        return hass.data[DOMAIN][entry.entry_id]["coordinator"]

    def _preprocess(indata: str):
        outdata = {}
        _LOGGER.debug("Received data: %s", indata)
        if entry.data[CONF_API_VERSION] == ApiVersion.API_V1:
            outdata["DID"] = indata["davis_current_observation"].get("DID")
            outdata["station_name"] = indata["davis_current_observation"].get(
                "station_name"
            )
            outdata[DataKey.TEMP_OUT] = indata.get("temp_f")
            outdata[DataKey.TEMP_IN] = indata["davis_current_observation"].get(
                "temp_in_f"
            )
            outdata[DataKey.HUM_IN] = indata["davis_current_observation"].get(
                "relative_humidity_in"
            )
            outdata[DataKey.HUM_OUT] = indata.get("relative_humidity")
            outdata[DataKey.BAR_SEA_LEVEL] = indata.get("pressure_in")
            outdata[DataKey.WIND_MPH] = indata.get("wind_mph")
            outdata[DataKey.WIND_GUST_MPH] = indata["davis_current_observation"].get(
                "wind_ten_min_gust_mph"
            )
            outdata[DataKey.WIND_DIR] = indata.get("wind_degrees")
            outdata[DataKey.DEWPOINT] = indata.get("dewpoint_f")
            outdata[DataKey.RAIN_DAY] = indata["davis_current_observation"].get(
                "rain_day_in"
            )
            outdata[DataKey.RAIN_STORM] = indata["davis_current_observation"].get(
                "rain_storm_in"
            )
            outdata[DataKey.RAIN_RATE] = indata["davis_current_observation"].get(
                "rain_rate_in_per_hr"
            )
            outdata[DataKey.RAIN_MONTH] = indata["davis_current_observation"].get(
                "rain_month_in"
            )
            outdata[DataKey.RAIN_YEAR] = indata["davis_current_observation"].get(
                "rain_year_in"
            )
            outdata[DataKey.BAR_TREND] = indata["davis_current_observation"].get(
                "pressure_tendency_string"
            )

        if entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
            outdata[DataKey.UUID] = indata["station_id_uuid"]
            for sensor in indata["sensors"]:
                # Vue
                if (
                    sensor["sensor_type"] in SENSOR_TYPE_VUE_AND_VANTAGE_PRO
                    and sensor["data_structure_type"] == 10
                ):
                    outdata[DataKey.DATA_STRUCTURE] = sensor["data_structure_type"]
                    outdata[DataKey.TEMP_OUT] = sensor["data"][0]["temp"]
                    outdata[DataKey.HUM_OUT] = sensor["data"][0]["hum"]
                    outdata[DataKey.WIND_MPH] = sensor["data"][0]["wind_speed_last"]
                    outdata[DataKey.WIND_GUST_MPH] = sensor["data"][0][
                        "wind_speed_hi_last_10_min"
                    ]
                    outdata[DataKey.WIND_DIR] = sensor["data"][0]["wind_dir_last"]
                    outdata[DataKey.DEWPOINT] = sensor["data"][0]["dew_point"]
                    outdata[DataKey.RAIN_DAY] = float(
                        sensor["data"][0]["rainfall_daily_in"]
                    )
                    outdata[DataKey.RAIN_STORM] = float(
                        sensor["data"][0]["rain_storm_in"]
                    )
                    outdata[DataKey.RAIN_STORM_START] = sensor["data"][0].get(
                        "rain_storm_start_at"
                    )

                    outdata[DataKey.RAIN_RATE] = sensor["data"][0]["rain_rate_last_in"]
                    outdata[DataKey.RAIN_MONTH] = sensor["data"][0][
                        "rainfall_monthly_in"
                    ]
                    outdata[DataKey.RAIN_YEAR] = sensor["data"][0]["rainfall_year_in"]
                    outdata[DataKey.TRANS_BATTERY_FLAG] = sensor["data"][0][
                        "trans_battery_flag"
                    ]
                if (
                    sensor["sensor_type"] in SENSOR_TYPE_VUE_AND_VANTAGE_PRO
                    and sensor["data_structure_type"] == 2
                ):
                    outdata[DataKey.DATA_STRUCTURE] = sensor["data_structure_type"]
                    outdata[DataKey.TEMP_OUT] = sensor["data"][0]["temp_out"]
                    outdata[DataKey.TEMP_IN] = sensor["data"][0]["temp_in"]
                    outdata[DataKey.BAR_SEA_LEVEL] = sensor["data"][0]["bar"]
                    outdata[DataKey.BAR_TREND] = (
                        float(sensor["data"][0]["bar_trend"]) / 1000
                    )
                    outdata[DataKey.HUM_OUT] = sensor["data"][0]["hum_out"]
                    outdata[DataKey.HUM_IN] = sensor["data"][0]["hum_in"]
                    outdata[DataKey.WIND_MPH] = sensor["data"][0]["wind_speed"]
                    outdata[DataKey.WIND_GUST_MPH] = sensor["data"][0][
                        "wind_gust_10_min"
                    ]
                    outdata[DataKey.WIND_DIR] = sensor["data"][0]["wind_dir"]
                    outdata[DataKey.DEWPOINT] = sensor["data"][0]["dew_point"]
                    outdata[DataKey.RAIN_DAY] = float(sensor["data"][0]["rain_day_in"])
                    outdata[DataKey.RAIN_STORM] = float(
                        sensor["data"][0]["rain_storm_in"]
                    )
                    outdata[DataKey.RAIN_STORM_START] = sensor["data"][0].get(
                        "rain_storm_start_date"
                    )
                    outdata[DataKey.RAIN_RATE] = sensor["data"][0]["rain_rate_in"]
                    outdata[DataKey.RAIN_MONTH] = sensor["data"][0]["rain_month_in"]
                    outdata[DataKey.RAIN_YEAR] = sensor["data"][0]["rain_year_in"]

                if (
                    sensor["sensor_type"] in SENSOR_TYPE_VUE_AND_VANTAGE_PRO
                    and sensor["data_structure_type"] == 23
                ):
                    outdata[DataKey.DATA_STRUCTURE] = sensor["data_structure_type"]
                    outdata[DataKey.TEMP_OUT] = sensor["data"][0]["temp"]
                    outdata[DataKey.HUM_OUT] = sensor["data"][0]["hum"]
                    outdata[DataKey.WIND_MPH] = sensor["data"][0]["wind_speed_last"]
                    outdata[DataKey.WIND_GUST_MPH] = sensor["data"][0][
                        "wind_speed_hi_last_10_min"
                    ]
                    outdata[DataKey.WIND_DIR] = sensor["data"][0]["wind_dir_last"]
                    outdata[DataKey.DEWPOINT] = sensor["data"][0]["dew_point"]
                    outdata[DataKey.RAIN_DAY] = float(
                        sensor["data"][0]["rainfall_day_in"]
                    )
                    x_storm = sensor["data"][0]["rain_storm_current_in"]
                    outdata[DataKey.RAIN_STORM] = float(
                        x_storm if x_storm is not None else 0.0
                    )
                    outdata[DataKey.RAIN_STORM_START] = sensor["data"][0].get(
                        "rain_storm_start_at"
                    )
                    outdata[DataKey.RAIN_RATE] = sensor["data"][0]["rain_rate_last_in"]
                    outdata[DataKey.RAIN_MONTH] = sensor["data"][0]["rainfall_month_in"]
                    outdata[DataKey.RAIN_YEAR] = sensor["data"][0]["rainfall_year_in"]
                    outdata[DataKey.TRANS_BATTERY_FLAG] = sensor["data"][0][
                        "trans_battery_flag"
                    ]
                    outdata[DataKey.TRANS_BATTERY_VOLT] = sensor["data"][0][
                        "trans_battery_volt"
                    ]
                    outdata[DataKey.SUPERCAP_VOLT] = sensor["data"][0]["supercap_volt"]
                    outdata[DataKey.SOLAR_PANEL_VOLT] = sensor["data"][0][
                        "solar_panel_volt"
                    ]

                if sensor["sensor_type"] == 365 and sensor["data_structure_type"] == 21:
                    outdata[DataKey.TEMP_IN] = sensor["data"][0]["temp_in"]
                    outdata[DataKey.HUM_IN] = sensor["data"][0]["hum_in"]
                if sensor["sensor_type"] == 243 and sensor["data_structure_type"] == 12:
                    outdata[DataKey.TEMP_IN] = sensor["data"][0]["temp_in"]
                    outdata[DataKey.HUM_IN] = sensor["data"][0]["hum_in"]
                if sensor["sensor_type"] == 242 and sensor["data_structure_type"] == 12:
                    outdata[DataKey.BAR_SEA_LEVEL] = sensor["data"][0]["bar_sea_level"]
                    outdata[DataKey.BAR_TREND] = sensor["data"][0]["bar_trend"]
                if sensor["sensor_type"] == 242 and sensor["data_structure_type"] == 19:
                    outdata[DataKey.BAR_SEA_LEVEL] = sensor["data"][0]["bar_sea_level"]
                    outdata[DataKey.BAR_TREND] = sensor["data"][0]["bar_trend"]

        return outdata

    async def async_fetch():
        api = hass.data[DOMAIN][entry.entry_id]["api"]
        try:
            async with async_timeout.timeout(10):
                res = await api.request("GET")
                json_data = await res.json()
                hass.data[DOMAIN][entry.entry_id]["current"] = json_data
                return _preprocess(json_data)
        except ClientResponseError as exc:
            _LOGGER.warning("API fetch failed. Status: %s, - %s", exc.code, exc.message)
            raise UpdateFailed(exc) from exc

    hass.data[DOMAIN][entry.entry_id]["coordinator"] = DataUpdateCoordinator(
        hass,
        logging.getLogger(__name__),
        name=DOMAIN,
        update_method=async_fetch,
        update_interval=timedelta(minutes=5),
    )
    await hass.data[DOMAIN][entry.entry_id]["coordinator"].async_refresh()
    return hass.data[DOMAIN][entry.entry_id]["coordinator"]


async def async_migrate_entry(hass, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.info("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        new_data = {**config_entry.data}

        new_data[CONF_API_VERSION] = ApiVersion.API_V1

        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=new_data)

    _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True

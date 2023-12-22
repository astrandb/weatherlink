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
    55,
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

        all_sensors = await hass.data[DOMAIN][entry.entry_id]["api"].get_all_sensors()

        sensors = []
        for sensor in all_sensors["sensors"]:
            if (
                sensor["parent_device_id"]
                == hass.data[DOMAIN][entry.entry_id]["station_data"]["stations"][0][
                    "gateway_id"
                ]
            ):
                sensors.append(sensor)
        hass.data[DOMAIN][entry.entry_id]["sensors_metadata"] = sensors
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
        outdata[1] = {}
        tx_id = 1
        # _LOGGER.debug("Received data: %s", indata)
        if entry.data[CONF_API_VERSION] == ApiVersion.API_V1:
            outdata[tx_id]["DID"] = indata["davis_current_observation"].get("DID")
            outdata[tx_id]["station_name"] = indata["davis_current_observation"].get(
                "station_name"
            )
            outdata[tx_id][DataKey.TEMP_OUT] = indata.get("temp_f")
            outdata[tx_id][DataKey.HEAT_INDEX] = indata.get("heat_index_f")
            outdata[tx_id][DataKey.WIND_CHILL] = indata.get("wind_chill_f")
            outdata[tx_id][DataKey.TEMP_IN] = indata["davis_current_observation"].get(
                "temp_in_f"
            )
            outdata[tx_id][DataKey.HUM_IN] = indata["davis_current_observation"].get(
                "relative_humidity_in"
            )
            outdata[tx_id][DataKey.HUM_OUT] = indata.get("relative_humidity")
            outdata[tx_id][DataKey.BAR_SEA_LEVEL] = indata.get("pressure_in")
            outdata[tx_id][DataKey.WIND_MPH] = indata.get("wind_mph")
            outdata[tx_id][DataKey.WIND_GUST_MPH] = indata[
                "davis_current_observation"
            ].get("wind_ten_min_gust_mph")
            outdata[tx_id][DataKey.WIND_DIR] = indata.get("wind_degrees")
            outdata[tx_id][DataKey.DEWPOINT] = indata.get("dewpoint_f")
            outdata[tx_id][DataKey.RAIN_DAY] = indata["davis_current_observation"].get(
                "rain_day_in"
            )
            outdata[tx_id][DataKey.RAIN_STORM] = indata[
                "davis_current_observation"
            ].get("rain_storm_in")
            outdata[tx_id][DataKey.RAIN_RATE] = indata["davis_current_observation"].get(
                "rain_rate_in_per_hr"
            )
            outdata[tx_id][DataKey.RAIN_MONTH] = indata[
                "davis_current_observation"
            ].get("rain_month_in")
            outdata[tx_id][DataKey.RAIN_YEAR] = indata["davis_current_observation"].get(
                "rain_year_in"
            )
            outdata[tx_id][DataKey.BAR_TREND] = indata["davis_current_observation"].get(
                "pressure_tendency_string"
            )

        if entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
            outdata[DataKey.UUID] = indata["station_id_uuid"]
            for sensor in indata["sensors"]:
                # outdata[tx_id][DataKey.SENSOR_TYPE] = sensor["sensor_type"]
                # Vue
                if (
                    sensor["sensor_type"] in SENSOR_TYPE_VUE_AND_VANTAGE_PRO
                    and sensor["data_structure_type"] == 10
                ):
                    tx_id = sensor["data"][0]["tx_id"]
                    outdata.setdefault(tx_id, {})
                    outdata[DataKey.DATA_STRUCTURE] = sensor["data_structure_type"]
                    outdata[tx_id][DataKey.TEMP_OUT] = sensor["data"][0]["temp"]
                    outdata[tx_id][DataKey.HUM_OUT] = sensor["data"][0]["hum"]
                    outdata[tx_id][DataKey.WIND_MPH] = sensor["data"][0][
                        "wind_speed_last"
                    ]
                    outdata[tx_id][DataKey.WIND_GUST_MPH] = sensor["data"][0][
                        "wind_speed_hi_last_10_min"
                    ]
                    outdata[tx_id][DataKey.WIND_DIR] = sensor["data"][0][
                        "wind_dir_last"
                    ]
                    outdata[tx_id][DataKey.DEWPOINT] = sensor["data"][0]["dew_point"]
                    outdata[tx_id][DataKey.HEAT_INDEX] = sensor["data"][0]["heat_index"]
                    outdata[tx_id][DataKey.THW_INDEX] = sensor["data"][0]["thw_index"]
                    outdata[tx_id][DataKey.THSW_INDEX] = sensor["data"][0]["thsw_index"]
                    outdata[tx_id][DataKey.WET_BULB] = sensor["data"][0]["wet_bulb"]
                    outdata[tx_id][DataKey.WIND_CHILL] = sensor["data"][0]["wind_chill"]
                    outdata[tx_id][DataKey.RAIN_DAY] = float(
                        sensor["data"][0]["rainfall_daily_in"]
                    )
                    outdata[tx_id][DataKey.RAIN_STORM] = float(
                        sensor["data"][0]["rain_storm_in"]
                    )
                    outdata[tx_id][DataKey.RAIN_STORM_START] = sensor["data"][0].get(
                        "rain_storm_start_at"
                    )
                    outdata[tx_id][DataKey.RAIN_STORM_LAST] = float(
                        sensor["data"][0]["rain_storm_last_in"]
                    )
                    outdata[tx_id][DataKey.RAIN_STORM_LAST_START] = sensor["data"][
                        0
                    ].get("rain_storm_last_start_at")
                    outdata[tx_id][DataKey.RAIN_STORM_LAST_END] = sensor["data"][0].get(
                        "rain_storm_last_end_at"
                    )

                    outdata[tx_id][DataKey.RAIN_RATE] = sensor["data"][0][
                        "rain_rate_last_in"
                    ]
                    outdata[tx_id][DataKey.RAIN_MONTH] = sensor["data"][0][
                        "rainfall_monthly_in"
                    ]
                    outdata[tx_id][DataKey.RAIN_YEAR] = sensor["data"][0][
                        "rainfall_year_in"
                    ]
                    outdata[tx_id][DataKey.TRANS_BATTERY_FLAG] = sensor["data"][0][
                        "trans_battery_flag"
                    ]
                    outdata[tx_id][DataKey.SOLAR_RADIATION] = sensor["data"][0][
                        "solar_rad"
                    ]
                if (
                    sensor["sensor_type"] in SENSOR_TYPE_VUE_AND_VANTAGE_PRO
                    and sensor["data_structure_type"] == 2
                ):
                    tx_id = sensor["data"][0].get("tx_id", 1)
                    outdata.setdefault(tx_id, {})
                    outdata[DataKey.DATA_STRUCTURE] = sensor["data_structure_type"]
                    outdata[tx_id][DataKey.TEMP_OUT] = sensor["data"][0]["temp_out"]
                    outdata[tx_id][DataKey.TEMP_IN] = sensor["data"][0]["temp_in"]
                    outdata[tx_id][DataKey.BAR_SEA_LEVEL] = sensor["data"][0]["bar"]
                    outdata[tx_id][DataKey.BAR_TREND] = (
                        float(sensor["data"][0]["bar_trend"]) / 1000
                    )
                    outdata[tx_id][DataKey.HUM_OUT] = sensor["data"][0]["hum_out"]
                    outdata[tx_id][DataKey.HUM_IN] = sensor["data"][0]["hum_in"]
                    outdata[tx_id][DataKey.WIND_MPH] = sensor["data"][0]["wind_speed"]
                    outdata[tx_id][DataKey.WIND_GUST_MPH] = sensor["data"][0][
                        "wind_gust_10_min"
                    ]
                    outdata[tx_id][DataKey.WIND_DIR] = sensor["data"][0]["wind_dir"]
                    outdata[tx_id][DataKey.DEWPOINT] = sensor["data"][0]["dew_point"]
                    outdata[tx_id][DataKey.HEAT_INDEX] = sensor["data"][0]["heat_index"]
                    outdata[tx_id][DataKey.WIND_CHILL] = sensor["data"][0]["wind_chill"]
                    outdata[tx_id][DataKey.RAIN_DAY] = float(
                        sensor["data"][0]["rain_day_in"]
                    )
                    outdata[tx_id][DataKey.RAIN_STORM] = float(
                        sensor["data"][0]["rain_storm_in"]
                    )
                    outdata[tx_id][DataKey.RAIN_STORM_START] = sensor["data"][0].get(
                        "rain_storm_start_date"
                    )
                    outdata[tx_id][DataKey.RAIN_RATE] = sensor["data"][0][
                        "rain_rate_in"
                    ]
                    outdata[tx_id][DataKey.RAIN_MONTH] = sensor["data"][0][
                        "rain_month_in"
                    ]
                    outdata[tx_id][DataKey.RAIN_YEAR] = sensor["data"][0][
                        "rain_year_in"
                    ]
                    outdata[tx_id][DataKey.SOLAR_RADIATION] = sensor["data"][0][
                        "solar_rad"
                    ]

                if (
                    sensor["sensor_type"] in SENSOR_TYPE_VUE_AND_VANTAGE_PRO
                    and sensor["data_structure_type"] == 23
                ):
                    tx_id = sensor["data"][0]["tx_id"]
                    outdata.setdefault(tx_id, {})
                    outdata[DataKey.DATA_STRUCTURE] = sensor["data_structure_type"]
                    outdata[tx_id][DataKey.TEMP_OUT] = sensor["data"][0]["temp"]
                    outdata[tx_id][DataKey.HUM_OUT] = sensor["data"][0]["hum"]
                    outdata[tx_id][DataKey.WIND_MPH] = sensor["data"][0][
                        "wind_speed_last"
                    ]
                    outdata[tx_id][DataKey.WIND_GUST_MPH] = sensor["data"][0][
                        "wind_speed_hi_last_10_min"
                    ]
                    outdata[tx_id][DataKey.WIND_DIR] = sensor["data"][0][
                        "wind_dir_last"
                    ]
                    outdata[tx_id][DataKey.DEWPOINT] = sensor["data"][0]["dew_point"]
                    outdata[tx_id][DataKey.HEAT_INDEX] = sensor["data"][0]["heat_index"]
                    outdata[tx_id][DataKey.THW_INDEX] = sensor["data"][0]["thw_index"]
                    outdata[tx_id][DataKey.THSW_INDEX] = sensor["data"][0]["thsw_index"]
                    outdata[tx_id][DataKey.WET_BULB] = sensor["data"][0]["wet_bulb"]
                    outdata[tx_id][DataKey.WIND_CHILL] = sensor["data"][0]["wind_chill"]
                    outdata[tx_id][DataKey.RAIN_DAY] = float(
                        sensor["data"][0]["rainfall_day_in"]
                    )
                    x_storm = sensor["data"][0]["rain_storm_current_in"]
                    outdata[tx_id][DataKey.RAIN_STORM] = float(
                        x_storm if x_storm is not None else 0.0
                    )
                    outdata[tx_id][DataKey.RAIN_STORM_START] = sensor["data"][0].get(
                        "rain_storm_current_start_at"
                    )
                    x_storm = sensor["data"][0]["rain_storm_last_in"]
                    outdata[tx_id][DataKey.RAIN_STORM_LAST] = float(
                        x_storm if x_storm is not None else 0.0
                    )
                    outdata[tx_id][DataKey.RAIN_STORM_LAST_START] = sensor["data"][
                        0
                    ].get("rain_storm_last_start_at")
                    outdata[tx_id][DataKey.RAIN_STORM_LAST_END] = sensor["data"][0].get(
                        "rain_storm_last_end_at"
                    )

                    outdata[tx_id][DataKey.RAIN_RATE] = sensor["data"][0][
                        "rain_rate_last_in"
                    ]
                    outdata[tx_id][DataKey.RAIN_MONTH] = sensor["data"][0][
                        "rainfall_month_in"
                    ]
                    outdata[tx_id][DataKey.RAIN_YEAR] = sensor["data"][0][
                        "rainfall_year_in"
                    ]
                    outdata[tx_id][DataKey.TRANS_BATTERY_FLAG] = sensor["data"][0][
                        "trans_battery_flag"
                    ]
                    outdata[tx_id][DataKey.TRANS_BATTERY_VOLT] = sensor["data"][0][
                        "trans_battery_volt"
                    ]
                    outdata[tx_id][DataKey.SUPERCAP_VOLT] = sensor["data"][0][
                        "supercap_volt"
                    ]
                    outdata[tx_id][DataKey.SOLAR_PANEL_VOLT] = sensor["data"][0][
                        "solar_panel_volt"
                    ]
                    outdata[tx_id][DataKey.SOLAR_RADIATION] = sensor["data"][0][
                        "solar_rad"
                    ]

                if sensor["sensor_type"] == 365 and sensor["data_structure_type"] == 21:
                    outdata[tx_id][DataKey.TEMP_IN] = sensor["data"][0]["temp_in"]
                    outdata[tx_id][DataKey.HUM_IN] = sensor["data"][0]["hum_in"]
                if sensor["sensor_type"] == 243 and sensor["data_structure_type"] == 12:
                    outdata[tx_id][DataKey.TEMP_IN] = sensor["data"][0]["temp_in"]
                    outdata[tx_id][DataKey.HUM_IN] = sensor["data"][0]["hum_in"]
                if sensor["sensor_type"] == 242 and sensor["data_structure_type"] == 12:
                    outdata[tx_id][DataKey.BAR_SEA_LEVEL] = sensor["data"][0][
                        "bar_sea_level"
                    ]
                    outdata[tx_id][DataKey.BAR_TREND] = sensor["data"][0]["bar_trend"]
                if sensor["sensor_type"] == 242 and sensor["data_structure_type"] == 19:
                    outdata[tx_id][DataKey.BAR_SEA_LEVEL] = sensor["data"][0][
                        "bar_sea_level"
                    ]
                    outdata[tx_id][DataKey.BAR_TREND] = sensor["data"][0]["bar_trend"]

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

"""The Weatherlink integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from email.utils import mktime_tz, parsedate_tz
import logging

from aiohttp import ClientError, ClientResponseError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntry
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

type WLConfigEntry = ConfigEntry[WLData]


@dataclass
class WLData:
    """WIP."""

    api: WLHub | WLHubV2
    primary_tx_id: int
    station_data: dict
    sensors_metadata: dict
    coordinator: DataUpdateCoordinator
    current: dict


PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]
SENSOR_TYPE_VUE_AND_VANTAGE_PRO = (
    23,
    24,
    27,
    28,
    33,
    34,
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

SENSOR_TYPE_AIRLINK = (
    323,
    326,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: WLConfigEntry) -> bool:
    """Set up Weatherlink from a config entry."""

    entry.runtime_data = WLData(
        api=None,
        primary_tx_id=1,
        station_data={},
        sensors_metadata={},
        coordinator=None,
        current={},
    )

    if entry.data[CONF_API_VERSION] == ApiVersion.API_V1:
        entry.runtime_data.api = WLHub(
            websession=async_get_clientsession(hass),
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            apitoken=entry.data[CONF_API_TOKEN],
        )
        entry.runtime_data.primary_tx_id = 1
        tx_ids = [1]

    if entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
        entry.runtime_data.api = WLHubV2(
            websession=async_get_clientsession(hass),
            station_id=entry.data[CONF_STATION_ID],
            api_key_v2=entry.data[CONF_API_KEY_V2],
            api_secret=entry.data[CONF_API_SECRET],
        )
        try:
            entry.runtime_data.station_data = await entry.runtime_data.api.get_station()

            all_sensors = await entry.runtime_data.api.get_all_sensors()
        except ClientResponseError as err:
            if 400 <= err.status < 500:
                raise ConfigEntryAuthFailed(
                    translation_domain=DOMAIN,
                    translation_key="config_entry_auth_failed",
                ) from err
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="config_entry_not_ready",
            ) from err
        except ClientError as err:
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="config_entry_not_ready",
            ) from err

        sensors = []
        tx_ids = []
        for sensor in all_sensors["sensors"]:
            if (
                sensor["station_id"]
                == entry.runtime_data.station_data["stations"][0]["station_id"]
            ):
                sensors.append(sensor)
                if (
                    sensor["sensor_type"] in SENSOR_TYPE_VUE_AND_VANTAGE_PRO
                    and sensor["tx_id"] is not None
                    and sensor["tx_id"] not in tx_ids
                ):
                    tx_ids.append(sensor["tx_id"])
        entry.runtime_data.sensors_metadata = sensors
        # todo Make primary_tx_id configurable by user - perhaps in config flow.
        if len(tx_ids) == 0:
            tx_ids = [1]
        entry.runtime_data.primary_tx_id = min(tx_ids)

    _LOGGER.debug("Primary tx_ids: %s", tx_ids)
    coordinator = await get_coordinator(hass, entry)
    if not coordinator.last_update_success:
        await coordinator.async_config_entry_first_refresh()
    _LOGGER.debug("First data: %s", coordinator.data)

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, get_unique_id_base(entry))},
        name=entry.title,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


def get_unique_id_base(entry: WLConfigEntry):
    """Generate base for unique_id."""
    unique_base = None
    if entry.data[CONF_API_VERSION] == ApiVersion.API_V1:
        unique_base = entry.runtime_data.coordinator.data[
            entry.runtime_data.primary_tx_id
        ]["DID"]
    if entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
        unique_base = entry.runtime_data.coordinator.data[DataKey.UUID]
    return unique_base


async def async_unload_entry(hass: HomeAssistant, entry: WLConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


DCO = "davis_current_observation"


async def get_coordinator(  # noqa: C901
    hass: HomeAssistant,
    entry: WLConfigEntry,
) -> DataUpdateCoordinator:
    """Get the data update coordinator."""

    if entry.runtime_data.coordinator is not None:
        return entry.runtime_data.coordinator

    def _preprocess(indata: str):  # noqa: C901
        outdata = {}
        # _LOGGER.debug("Received data: %s", indata)
        if entry.data[CONF_API_VERSION] == ApiVersion.API_V1:
            tx_id = 1
            outdata.setdefault(tx_id, {})
            outdata[tx_id]["DID"] = indata[DCO].get("DID")
            outdata[tx_id]["station_name"] = indata[DCO].get("station_name")
            outdata[tx_id][DataKey.TEMP_OUT] = indata.get("temp_f")
            outdata[tx_id][DataKey.HEAT_INDEX] = indata.get("heat_index_f")
            outdata[tx_id][DataKey.WIND_CHILL] = indata.get("wind_chill_f")
            outdata[tx_id][DataKey.TEMP_IN] = indata[DCO].get("temp_in_f")
            outdata[tx_id][DataKey.HUM_IN] = indata[DCO].get("relative_humidity_in")
            outdata[tx_id][DataKey.HUM_OUT] = indata.get("relative_humidity")
            outdata[tx_id][DataKey.BAR_SEA_LEVEL] = indata.get("pressure_in")
            outdata[tx_id][DataKey.WIND_MPH] = indata.get("wind_mph")
            outdata[tx_id][DataKey.WIND_GUST_MPH] = indata[DCO].get(
                "wind_ten_min_gust_mph"
            )
            outdata[tx_id][DataKey.WIND_DIR] = indata.get("wind_degrees")
            outdata[tx_id][DataKey.DEWPOINT] = indata.get("dewpoint_f")
            outdata[tx_id][DataKey.RAIN_DAY] = indata[DCO].get("rain_day_in")
            outdata[tx_id][DataKey.RAIN_STORM] = indata[DCO].get("rain_storm_in", 0.0)
            outdata[tx_id][DataKey.RAIN_RATE] = indata[DCO].get("rain_rate_in_per_hr")
            outdata[tx_id][DataKey.RAIN_MONTH] = indata[DCO].get("rain_month_in")
            outdata[tx_id][DataKey.RAIN_YEAR] = indata[DCO].get("rain_year_in")
            outdata[tx_id][DataKey.BAR_TREND] = indata[DCO].get(
                "pressure_tendency_string"
            )
            outdata[tx_id][DataKey.SOLAR_RADIATION] = indata[DCO].get("solar_radiation")
            outdata[tx_id][DataKey.UV_INDEX] = indata[DCO].get("uv_index")
            outdata[tx_id][DataKey.ET_DAY] = indata[DCO].get("et_day")
            outdata[tx_id][DataKey.ET_MONTH] = indata[DCO].get("et_month")
            outdata[tx_id][DataKey.ET_YEAR] = indata[DCO].get("et_year")

            outdata[tx_id][DataKey.TIMESTAMP] = mktime_tz(
                parsedate_tz(indata["observation_time_rfc822"])
            )

        if entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
            primary_tx_id = tx_id = entry.runtime_data.primary_tx_id
            outdata.setdefault(tx_id, {})
            outdata[DataKey.UUID] = indata["station_id_uuid"]
            for sensor in indata["sensors"]:
                # Vue
                if (
                    sensor["sensor_type"] in SENSOR_TYPE_VUE_AND_VANTAGE_PRO
                    or sensor["sensor_type"] in [55]
                ) and sensor["data_structure_type"] == 10:
                    # _LOGGER.debug("Sensor: %s | %s", sensor["sensor_type"], sensor)
                    tx_id = sensor["data"][0]["tx_id"]
                    outdata.setdefault(tx_id, {})
                    outdata[tx_id][DataKey.SENSOR_TYPE] = sensor["sensor_type"]
                    outdata[tx_id][DataKey.DATA_STRUCTURE] = sensor[
                        "data_structure_type"
                    ]
                    outdata[tx_id][DataKey.TIMESTAMP] = sensor["data"][0]["ts"]
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
                    outdata[tx_id][DataKey.RAIN_DAY] = sensor["data"][0].get(
                        "rainfall_daily_in", 0.0
                    )

                    if (xx := sensor["data"][0].get("rain_storm_in", 0.0)) is None:
                        xx = 0.0
                    outdata[tx_id][DataKey.RAIN_STORM] = xx
                    outdata[tx_id][DataKey.RAIN_STORM_START] = sensor["data"][0].get(
                        "rain_storm_start_at"
                    )
                    if (xx := sensor["data"][0].get("rain_storm_last_in", 0.0)) is None:
                        xx = 0.0
                    outdata[tx_id][DataKey.RAIN_STORM_LAST] = xx
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
                    outdata[tx_id][DataKey.UV_INDEX] = sensor["data"][0]["uv_index"]
                    outdata[tx_id][DataKey.SOLAR_RADIATION] = sensor["data"][0][
                        "solar_rad"
                    ]
                    outdata[tx_id][DataKey.ET_DAY] = sensor["data"][0].get("et_day")
                    outdata[tx_id][DataKey.ET_MONTH] = sensor["data"][0].get("et_month")
                    outdata[tx_id][DataKey.ET_YEAR] = sensor["data"][0].get("et_year")

                # ----------- Data structure 2
                if (
                    sensor["sensor_type"] in SENSOR_TYPE_VUE_AND_VANTAGE_PRO
                    and sensor["data_structure_type"] == 2
                ):
                    tx_id = sensor["data"][0].get("tx_id", 1)
                    outdata.setdefault(tx_id, {})
                    outdata[tx_id][DataKey.SENSOR_TYPE] = sensor["sensor_type"]
                    outdata[tx_id][DataKey.DATA_STRUCTURE] = sensor[
                        "data_structure_type"
                    ]
                    outdata[tx_id][DataKey.TIMESTAMP] = sensor["data"][0]["ts"]
                    outdata[tx_id][DataKey.TEMP_OUT] = sensor["data"][0]["temp_out"]
                    outdata[tx_id][DataKey.TEMP_IN] = sensor["data"][0]["temp_in"]
                    for numb in range(1, 7 + 1):
                        outdata[tx_id][f"{DataKey.TEMP_EXTRA}_{numb}"] = sensor["data"][
                            0
                        ][f"temp_extra_{numb}"]
                    for numb in range(1, 4 + 1):
                        outdata[tx_id][f"{DataKey.TEMP_LEAF}_{numb}"] = sensor["data"][
                            0
                        ][f"temp_leaf_{numb}"]
                    for numb in range(1, 4 + 1):
                        outdata[tx_id][f"{DataKey.TEMP_SOIL}_{numb}"] = sensor["data"][
                            0
                        ][f"temp_soil_{numb}"]
                    for numb in range(1, 7 + 1):
                        outdata[tx_id][f"{DataKey.HUM_EXTRA}_{numb}"] = sensor["data"][
                            0
                        ][f"hum_extra_{numb}"]
                    for numb in range(1, 4 + 1):
                        outdata[tx_id][f"{DataKey.MOIST_SOIL}_{numb}"] = sensor["data"][
                            0
                        ][f"moist_soil_{numb}"]
                    for numb in range(1, 4 + 1):
                        outdata[tx_id][f"{DataKey.WET_LEAF}_{numb}"] = sensor["data"][
                            0
                        ][f"wet_leaf_{numb}"]
                    outdata[tx_id][DataKey.BAR_SEA_LEVEL] = sensor["data"][0]["bar"]
                    if (xx := sensor["data"][0].get("bar_trend", 0)) is not None:
                        xx = xx / 1000
                    outdata[tx_id][DataKey.BAR_TREND] = xx
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
                    outdata[tx_id][DataKey.RAIN_DAY] = sensor["data"][0].get(
                        "rain_day_in"
                    )
                    if (xx := sensor["data"][0].get("rain_storm_in", 0.0)) is None:
                        xx = 0.0
                    outdata[tx_id][DataKey.RAIN_STORM] = xx
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
                    outdata[tx_id][DataKey.UV_INDEX] = sensor["data"][0]["uv"]
                    outdata[tx_id][DataKey.ET_DAY] = sensor["data"][0]["et_day"]
                    outdata[tx_id][DataKey.ET_MONTH] = sensor["data"][0]["et_month"]
                    outdata[tx_id][DataKey.ET_YEAR] = sensor["data"][0]["et_year"]

                # ----------- Data structure 6 - EnviroMonitor
                if (
                    sensor["sensor_type"] in SENSOR_TYPE_VUE_AND_VANTAGE_PRO
                    and sensor["data_structure_type"] == 6
                ):
                    tx_id = sensor["data"][0].get("tx_id", 1)
                    outdata.setdefault(tx_id, {})
                    outdata[tx_id][DataKey.SENSOR_TYPE] = sensor["sensor_type"]
                    outdata[tx_id][DataKey.DATA_STRUCTURE] = sensor[
                        "data_structure_type"
                    ]
                    outdata[tx_id][DataKey.TIMESTAMP] = sensor["data"][0]["ts"]
                    outdata[tx_id][DataKey.TEMP_OUT] = sensor["data"][0]["temp_out"]
                    outdata[tx_id][DataKey.BAR_SEA_LEVEL] = sensor["data"][0]["bar"]
                    if (xx := sensor["data"][0].get("bar_trend", 0)) is not None:
                        xx = xx / 1000
                    outdata[tx_id][DataKey.BAR_TREND] = xx
                    outdata[tx_id][DataKey.HUM_OUT] = sensor["data"][0]["hum_out"]
                    outdata[tx_id][DataKey.WIND_MPH] = sensor["data"][0]["wind_speed"]
                    outdata[tx_id][DataKey.WIND_GUST_MPH] = sensor["data"][0][
                        "wind_gust_10_min"
                    ]
                    outdata[tx_id][DataKey.WIND_DIR] = sensor["data"][0]["wind_dir"]
                    outdata[tx_id][DataKey.DEWPOINT] = sensor["data"][0]["dew_point"]
                    outdata[tx_id][DataKey.HEAT_INDEX] = sensor["data"][0]["heat_index"]
                    outdata[tx_id][DataKey.WIND_CHILL] = sensor["data"][0]["wind_chill"]
                    outdata[tx_id][DataKey.RAIN_DAY] = sensor["data"][0].get(
                        "rain_day_in"
                    )
                    if (xx := sensor["data"][0].get("rain_storm_in", 0.0)) is None:
                        xx = 0.0
                    outdata[tx_id][DataKey.RAIN_STORM] = xx
                    outdata[tx_id][DataKey.RAIN_STORM_START] = sensor["data"][0].get(
                        "rain_storm_start_date"
                    )
                    outdata[tx_id][DataKey.RAIN_RATE] = sensor["data"][0][
                        "rain_rate_in"
                    ]
                    outdata[tx_id][DataKey.SOLAR_RADIATION] = sensor["data"][0][
                        "solar_rad"
                    ]
                    outdata[tx_id][DataKey.UV_INDEX] = sensor["data"][0]["uv"]
                    outdata[tx_id][DataKey.ET_DAY] = sensor["data"][0]["et_day"]
                    outdata[tx_id][DataKey.THSW_INDEX] = sensor["data"][0]["thsw_index"]
                    outdata[tx_id][DataKey.WET_BULB] = sensor["data"][0]["wet_bulb"]

                if (
                    sensor["sensor_type"] in SENSOR_TYPE_VUE_AND_VANTAGE_PRO
                    or sensor["sensor_type"] in [55]
                ) and sensor["data_structure_type"] == 23:
                    tx_id = sensor["data"][0]["tx_id"]
                    outdata.setdefault(tx_id, {})
                    outdata[tx_id][DataKey.SENSOR_TYPE] = sensor["sensor_type"]
                    outdata[tx_id][DataKey.DATA_STRUCTURE] = sensor[
                        "data_structure_type"
                    ]
                    outdata[tx_id][DataKey.TIMESTAMP] = sensor["data"][0]["ts"]
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
                    outdata[tx_id][DataKey.RAIN_DAY] = sensor["data"][0].get(
                        "rainfall_day_in", 0.0
                    )
                    if (
                        xx := sensor["data"][0].get("rain_storm_current_in", 0.0)
                    ) is None:
                        xx = 0.0
                    outdata[tx_id][DataKey.RAIN_STORM] = xx
                    outdata[tx_id][DataKey.RAIN_STORM_START] = sensor["data"][0].get(
                        "rain_storm_current_start_at"
                    )
                    if (xx := sensor["data"][0].get("rain_storm_last_in", 0.0)) is None:
                        xx = 0.0
                    outdata[tx_id][DataKey.RAIN_STORM_LAST] = xx
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
                    outdata[tx_id][DataKey.UV_INDEX] = sensor["data"][0]["uv_index"]
                    outdata[tx_id][DataKey.ET_DAY] = sensor["data"][0]["et_day"]
                    outdata[tx_id][DataKey.ET_MONTH] = sensor["data"][0]["et_month"]
                    outdata[tx_id][DataKey.ET_YEAR] = sensor["data"][0]["et_year"]

                if sensor["sensor_type"] == 56 and sensor["data_structure_type"] == 12:
                    tx_id = sensor["data"][0]["tx_id"]
                    outdata.setdefault(tx_id, {})
                    outdata[tx_id][DataKey.SENSOR_TYPE] = sensor["sensor_type"]
                    outdata[tx_id][DataKey.DATA_STRUCTURE] = sensor[
                        "data_structure_type"
                    ]
                    outdata[tx_id][DataKey.TIMESTAMP] = sensor["data"][0]["ts"]
                    for numb in range(1, 4 + 1):
                        outdata[tx_id][f"{DataKey.TEMP}_{numb}"] = sensor["data"][0][
                            f"temp_{numb}"
                        ]
                    for numb in range(1, 4 + 1):
                        outdata[tx_id][f"{DataKey.MOIST_SOIL}_{numb}"] = sensor["data"][
                            0
                        ][f"moist_soil_{numb}"]
                    for numb in range(1, 2 + 1):
                        outdata[tx_id][f"{DataKey.WET_LEAF}_{numb}"] = sensor["data"][
                            0
                        ][f"wet_leaf_{numb}"]

                if sensor["sensor_type"] == 56 and sensor["data_structure_type"] == 25:
                    tx_id = sensor["data"][0]["tx_id"]
                    outdata.setdefault(tx_id, {})
                    outdata[tx_id][DataKey.SENSOR_TYPE] = sensor["sensor_type"]
                    outdata[tx_id][DataKey.DATA_STRUCTURE] = sensor[
                        "data_structure_type"
                    ]
                    outdata[tx_id][DataKey.TIMESTAMP] = sensor["data"][0]["ts"]
                    for numb in range(1, 4 + 1):
                        outdata[tx_id][f"{DataKey.TEMP}_{numb}"] = sensor["data"][0][
                            f"temp_{numb}"
                        ]
                    for numb in range(1, 4 + 1):
                        outdata[tx_id][f"{DataKey.MOIST_SOIL}_{numb}"] = sensor["data"][
                            0
                        ][f"moist_soil_{numb}"]
                    for numb in range(1, 2 + 1):
                        outdata[tx_id][f"{DataKey.WET_LEAF}_{numb}"] = sensor["data"][
                            0
                        ][f"wet_leaf_{numb}"]
                    outdata[tx_id][DataKey.TRANS_BATTERY_FLAG] = sensor["data"][0][
                        "trans_battery_flag"
                    ]

                if sensor["sensor_type"] == 365 and sensor["data_structure_type"] == 21:
                    tx_id = primary_tx_id
                    outdata[tx_id][DataKey.TEMP_IN] = sensor["data"][0]["temp_in"]
                    outdata[tx_id][DataKey.HUM_IN] = sensor["data"][0]["hum_in"]
                if sensor["sensor_type"] == 243 and sensor["data_structure_type"] == 12:
                    tx_id = primary_tx_id
                    outdata[tx_id][DataKey.TEMP_IN] = sensor["data"][0]["temp_in"]
                    outdata[tx_id][DataKey.HUM_IN] = sensor["data"][0]["hum_in"]
                if sensor["sensor_type"] == 242 and sensor["data_structure_type"] == 12:
                    tx_id = primary_tx_id
                    outdata[tx_id][DataKey.BAR_SEA_LEVEL] = sensor["data"][0][
                        "bar_sea_level"
                    ]
                    outdata[tx_id][DataKey.BAR_TREND] = sensor["data"][0]["bar_trend"]
                if sensor["sensor_type"] == 242 and sensor["data_structure_type"] == 19:
                    tx_id = primary_tx_id
                    outdata[tx_id][DataKey.BAR_SEA_LEVEL] = sensor["data"][0][
                        "bar_sea_level"
                    ]
                    outdata[tx_id][DataKey.BAR_TREND] = sensor["data"][0]["bar_trend"]

                if (
                    sensor["sensor_type"] in SENSOR_TYPE_AIRLINK
                    and sensor["data_structure_type"] == 16
                ):
                    tx_id = primary_tx_id
                    tx_id = sensor["lsid"]
                    outdata.setdefault(tx_id, {})
                    outdata[tx_id][DataKey.SENSOR_TYPE] = sensor["sensor_type"]
                    outdata[tx_id][DataKey.DATA_STRUCTURE] = sensor[
                        "data_structure_type"
                    ]
                    outdata[tx_id][DataKey.TIMESTAMP] = sensor["data"][0]["ts"]
                    outdata[tx_id][DataKey.TEMP] = sensor["data"][0]["temp"]
                    outdata[tx_id][DataKey.HUM] = sensor["data"][0]["hum"]
                    outdata[tx_id][DataKey.DEWPOINT] = sensor["data"][0]["dew_point"]
                    outdata[tx_id][DataKey.HEAT_INDEX] = sensor["data"][0]["heat_index"]
                    outdata[tx_id][DataKey.WET_BULB] = sensor["data"][0]["wet_bulb"]
                    outdata[tx_id][DataKey.PM_1] = sensor["data"][0]["pm_1"]
                    outdata[tx_id][DataKey.PM_2P5] = sensor["data"][0]["pm_2p5"]
                    outdata[tx_id][DataKey.PM_2P5_24H] = sensor["data"][0][
                        "pm_2p5_24_hour"
                    ]
                    outdata[tx_id][DataKey.PM_10] = sensor["data"][0]["pm_10"]
                    outdata[tx_id][DataKey.PM_10_24H] = sensor["data"][0][
                        "pm_10_24_hour"
                    ]
                    outdata[tx_id][DataKey.AQI_VAL] = sensor["data"][0]["aqi_val"]
                    outdata[tx_id][DataKey.AQI_NOWCAST_VAL] = sensor["data"][0][
                        "aqi_nowcast_val"
                    ]

            # Test data can be injected here

            # tx_id = primary_tx_id
            # outdata[tx_id][DataKey.PM_1] = 10
            # outdata[tx_id][DataKey.PM_2P5] = 20
            # outdata[tx_id][DataKey.PM_10] = 50
            # outdata[tx_id][DataKey.AQI_VAL] = 101
            # outdata[tx_id][DataKey.AQI_NOWCAST_VAL] = 102

        return outdata

    async def async_fetch():
        api = entry.runtime_data.api
        try:
            async with asyncio.timeout(10):
                json_data = await api.get_data()
                entry.runtime_data.current = json_data
                return _preprocess(json_data)
        except ClientResponseError as exc:
            _LOGGER.warning("API fetch failed. Status: %s, - %s", exc.code, exc.message)
            raise UpdateFailed(exc) from exc

    entry.runtime_data.coordinator = DataUpdateCoordinator(
        hass,
        logging.getLogger(__name__),
        name=DOMAIN,
        update_method=async_fetch,
        update_interval=timedelta(minutes=5),
    )
    await entry.runtime_data.coordinator.async_refresh()
    return entry.runtime_data.coordinator


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


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove config entry from a device."""
    api_data = config_entry.runtime_data.coordinator.data
    return not any(
        identifier
        for _, identifier in device_entry.identifiers
        if identifier in api_data
    )

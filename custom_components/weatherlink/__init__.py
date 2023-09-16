"""The Weatherlink integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from aiohttp import ClientResponseError
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .config_flow import API_V1, API_V2
from .const import DOMAIN
from .pyweatherlink import WLHub, WLHubV2

PLATFORMS = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Weatherlink from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}
    if entry.data["api_version"] == API_V1:
        hass.data[DOMAIN][entry.entry_id]["api"] = WLHub(
            websession=async_get_clientsession(hass),
            username=entry.data["username"],
            password=entry.data["password"],
            apitoken=entry.data["apitoken"],
        )

    if entry.data["api_version"] == API_V2:
        hass.data[DOMAIN][entry.entry_id]["api"] = WLHubV2(
            websession=async_get_clientsession(hass),
            station_id=entry.data["station_id"],
            api_key_v2=entry.data["api_key_v2"],
            api_secret=entry.data["api_secret"],
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
        if entry.data["api_version"] == API_V1:
            outdata["DID"] = indata["davis_current_observation"].get("DID")
            outdata["station_name"] = indata["davis_current_observation"].get(
                "station_name"
            )
            outdata["temp_out"] = indata.get("temp_f")
            outdata["temp_in"] = indata["davis_current_observation"].get("temp_in_f")
            outdata["hum_in"] = indata["davis_current_observation"].get(
                "relative_humidity_in"
            )
            outdata["hum_out"] = indata.get("relative_humidity")
            outdata["bar_sea_level"] = indata.get("pressure_in")
            outdata["wind_mph"] = indata.get("wind_mph")
            outdata["wind_dir"] = indata.get("wind_degrees")
            outdata["dewpoint"] = indata.get("dewpoint_f")
            outdata["rain_day"] = indata["davis_current_observation"].get("rain_day_in")
            outdata["rain_rate"] = indata["davis_current_observation"].get(
                "rain_rate_in_per_hr"
            )
            outdata["rain_month"] = indata["davis_current_observation"].get(
                "rain_month_in"
            )
            outdata["rain_year"] = indata["davis_current_observation"].get(
                "rain_year_in"
            )
        if entry.data["api_version"] == API_V2:
            outdata["station_id_uuid"] = indata["station_id_uuid"]
            for sensor in indata["sensors"]:
                if sensor["sensor_type"] == 37 and sensor["data_structure_type"] == 10:
                    outdata["temp_out"] = sensor["data"][0]["temp"]
                    outdata["hum_out"] = sensor["data"][0]["hum"]
                    outdata["wind_mph"] = sensor["data"][0]["wind_speed_last"]
                    outdata["wind_dir"] = sensor["data"][0]["wind_dir_last"]
                    outdata["dewpoint"] = sensor["data"][0]["dew_point"]
                    outdata["rain_day"] = float(sensor["data"][0]["rainfall_daily_in"])
                    outdata["rain_rate"] = sensor["data"][0]["rain_rate_last_in"]
                    outdata["rain_month"] = sensor["data"][0]["rainfall_monthly_in"]
                    outdata["rain_year"] = sensor["data"][0]["rainfall_year_in"]
                if sensor["sensor_type"] == 37 and sensor["data_structure_type"] == 23:
                    outdata["temp_out"] = sensor["data"][0]["temp"]
                    outdata["hum_out"] = sensor["data"][0]["hum"]
                    outdata["wind_mph"] = sensor["data"][0]["wind_speed_last"]
                    outdata["wind_dir"] = sensor["data"][0]["wind_dir_last"]
                    outdata["dewpoint"] = sensor["data"][0]["dew_point"]
                    outdata["rain_day"] = float(sensor["data"][0]["rainfall_day_in"])
                    outdata["rain_rate"] = sensor["data"][0]["rain_rate_last_in"]
                    outdata["rain_month"] = sensor["data"][0]["rainfall_month_in"]
                    outdata["rain_year"] = sensor["data"][0]["rainfall_year_in"]
                if sensor["sensor_type"] == 365 and sensor["data_structure_type"] == 21:
                    outdata["temp_in"] = sensor["data"][0]["temp_in"]
                    outdata["hum_in"] = sensor["data"][0]["hum_in"]
                if sensor["sensor_type"] == 243 and sensor["data_structure_type"] == 12:
                    outdata["temp_in"] = sensor["data"][0]["temp_in"]
                    outdata["hum_in"] = sensor["data"][0]["hum_in"]
                if sensor["sensor_type"] == 242 and sensor["data_structure_type"] == 12:
                    outdata["bar_sea_level"] = sensor["data"][0]["bar_sea_level"]
                    outdata["bar_trend"] = sensor["data"][0]["bar_trend"]
                if sensor["sensor_type"] == 242 and sensor["data_structure_type"] == 19:
                    outdata["bar_sea_level"] = sensor["data"][0]["bar_sea_level"]
                    outdata["bar_trend"] = sensor["data"][0]["bar_trend"]

        return outdata

    async def async_fetch():
        api = hass.data[DOMAIN][entry.entry_id]["api"]
        try:
            async with async_timeout.timeout(10):
                res = await api.request("GET")
                json_data = await res.json()
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

        new_data["api_version"] = API_V1

        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=new_data)

    _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True

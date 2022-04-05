"""The Weatherlink integration."""
from __future__ import annotations

import logging
from datetime import timedelta

import async_timeout
from aiohttp import ClientResponseError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .pyweatherlink import WLHub

PLATFORMS = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Weatherlink from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}
    hass.data[DOMAIN][entry.entry_id]["api"] = WLHub(
        websession=async_get_clientsession(hass),
        username=entry.data["username"],
        password=entry.data["password"],
        apitoken=entry.data["apitoken"],
    )

    coordinator = await get_coordinator(hass, entry)
    if not coordinator.last_update_success:
        await coordinator.async_config_entry_first_refresh()
    _LOGGER.debug("First data: %s", coordinator.data)

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def get_coordinator(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> DataUpdateCoordinator:
    """Get the data update coordinator."""
    if "coordinator" in hass.data[DOMAIN][entry.entry_id]:
        return hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async def async_fetch():
        api = hass.data[DOMAIN][entry.entry_id]["api"]
        try:
            async with async_timeout.timeout(10):
                res = await api.request("GET")
                return await res.json()
        except ClientResponseError as exc:
            _LOGGER.warning("API fetch failed. Status: %s, - %s", exc.code, exc.message)

    hass.data[DOMAIN][entry.entry_id]["coordinator"] = DataUpdateCoordinator(
        hass,
        logging.getLogger(__name__),
        name=DOMAIN,
        update_method=async_fetch,
        update_interval=timedelta(minutes=5),
    )
    await hass.data[DOMAIN][entry.entry_id]["coordinator"].async_refresh()
    return hass.data[DOMAIN][entry.entry_id]["coordinator"]

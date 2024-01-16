"""Diagnostics support for Weatherlink."""
from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_API_KEY_V2,
    CONF_API_SECRET,
    CONF_API_TOKEN,
    CONF_API_VERSION,
    DOMAIN,
    ApiVersion,
)

TO_REDACT = {
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_API_TOKEN,
    CONF_API_SECRET,
    CONF_API_KEY_V2,
    "user_email",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]
    station_data = hass.data[DOMAIN][config_entry.entry_id].get("station_data", {})
    current = hass.data[DOMAIN][config_entry.entry_id]["current"]
    sensor_metadata = hass.data[DOMAIN][config_entry.entry_id]["sensors_metadata"]

    sensor_data = {}
    if config_entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
        sensor_data = await hass.data[DOMAIN][config_entry.entry_id][
            "api"
        ].get_all_sensors()

    diagnostics_data = {
        "info": async_redact_data(config_entry.data, TO_REDACT),
        "station_data": async_redact_data(station_data, TO_REDACT),
        "all_sensor_data": async_redact_data(sensor_data, TO_REDACT),
        "sensor_metadata": async_redact_data(sensor_metadata, TO_REDACT),
        "current_data": async_redact_data(current, TO_REDACT),
        "data": async_redact_data(coordinator.data, TO_REDACT),
    }

    return diagnostics_data

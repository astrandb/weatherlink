"""Diagnostics support for Weatherlink."""

from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_API_KEY_V2,
    CONF_API_SECRET,
    CONF_API_TOKEN,
    CONF_API_VERSION,
    ApiVersion,
)

from . import WLConfigEntry

TO_REDACT = {
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_API_TOKEN,
    CONF_API_SECRET,
    CONF_API_KEY_V2,
    "user_email",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: WLConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""
    coordinator: DataUpdateCoordinator = entry.runtime_data.coordinator
    station_data = entry.runtime_data.station_data
    current = entry.runtime_data.current
    sensor_metadata = entry.runtime_data.sensors_metadata

    sensor_data = {}
    if entry.data[CONF_API_VERSION] == ApiVersion.API_V2:
        sensor_data = await entry.runtime_data.api.get_all_sensors()

    diagnostics_data = {
        "info": async_redact_data(entry.data, TO_REDACT),
        "station_data": async_redact_data(station_data, TO_REDACT),
        "all_sensor_data": async_redact_data(sensor_data, TO_REDACT),
        "sensor_metadata": async_redact_data(sensor_metadata, TO_REDACT),
        "current_data": async_redact_data(current, TO_REDACT),
        "data": async_redact_data(coordinator.data, TO_REDACT),
    }

    return diagnostics_data

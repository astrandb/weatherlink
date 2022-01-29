"""Diagnostics support for Weatherlink."""
from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_API_TOKEN, DOMAIN

TO_REDACT = {
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_API_TOKEN,
    "apitoken",
    "DID",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    diagnostics_data = {
        "info": async_redact_data(config_entry.data, TO_REDACT),
        "data": async_redact_data(coordinator.data, TO_REDACT),
    }

    return diagnostics_data

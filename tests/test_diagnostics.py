"""Tests for the diagnostics data provided by the weatherlink integration."""

from http import HTTPStatus
from typing import cast

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator
from syrupy import SnapshotAssertion

from custom_components.weatherlink.const import DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.json import JsonObjectType

from .const import ENTRY_ID, MOCK_CONFIG_V2


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
    bypass_get_data,
    bypass_get_station,
    bypass_get_all_sensors,
) -> None:
    """Test diagnostics."""
    entry = MockConfigEntry(
        domain=DOMAIN, version=2, data=MOCK_CONFIG_V2, entry_id=ENTRY_ID
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert await get_diagnostics_for_config_entry(hass, hass_client, entry) == snapshot


# The following 2 functions are copied from https://github.com/home-assistant/core/blob/dev/tests/components/diagnostics/__init__.py
async def _get_diagnostics_for_config_entry(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    config_entry: ConfigEntry,
) -> JsonObjectType:
    """Return the diagnostics config entry for the specified domain."""
    assert await async_setup_component(hass, "diagnostics", {})
    await hass.async_block_till_done()

    client = await hass_client()
    response = await client.get(
        f"/api/diagnostics/config_entry/{config_entry.entry_id}"
    )
    assert response.status == HTTPStatus.OK
    return cast(JsonObjectType, await response.json())


async def get_diagnostics_for_config_entry(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    config_entry: ConfigEntry,
) -> JsonObjectType:
    """Return the diagnostics config entry for the specified domain."""
    data = await _get_diagnostics_for_config_entry(hass, hass_client, config_entry)
    return cast(JsonObjectType, data["data"])

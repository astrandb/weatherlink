"""Provide tests for weatherlink sensors."""

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy import SnapshotAssertion

from custom_components.weatherlink.const import DOMAIN
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import setup_integration
from .const import ENTRY_ID, MOCK_CONFIG_V2


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_binary_sensor(
    hass: HomeAssistant,
    bypass_get_data,
    bypass_get_station,
    bypass_get_all_sensors,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test sensor states."""

    mock_config_entry = MockConfigEntry(
        domain=DOMAIN, version=2, data=MOCK_CONFIG_V2, entry_id=ENTRY_ID
    )

    with patch("custom_components.weatherlink.PLATFORMS", [Platform.BINARY_SENSOR]):
        await setup_integration(hass, mock_config_entry)

    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


# @pytest.mark.parametrize(
#     "data_file_name", ["station_166.json", "station_135.json", "station_88.json"]
# )
# @pytest.mark.usefixtures("entity_registry_enabled_by_default")
# async def test_sensor_additional_stations(
#     hass: HomeAssistant,
#     bypass_get_data,
#     snapshot: SnapshotAssertion,
#     entity_registry: er.EntityRegistry,
# ) -> None:
#     """Test states for additional stations."""

#     mock_config_entry = MockConfigEntry(
#         domain=DOMAIN, data=MOCK_CONFIG, entry_id=ENTRY_ID
#     )

#     with patch("custom_components.viva.PLATFORMS", [Platform.SENSOR]):
#         await setup_integration(hass, mock_config_entry)

#     await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)

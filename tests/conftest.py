"""pytest fixtures."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import load_fixture
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from syrupy import SnapshotAssertion

from homeassistant.core import HomeAssistant
from homeassistant.util.json import json_loads

# pylint: disable=redefined-outer-name


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    return


@pytest.fixture
def data_file_name() -> str:
    """Filename for data fixture."""
    return "strp81.json"


@pytest.fixture(name="load_default_station")
def load_default_station_fixture(data_file_name: str) -> dict:
    """Load data for default station."""
    return json_loads(load_fixture(data_file_name))
    # data = json_loads(load_fixture(data_file_name))
    # result = data["GetSingleStationResult"]
    # res = {}
    # for sample in data["GetSingleStationResult"]["Samples"]:
    #     res[sample["Name"]] = sample
    # result["Samples"] = res
    # return result


@pytest.fixture(name="load_all_stations")
def load_all_stations_fixture() -> dict:
    """Load data for all stations."""
    return json_loads(load_fixture("all_stations.json"))


@pytest.fixture(name="load_default_data")
def load_default_data_fixture() -> dict:
    """Load data for a station."""
    return json_loads(load_fixture("strp81_current.json"))


@pytest.fixture(name="load_sensors")
def load_sensors_fixture() -> dict:
    """Load data for all stations."""
    return json_loads(load_fixture("sensors.json"))


#     data = json_loads(load_fixture("all_stations.json"))
#     result = data["GetStationsResult"]["Stations"]
#     return [Station(station_data) for station_data in result]


@pytest.fixture(name="bypass_get_data")
def bypass_get_data_fixture(
    hass: HomeAssistant,
    load_default_data: dict,
):
    """Skip calls to get data from API."""
    with patch(
        "custom_components.weatherlink.pyweatherlink.WLHubV2.get_data",
        return_value=load_default_data,
    ):
        yield


@pytest.fixture(name="bypass_get_data_api_1")
def bypass_get_data_api_1_fixture(
    hass: HomeAssistant,
):
    """Skip calls to get data from API."""
    with patch(
        "custom_components.weatherlink.pyweatherlink.WLHub.get_data",
        return_value=json_loads(load_fixture("fryksasm_api1.json")),
    ):
        yield


@pytest.fixture(name="bypass_get_station")
def bypass_get_station_fixture(
    hass: HomeAssistant,
    load_default_station: dict,
):
    """Skip calls to get data from API."""
    with patch(
        "custom_components.weatherlink.pyweatherlink.WLHubV2.get_station",
        return_value=load_default_station,
    ):
        yield


@pytest.fixture(name="bypass_get_all_sensors")
def bypass_get_all_sensors_fixture(
    hass: HomeAssistant,
    load_sensors: dict,
):
    """Skip calls to get data from API."""
    with patch(
        "custom_components.weatherlink.pyweatherlink.WLHubV2.get_all_sensors",
        return_value=load_sensors,
    ):
        yield


@pytest.fixture(name="bypass_get_all_stations")
def bypass_get_all_stations_fixture(
    hass: HomeAssistant,
    load_all_stations: dict,
):
    """Skip calls to get data from API."""
    with patch(
        "custom_components.weatherlink.pyweatherlink.WLHubV2.get_all_stations",
        return_value=load_all_stations,
    ):
        yield


@pytest.fixture
def entity_registry_enabled_by_default() -> Generator[None]:
    """Test fixture that ensures all entities are enabled in the registry."""
    with patch(
        "homeassistant.helpers.entity.Entity.entity_registry_enabled_default",
        return_value=True,
    ):
        yield


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return snapshot assertion fixture with the Home Assistant extension."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture
def mock_api() -> Generator[MagicMock]:
    """Mock api."""
    with (
        patch(
            "custom_components.weatherlink.pyweatherlink.WLHubV2.get_data"
        ) as mock_api,
    ):
        yield mock_api

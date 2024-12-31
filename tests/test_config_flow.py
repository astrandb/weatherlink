"""Tests for config flow."""

from unittest.mock import patch

import pytest

from custom_components.weatherlink.config_flow import CannotConnect, InvalidAuth
from custom_components.weatherlink.const import (
    DOMAIN,
    CONF_API_KEY_V2,
    CONF_API_SECRET,
    CONF_API_TOKEN,
    CONF_STATION_ID,
)
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType


@pytest.fixture(autouse=True)
def bypass_setup_fixture():
    """Prevent setup."""
    with patch(
        "custom_components.weatherlink.async_setup_entry",
        return_value=True,
    ):
        yield


async def test_succesful_flow(
    hass: HomeAssistant, bypass_get_all_stations, bypass_get_station
) -> None:
    """Test that we get the form and create the entry."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"api_version": "api_v2"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user_2"

    with patch(
        "custom_components.weatherlink.WLHubV2.authenticate",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY_V2: "123", CONF_API_SECRET: "456"}
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user_3"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_STATION_ID: "167531"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    ("exc", "key"),
    [
        (CannotConnect, "cannot_connect"),
        (InvalidAuth, "invalid_auth"),
        (Exception, "unknown"),
    ],
    ids=["cannot_connect", "invalid_auth", "other_exception"],
)
async def test_failed_flow_api_v2_step_2(
    hass: HomeAssistant, bypass_get_all_stations, bypass_get_station, exc, key
) -> None:
    """Test failing flow step 2."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"api_version": "api_v2"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user_2"

    with patch(
        "custom_components.weatherlink.config_flow.validate_input_v2", side_effect=exc
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY_V2: "123", CONF_API_SECRET: "456"}
        )


@pytest.mark.parametrize(
    ("exc", "key"),
    [
        (CannotConnect, "cannot_connect"),
        (InvalidAuth, "invalid_auth"),
        (Exception, "unknown"),
    ],
    ids=["cannot_connect", "invalid_auth", "other_exception"],
)
async def test_failed_flow_api_v2_step_3(
    hass: HomeAssistant, bypass_get_all_stations, bypass_get_station, exc, key
) -> None:
    """Test failing flow step 3."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"api_version": "api_v2"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user_2"

    with patch(
        "custom_components.weatherlink.config_flow.validate_input_v2", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY_V2: "123", CONF_API_SECRET: "456"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user_3"

    with patch(
        "custom_components.weatherlink.config_flow.validate_input_v2b",
        side_effect=exc,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_STATION_ID: "167531"},
        )

    assert result["errors"] == {"base": key}


async def test_auth_error(
    hass: HomeAssistant, bypass_get_all_stations, bypass_get_station
) -> None:
    """Test auth error."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"api_version": "api_v2"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user_2"

    with patch(
        "custom_components.weatherlink.WLHubV2.authenticate",
        return_value=False,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY_V2: "123", CONF_API_SECRET: "456"}
        )

    assert result["errors"] == {"base": "invalid_auth"}


async def test_succesful_flow_api_v1(
    hass: HomeAssistant, bypass_get_data_api_1
) -> None:
    """Test that we get the form and create the entry using api v1."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"api_version": "api_v1"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user_1"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: "username",
            CONF_PASSWORD: "password",
            CONF_API_TOKEN: "token",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_auth_error_api_v1(
    hass: HomeAssistant,
    bypass_get_data_api_1,
) -> None:
    """Test auth error."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"api_version": "api_v1"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user_1"

    with patch(
        "custom_components.weatherlink.WLHub.authenticate",
        return_value=False,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "username",
                CONF_PASSWORD: "password",
                CONF_API_TOKEN: "token",
            },
        )

    assert result["errors"] == {"base": "invalid_auth"}


@pytest.mark.parametrize(
    ("exc", "key"),
    [
        (CannotConnect, "cannot_connect"),
        (InvalidAuth, "invalid_auth"),
        (Exception, "unknown"),
    ],
    ids=["cannot_connect", "invalid_auth", "other_exception"],
)
async def test_failed_flow_api_1(
    hass: HomeAssistant, bypass_get_data_api_1, exc, key
) -> None:
    """Test failing flows."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"api_version": "api_v1"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user_1"

    with patch(
        "custom_components.weatherlink.config_flow.validate_input", side_effect=exc
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "username",
                CONF_PASSWORD: "password",
                CONF_API_TOKEN: "token",
            },
        )

    assert result["errors"] == {"base": key}

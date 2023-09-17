"""Config flow for Weatherlink integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
)

from .const import (
    CONF_API_KEY_V2,
    CONF_API_SECRET,
    CONF_API_TOKEN,
    CONF_API_VERSION,
    CONF_STATION_ID,
    DOMAIN,
)
from .pyweatherlink import WLHub, WLHubV2

_LOGGER = logging.getLogger(__name__)

API_V1 = "api_v1"
API_V2 = "api_v2"
API_VERSIONS = [API_V1, API_V2]

STEP_USER_APIVER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_VERSION, default=API_V2): SelectSelector(
            SelectSelectorConfig(options=API_VERSIONS, translation_key="set_api_ver")
        ),
    }
)

STEP_USER_DATA_SCHEMA_V1 = vol.Schema(
    {
        vol.Required("username"): TextSelector(),
        vol.Required("password"): str,
        vol.Required(CONF_API_TOKEN): str,
    }
)

STEP_USER_DATA_SCHEMA_V2_A = vol.Schema(
    {
        vol.Required(CONF_API_KEY_V2): TextSelector(),
        vol.Required(CONF_API_SECRET): TextSelector(),
    }
)

STEP_USER_DATA_SCHEMA_V2_B = vol.Schema(
    {
        vol.Required(CONF_STATION_ID): TextSelector(),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA_V1 with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )

    websession = async_get_clientsession(hass)
    hub = WLHub(
        username=data["username"],
        password=data["password"],
        apitoken=data[CONF_API_TOKEN],
        websession=websession,
    )

    if not await hub.authenticate(
        data["username"], data["password"], data[CONF_API_TOKEN]
    ):
        raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    data = await hub.get_data()
    station_name = data["davis_current_observation"]["station_name"]
    did = data["davis_current_observation"]["DID"]

    return {"title": station_name, "did": did}


async def validate_input_v2(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA_V2 with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    websession = async_get_clientsession(hass)
    hub = WLHubV2(
        station_id=data.get(CONF_STATION_ID),
        api_key_v2=data[CONF_API_KEY_V2],
        api_secret=data[CONF_API_SECRET],
        websession=websession,
    )

    if not await hub.authenticate(
        data.get(CONF_STATION_ID), data[CONF_API_KEY_V2], data[CONF_API_SECRET]
    ):
        raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    data = await hub.get_station()
    _LOGGER.debug("Station data: %s", data)
    station_name = data["stations"][0]["station_name"]
    # did = data["davis_current_observation"]["DID"]

    # return {"title": station_name, "did": did}
    return {"title": station_name}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Weatherlink."""

    VERSION = 2

    user_data_2 = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        data_schema = STEP_USER_APIVER_SCHEMA
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=data_schema)

        if user_input[CONF_API_VERSION] == API_V1:
            return await self.async_step_user_1()
        if user_input[CONF_API_VERSION] == API_V2:
            return await self.async_step_user_2()

    async def async_step_user_1(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the step for API_V1."""
        data_schema = STEP_USER_DATA_SCHEMA_V1
        if user_input is None:
            return self.async_show_form(step_id="user_1", data_schema=data_schema)

        errors = {}

        user_input[CONF_API_VERSION] = API_V1
        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            await self.async_set_unique_id(user_input["username"])
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user_1", data_schema=data_schema, errors=errors
        )

    async def async_step_user_2(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the first step for API_V2."""
        data_schema = STEP_USER_DATA_SCHEMA_V2_A
        if user_input is None:
            return self.async_show_form(step_id="user_2", data_schema=data_schema)

        errors = {}

        user_input[CONF_API_VERSION] = API_V2
        try:
            await validate_input_v2(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            self.user_data_2 = user_input
            return await self.async_step_user_3()

        return self.async_show_form(
            step_id="user_2", data_schema=data_schema, errors=errors
        )

    async def async_step_user_3(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the second step for API_V2."""
        data_schema = STEP_USER_DATA_SCHEMA_V2_B
        websession = async_get_clientsession(self.hass)
        _api = WLHubV2(
            api_key_v2=self.user_data_2[CONF_API_KEY_V2],
            api_secret=self.user_data_2[CONF_API_SECRET],
            websession=websession,
        )
        station_list_raw = await _api.get_all_stations()
        station_list = [
            SelectOptionDict(value=str(stn[CONF_STATION_ID]), label=stn["station_name"])
            for stn in (station_list_raw["stations"])
        ]

        if user_input is None:
            return self.async_show_form(
                step_id="user_3",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_STATION_ID): SelectSelector(
                            SelectSelectorConfig(options=station_list)
                        ),
                    }
                ),
            )
        errors = {}

        user_input[CONF_API_VERSION] = API_V2
        user_input[CONF_API_KEY_V2] = self.user_data_2[CONF_API_KEY_V2]
        user_input[CONF_API_SECRET] = self.user_data_2[CONF_API_SECRET]

        try:
            info = await validate_input_v2(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            await self.async_set_unique_id(user_input[CONF_STATION_ID])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user_3", data_schema=data_schema, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

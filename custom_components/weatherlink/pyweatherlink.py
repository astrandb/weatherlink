"""Library for Weatherlink.

Move to pypi.org when stable
"""
from dataclasses import dataclass
import logging
import urllib.parse

from aiohttp import ClientResponse, ClientResponseError, ClientSession

from .const import VERSION

API_V1_URL = "https://api.weatherlink.com/v1/NoaaExt.json"
API_V2_URL = "https://api.weatherlink.com/v2/"


_LOGGER = logging.getLogger(__name__)


class WLHub:
    """Class to get data from Wetherlink API v1."""

    def __init__(
        self, username: str, password: str, apitoken: str, websession: ClientSession
    ) -> None:
        """Initialize."""
        self.username = username
        self.password = password
        self.apitoken = apitoken
        self.websession = websession

    async def authenticate(self, username: str, password: str, apitoken: str) -> bool:
        """Test if we can authenticate with the host."""
        return True

    async def request(self, method, **kwargs) -> ClientResponse:
        """Make a request."""
        headers = kwargs.get("headers")

        if headers is None:
            headers = {}
        else:
            headers = dict(headers)
            kwargs.pop("headers")

        params = {
            "user": self.username,
            "pass": self.password,
            "apiToken": self.apitoken,
        }
        params_enc = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)

        res = await self.websession.request(
            method,
            f"{API_V1_URL}?{params_enc}",
            **kwargs,
            headers=headers,
        )
        res.raise_for_status()
        return res

    async def get_data(self):
        """Get data from api."""
        try:
            res = await self.request("GET")
            return await res.json()
        except ClientResponseError as exc:
            _LOGGER.error(
                "API get_data failed. Status: %s, - %s", exc.code, exc.message
            )


class WLHubV2:
    """Class to get data from Wetherlink API v2."""

    def __init__(
        self,
        station_id: str,
        api_key_v2: str,
        api_secret: str,
        websession: ClientSession,
    ) -> None:
        """Initialize."""
        self.station_id = station_id
        self.api_key_v2 = api_key_v2
        self.api_secret = api_secret
        self.websession = websession

    async def authenticate(
        self, station_id: str, api_key_v2: str, api_secret: str
    ) -> bool:
        """Test if we can authenticate with the host."""
        return True

    async def request(self, method, endpoint="current/", **kwargs) -> ClientResponse:
        """Make a request."""
        headers = kwargs.get("headers")

        if headers is None:
            headers = {}
        else:
            headers = dict(headers)
            kwargs.pop("headers")

        headers["x-api-secret"] = self.api_secret
        headers["User-Agent"] = f"Weatherlink for Home Assistant/{VERSION}"
        params = {
            # "station_id": self.station_id,
            "api-key": self.api_key_v2,
            # "api_secret": self.api_secret,
        }
        params_enc = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)

        res = await self.websession.request(
            method,
            f"{API_V2_URL}{endpoint}{self.station_id}?{params_enc}",
            **kwargs,
            headers=headers,
        )
        res.raise_for_status()
        return res

    async def get_data(self):
        """Get data from api."""
        try:
            res = await self.request("GET")
            return await res.json()
        except ClientResponseError as exc:
            _LOGGER.error(
                "API get_data failed. Status: %s, - %s", exc.code, exc.message
            )

    async def get_station(self):
        """Get data from api."""
        try:
            res = await self.request("GET", endpoint="stations/")
            return await res.json()
        except ClientResponseError as exc:
            _LOGGER.error(
                "API get_station failed. Status: %s, - %s", exc.code, exc.message
            )


@dataclass
class WLData:
    """Common data model for all API:s and stations."""

    temp_out: float | None = None
    temp_in: float | None = None
    humidity_out: float | None = None

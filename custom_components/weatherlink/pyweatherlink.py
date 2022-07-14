"""Library for Weatherlink.

Move to pypi.org when stable
"""
import logging
import urllib.parse

from aiohttp import ClientResponse, ClientResponseError, ClientSession

API_URL = "https://api.weatherlink.com/v1/NoaaExt.json"


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
            f"{API_URL}?{params_enc}",
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

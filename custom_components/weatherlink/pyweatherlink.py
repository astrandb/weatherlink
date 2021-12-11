"""Library for Weatherlink.

Move to pypi.org when stable
"""

from aiohttp import ClientResponse, ClientSession

API_URL = "https://api.weatherlink.com/v1/NoaaExt.json"


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

        return await self.websession.request(
            method,
            f"{API_URL}?user={self.username}&pass={self.password}&apiToken={self.apitoken}",
            **kwargs,
            headers=headers,
        )

    async def get_data(self):
        """Get data from api."""
        res = await self.request("GET")
        return await res.json()

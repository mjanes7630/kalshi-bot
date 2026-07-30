import time

import httpx
from cryptography.hazmat.primitives.asymmetric import rsa

from kalshi_bot.api.auth import create_auth_headers
from kalshi_bot.api.models import (
    GetBalanceResponse,
    GetMarketsResponse,
)

KALSHI_API_BASE_URL = "https://external-api.demo.kalshi.co/trade-api/v2/"


class KalshiClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        *,
        api_key_id: str | None = None,
        private_key: rsa.RSAPrivateKey | None = None,
    ) -> None:
        self._http_client = http_client
        self._api_key_id = api_key_id
        self._private_key = private_key

    async def get_markets(
        self,
        *,
        limit: int = 100,
        cursor: str | None = None,
    ) -> GetMarketsResponse:
        params: dict[str, int | str] = {"limit": limit}

        if cursor is not None:
            params["cursor"] = cursor

        response = await self._http_client.get(
            "markets",
            params=params,
        )
        response.raise_for_status()

        return GetMarketsResponse.model_validate(response.json())

    async def get_balance(self) -> GetBalanceResponse:
        if self._api_key_id is None or self._private_key is None:
            raise ValueError("API credentials are required to retrieve the balance.")

        path = "/trade-api/v2/portfolio/balance"
        timestamp = str(time.time_ns() // 1_000_000)

        headers = create_auth_headers(
            api_key_id=self._api_key_id,
            private_key=self._private_key,
            timestamp=timestamp,
            method="GET",
            path=path,
        )

        response = await self._http_client.get(
            "portfolio/balance",
            headers=headers,
        )
        response.raise_for_status()

        return GetBalanceResponse.model_validate(response.json())

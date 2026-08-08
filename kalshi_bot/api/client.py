import time

import httpx
from cryptography.hazmat.primitives.asymmetric import rsa

from kalshi_bot.api.auth import create_auth_headers
from kalshi_bot.api.models import (
    CancelOrderResponse,
    CreateOrderRequest,
    CreateOrderResponse,
    GetBalanceResponse,
    GetMarketOrderbookResponse,
    GetMarketsResponse,
    GetOrdersResponse,
    GetPositionsResponse,
    GetTradesResponse,
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

    async def get_trades(
        self,
        *,
        ticker: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> GetTradesResponse:
        params: dict[str, str | int] = {"limit": limit}

        if ticker is not None:
            params["ticker"] = ticker

        if cursor is not None:
            params["cursor"] = cursor

        if not 1 <= limit <= 1000:
            raise ValueError("Trade limit must be between 1 and 1000.")

        response = await self._http_client.get(
            "markets/trades",
            params=params,
        )
        response.raise_for_status()

        return GetTradesResponse.model_validate(response.json())

    async def get_market_orderbook(
        self,
        ticker: str,
        *,
        depth: int = 0,
    ) -> GetMarketOrderbookResponse:
        if self._api_key_id is None or self._private_key is None:
            raise ValueError(
                "API credentials are required to retrieve the market orderbook."
            )

        if not 0 <= depth <= 100:
            raise ValueError("Orderbook depth must be between 0 and 100.")

        path = f"/trade-api/v2/markets/{ticker}/orderbook"
        timestamp = str(time.time_ns() // 1_000_000)

        headers = create_auth_headers(
            api_key_id=self._api_key_id,
            private_key=self._private_key,
            timestamp=timestamp,
            method="GET",
            path=path,
        )

        response = await self._http_client.get(
            f"markets/{ticker}/orderbook",
            params={"depth": depth},
            headers=headers,
        )
        response.raise_for_status()

        return GetMarketOrderbookResponse.model_validate(response.json())

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

    async def get_positions(
        self,
        *,
        ticker: str | None = None,
        event_ticker: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> GetPositionsResponse:
        if self._api_key_id is None or self._private_key is None:
            raise ValueError("API credentials are required to retrieve positions.")

        params: dict[str, str | int] = {"limit": limit}

        if ticker is not None:
            params["ticker"] = ticker

        if event_ticker is not None:
            params["event_ticker"] = event_ticker

        if cursor is not None:
            params["cursor"] = cursor

        if not 1 <= limit <= 1000:
            raise ValueError("Position limit must be between 1 and 1000.")

        path = "/trade-api/v2/portfolio/positions"
        timestamp = str(time.time_ns() // 1_000_000)

        headers = create_auth_headers(
            api_key_id=self._api_key_id,
            private_key=self._private_key,
            timestamp=timestamp,
            method="GET",
            path=path,
        )

        response = await self._http_client.get(
            "portfolio/positions",
            params=params,
            headers=headers,
        )
        response.raise_for_status()

        return GetPositionsResponse.model_validate(response.json())

    async def get_orders(
        self,
        *,
        status: str,
        limit: int = 100,
        cursor: str | None = None,
    ) -> GetOrdersResponse:
        if self._api_key_id is None or self._private_key is None:
            raise ValueError("API credentials are required to retrieve orders.")

        params: dict[str, str | int] = {"status": status, "limit": limit}

        if cursor is not None:
            params["cursor"] = cursor

        if not 1 <= limit <= 1000:
            raise ValueError("Order limit must be between 1 and 1000.")

        path = "/trade-api/v2/portfolio/orders"
        timestamp = str(time.time_ns() // 1_000_000)

        headers = create_auth_headers(
            api_key_id=self._api_key_id,
            private_key=self._private_key,
            timestamp=timestamp,
            method="GET",
            path=path,
        )

        response = await self._http_client.get(
            "portfolio/orders",
            params=params,
            headers=headers,
        )
        response.raise_for_status()

        return GetOrdersResponse.model_validate(response.json())

    async def create_order(
        self,
        order_request: CreateOrderRequest,
    ) -> CreateOrderResponse:
        if self._api_key_id is None or self._private_key is None:
            raise ValueError("API credentials are required to create an order.")

        path = "/trade-api/v2/portfolio/events/orders"
        timestamp = str(time.time_ns() // 1_000_000)

        headers = create_auth_headers(
            api_key_id=self._api_key_id,
            private_key=self._private_key,
            timestamp=timestamp,
            method="POST",
            path=path,
        )

        response = await self._http_client.post(
            "portfolio/events/orders",
            json=order_request.model_dump(mode="json"),
            headers=headers,
        )
        response.raise_for_status()

        return CreateOrderResponse.model_validate(response.json())

    async def cancel_order(
        self,
        order_id: str,
    ) -> CancelOrderResponse:
        if self._api_key_id is None or self._private_key is None:
            raise ValueError("API credentials are required to cancel an order.")

        path = f"/trade-api/v2/portfolio/events/orders/{order_id}"
        timestamp = str(time.time_ns() // 1_000_000)

        headers = create_auth_headers(
            api_key_id=self._api_key_id,
            private_key=self._private_key,
            timestamp=timestamp,
            method="DELETE",
            path=path,
        )

        response = await self._http_client.delete(
            f"portfolio/events/orders/{order_id}",
            headers=headers,
        )
        response.raise_for_status()

        return CancelOrderResponse.model_validate(response.json())

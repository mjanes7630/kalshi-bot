import asyncio
from decimal import Decimal

import httpx
import pytest

from kalshi_bot.api.client import KALSHI_API_BASE_URL, KalshiClient


def test_get_markets_sends_request_and_parses_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/trade-api/v2/markets"
        assert request.url.params["limit"] == "50"
        assert request.url.params["cursor"] == "current-page-token"

        return httpx.Response(
            200,
            json={
                "markets": [
                    {
                        "ticker": "TEST-MARKET",
                        "title": "Test market",
                        "yes_bid_dollars": "0.3700",
                        "yes_ask_dollars": "0.4200",
                        "no_bid_dollars": "0.5800",
                        "no_ask_dollars": "0.6300",
                        "last_price_dollars": "0.4000",
                    }
                ],
                "cursor": "next-page-token",
            },
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            result = await client.get_markets(limit=50, cursor="current-page-token")

        assert result.cursor == "next-page-token"
        assert len(result.markets) == 1
        assert result.markets[0].ticker == "TEST-MARKET"
        assert result.markets[0].yes_bid_dollars == Decimal("0.3700")

    asyncio.run(run_test())


def test_get_markets_raises_for_unsuccessful_response() -> None:
    def handler(request: httpx.request) -> httpx.Response:
        return httpx.Response(
            503,
            json={"error": "Service unavailable"},
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            with pytest.raises(httpx.HTTPStatusError) as error:
                await client.get_markets()

        assert error.value.response.status_code == 503

    asyncio.run(run_test())

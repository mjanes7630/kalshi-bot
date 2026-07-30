import asyncio
import base64
from decimal import Decimal

import httpx
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

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
    def handler(request: httpx.Request) -> httpx.Response:
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


def test_get_balance_sends_authenticated_request_and_parses_response() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/trade-api/v2/portfolio/balance"
        assert request.headers["KALSHI-ACCESS-KEY"] == "test-key-id"

        timestamp = request.headers["KALSHI-ACCESS-TIMESTAMP"]
        expected_message = f"{timestamp}GET/trade-api/v2/portfolio/balance".encode()

        private_key.public_key().verify(
            base64.b64decode(request.headers["KALSHI-ACCESS-SIGNATURE"]),
            expected_message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )

        return httpx.Response(
            200,
            json={
                "balance": 1250,
                "balance_dollars": "12.5000",
                "portfolio_value": 1550,
                "updated_ts": 1703123456,
                "balance_breakdown": [],
            },
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(
                http_client,
                api_key_id="test-key-id",
                private_key=private_key,
            )

            result = await client.get_balance()

        assert result.balance == 1250
        assert result.balance_dollars == Decimal("12.5000")
        assert result.portfolio_value == 1550
        assert result.updated_ts == 1703123456

    asyncio.run(run_test())

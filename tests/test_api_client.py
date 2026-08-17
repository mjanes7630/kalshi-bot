import asyncio
import base64
import json
from decimal import Decimal
from http import HTTPStatus
from unittest.mock import AsyncMock, call, patch

import httpx
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from kalshi_bot.api.client import KALSHI_API_BASE_URL, KalshiClient
from kalshi_bot.api.models import (
    CreateOrderRequest,
    GetMarketResponse,
    GetOrderResponse,
    KalshiOrderSide,
)


def test_get_markets_sends_request_and_parses_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/trade-api/v2/markets"
        assert request.url.params["limit"] == "50"
        assert request.url.params["cursor"] == "current-page-token"

        return httpx.Response(
            HTTPStatus.OK,
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
                        "status": "open",
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
            HTTPStatus.SERVICE_UNAVAILABLE,
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

        assert error.value.response.status_code == HTTPStatus.SERVICE_UNAVAILABLE

    asyncio.run(run_test())


def test_get_market_sends_request_and_parses_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/trade-api/v2/markets/TEST-MARKET"

        return httpx.Response(
            HTTPStatus.OK,
            json={
                "market": {
                    "ticker": "TEST-MARKET",
                    "title": "Test market",
                    "yes_bid_dollars": "0.3700",
                    "yes_ask_dollars": "0.4200",
                    "no_bid_dollars": "0.5800",
                    "no_ask_dollars": "0.6300",
                    "last_price_dollars": "0.4000",
                    "status": "open",
                }
            },
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            result = await client.get_market("TEST-MARKET")

        assert isinstance(result, GetMarketResponse)
        assert result.market.ticker == "TEST-MARKET"

    asyncio.run(run_test())


def test_get_market_orderbook_sends_authenticated_request_and_parses_response() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/trade-api/v2/markets/TEST-MARKET/orderbook"
        assert request.url.params["depth"] == "5"
        assert request.headers["KALSHI-ACCESS-KEY"] == "test-key-id"

        timestamp = request.headers["KALSHI-ACCESS-TIMESTAMP"]
        expected_message = (
            f"{timestamp}GET/trade-api/v2/markets/TEST-MARKET/orderbook".encode()
        )

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
            HTTPStatus.OK,
            json={
                "orderbook_fp": {
                    "yes_dollars": [
                        ["0.3700", "125.00"],
                    ],
                    "no_dollars": [
                        ["0.5800", "80.00"],
                    ],
                },
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

            result = await client.get_market_orderbook(ticker="TEST-MARKET", depth=5)

        assert result.orderbook_fp.yes_dollars == [
            (Decimal("0.3700"), Decimal("125.00")),
        ]
        assert result.orderbook_fp.no_dollars == [
            (Decimal("0.5800"), Decimal("80.00")),
        ]

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
            HTTPStatus.OK,
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


def test_get_market_orderbook_requires_credentials() -> None:
    async def run_test() -> None:
        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
        ) as http_client:
            client = KalshiClient(http_client)

            with pytest.raises(
                ValueError,
                match="API credentials are required to retrieve the market orderbook.",
            ):
                await client.get_market_orderbook("TEST-MARKET")

    asyncio.run(run_test())


@pytest.mark.parametrize("depth", [-1, 101])
def test_get_market_orderbook_rejects_invalid_depth(depth: int) -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
        ) as http_client:
            client = KalshiClient(
                http_client,
                api_key_id="test-key-id",
                private_key=private_key,
            )

            with pytest.raises(
                ValueError,
                match="Orderbook depth must be between 0 and 100.",
            ):
                await client.get_market_orderbook(
                    ticker="TEST-MARKET",
                    depth=depth,
                )

    asyncio.run(run_test())


def test_get_balance_requires_credentials() -> None:
    async def run_test() -> None:
        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
        ) as http_client:
            client = KalshiClient(http_client)

            with pytest.raises(
                ValueError,
                match="API credentials are required to retrieve the balance.",
            ):
                await client.get_balance()

    asyncio.run(run_test())


def test_get_trades_sends_request_and_parses_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/trade-api/v2/markets/trades"
        assert request.url.params["ticker"] == "TEST-MARKET"
        assert request.url.params["limit"] == "50"
        assert request.url.params["cursor"] == "previous-page"
        assert "KALSHI-ACCESS-KEY" not in request.headers

        return httpx.Response(
            HTTPStatus.OK,
            json={
                "trades": [
                    {
                        "trade_id": "trade-123",
                        "ticker": "TEST-MARKET",
                        "count_fp": "12.50",
                        "yes_price_dollars": "0.4100",
                        "no_price_dollars": "0.5900",
                        "created_time": "2026-07-31T18:45:00Z",
                        "is_block_trade": False,
                    }
                ],
                "cursor": "next-page",
            },
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            result = await client.get_trades(
                ticker="TEST-MARKET",
                limit=50,
                cursor="previous-page",
            )

        assert result.trades[0].trade_id == "trade-123"
        assert result.trades[0].count_fp == Decimal("12.50")
        assert result.trades[0].yes_price_dollars == Decimal("0.4100")
        assert result.cursor == "next-page"

    asyncio.run(run_test())


def test_get_trades_omits_optional_query_parameters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/trade-api/v2/markets/trades"
        assert request.url.params["limit"] == "100"
        assert "ticker" not in request.url.params
        assert "cursor" not in request.url.params

        return httpx.Response(
            HTTPStatus.OK,
            json={
                "trades": [],
                "cursor": "",
            },
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            result = await client.get_trades()

        assert result.trades == []
        assert result.cursor == ""

    asyncio.run(run_test())


@pytest.mark.parametrize("limit", [0, 1001])
def test_get_trades_rejects_invalid_limit(limit: int) -> None:
    async def run_test() -> None:
        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
        ) as http_client:
            client = KalshiClient(http_client)

            with pytest.raises(
                ValueError,
                match="Trade limit must be between 1 and 1000.",
            ):
                await client.get_trades(limit=limit)

    asyncio.run(run_test())


def test_get_positions_sends_authenticated_request_and_parses_response() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/trade-api/v2/portfolio/positions"
        assert request.url.params["ticker"] == "TEST-MARKET"
        assert request.url.params["event_ticker"] == "TEST-EVENT"
        assert request.url.params["limit"] == "50"
        assert request.url.params["cursor"] == "previous-page"
        assert request.headers["KALSHI-ACCESS-KEY"] == "test-key-id"

        timestamp = request.headers["KALSHI-ACCESS-TIMESTAMP"]
        expected_message = (f"{timestamp}GET/trade-api/v2/portfolio/positions").encode()

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
            HTTPStatus.OK,
            json={
                "market_positions": [
                    {
                        "ticker": "TEST-MARKET",
                        "total_traded_dollars": "7.2500",
                        "position_fp": "-5.00",
                        "market_exposure_dollars": "2.0500",
                        "realized_pnl_dollars": "-0.3000",
                        "fees_paid_dollars": "0.1200",
                        "last_updated_ts": "2026-07-31T19:30:00Z",
                    }
                ],
                "event_positions": [],
                "cursor": "next-page",
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

            result = await client.get_positions(
                ticker="TEST-MARKET",
                event_ticker="TEST-EVENT",
                limit=50,
                cursor="previous-page",
            )

        position = result.market_positions[0]

        assert position.ticker == "TEST-MARKET"
        assert position.position_fp == Decimal("-5.00")
        assert position.market_exposure_dollars == Decimal("2.0500")
        assert result.cursor == "next-page"

    asyncio.run(run_test())


def test_get_positions_requires_credentials() -> None:
    async def run_test() -> None:
        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
        ) as http_client:
            client = KalshiClient(http_client)

            with pytest.raises(
                ValueError,
                match="API credentials are required to retrieve positions.",
            ):
                await client.get_positions()

    asyncio.run(run_test())


def test_get_positions_omits_optional_query_parameters() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/trade-api/v2/portfolio/positions"
        assert request.url.params["limit"] == "100"
        assert "ticker" not in request.url.params
        assert "event_ticker" not in request.url.params
        assert "cursor" not in request.url.params
        assert request.headers["KALSHI-ACCESS-KEY"] == "test-key-id"

        return httpx.Response(
            HTTPStatus.OK,
            json={
                "market_positions": [],
                "event_positions": [],
                "cursor": "",
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

            result = await client.get_positions()

        assert result.market_positions == []
        assert result.event_positions == []
        assert result.cursor == ""

    asyncio.run(run_test())


@pytest.mark.parametrize("limit", [0, 1001])
def test_get_positions_rejects_invalid_limit(limit: int) -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
        ) as http_client:
            client = KalshiClient(
                http_client,
                api_key_id="test-key-id",
                private_key=private_key,
            )

            with pytest.raises(
                ValueError,
                match="Position limit must be between 1 and 1000.",
            ):
                await client.get_positions(limit=limit)

    asyncio.run(run_test())


def test_create_order_sends_authenticated_request_and_parses_response() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    order_request = CreateOrderRequest(
        ticker="TEST-MARKET",
        client_order_id="client-order-123",
        side=KalshiOrderSide.BID,
        count=Decimal("2.00"),
        price=Decimal("0.4200"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == ("/trade-api/v2/portfolio/events/orders")
        assert request.headers["KALSHI-ACCESS-KEY"] == "test-key-id"
        assert request.headers["Content-Type"] == "application/json"

        assert json.loads(request.content) == {
            "ticker": "TEST-MARKET",
            "client_order_id": "client-order-123",
            "side": "bid",
            "count": "2.00",
            "price": "0.4200",
            "time_in_force": "good_till_canceled",
            "self_trade_prevention_type": "taker_at_cross",
            "post_only": True,
            "cancel_order_on_pause": True,
        }

        timestamp = request.headers["KALSHI-ACCESS-TIMESTAMP"]
        expected_message = (
            f"{timestamp}POST/trade-api/v2/portfolio/events/orders"
        ).encode()

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
            HTTPStatus.CREATED,
            json={
                "order_id": "order-123",
                "client_order_id": "client-order-123",
                "fill_count": "0.00",
                "remaining_count": "2.00",
                "ts_ms": 1785970800000,
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

            result = await client.create_order(order_request)

        assert result.order_id == "order-123"
        assert result.client_order_id == "client-order-123"
        assert result.fill_count == Decimal("0.00")
        assert result.remaining_count == Decimal("2.00")
        assert result.ts_ms == 1785970800000

    asyncio.run(run_test())


def test_create_order_requires_credentials() -> None:
    order_request = CreateOrderRequest(
        ticker="TEST-MARKET",
        client_order_id="client-order-123",
        side=KalshiOrderSide.BID,
        count=Decimal("2.00"),
        price=Decimal("0.4200"),
    )

    async def run_test() -> None:
        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
        ) as http_client:
            client = KalshiClient(http_client)

            with pytest.raises(
                ValueError,
                match="API credentials are required to create an order.",
            ):
                await client.create_order(order_request)

    asyncio.run(run_test())


def test_create_order_raises_for_unsuccessful_response() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    order_request = CreateOrderRequest(
        ticker="TEST-MARKET",
        client_order_id="client-order-123",
        side=KalshiOrderSide.BID,
        count=Decimal("2.00"),
        price=Decimal("0.4200"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            HTTPStatus.CONFLICT,
            json={
                "code": "order_rejected",
                "message": "Order rejected",
                "details": "Test rejection",
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

            with pytest.raises(httpx.HTTPStatusError) as error:
                await client.create_order(order_request)

        assert error.value.response.status_code == HTTPStatus.CONFLICT

    asyncio.run(run_test())


def test_cancel_order_sends_authenticated_request_and_parses_response() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.path == ("/trade-api/v2/portfolio/events/orders/order-123")
        assert request.headers["KALSHI-ACCESS-KEY"] == "test-key-id"

        timestamp = request.headers["KALSHI-ACCESS-TIMESTAMP"]
        expected_message = (
            f"{timestamp}DELETE/trade-api/v2/portfolio/events/orders/order-123"
        ).encode()

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
            HTTPStatus.OK,
            json={
                "order_id": "order-123",
                "client_order_id": "client-order-123",
                "reduced_by": "1.50",
                "ts_ms": 1785970800000,
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

            result = await client.cancel_order("order-123")

        assert result.order_id == "order-123"
        assert result.client_order_id == "client-order-123"
        assert result.reduced_by == Decimal("1.50")
        assert result.ts_ms == 1785970800000

    asyncio.run(run_test())


def test_cancel_order_requires_credentials() -> None:
    async def run_test() -> None:
        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
        ) as http_client:
            client = KalshiClient(http_client)

            with pytest.raises(
                ValueError,
                match="API credentials are required to cancel an order.",
            ):
                await client.cancel_order("order-123")

    asyncio.run(run_test())


def test_cancel_order_raises_for_unsuccessful_response() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            HTTPStatus.CONFLICT,
            json={
                "code": "order_not_cancelable",
                "message": "Order cannot be canceled",
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

            with pytest.raises(httpx.HTTPStatusError) as error:
                await client.cancel_order("order-123")

        assert error.value.response.status_code == HTTPStatus.CONFLICT

    asyncio.run(run_test())


def test_get_orders_sends_authenticated_request_and_parses_response() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/trade-api/v2/portfolio/orders"
        assert request.url.params["status"] == "resting"
        assert request.url.params["limit"] == "50"
        assert request.url.params["cursor"] == "previous-page"
        assert request.headers["KALSHI-ACCESS-KEY"] == "test-key-id"
        assert request.url.params["ticker"] == "TEST-MARKET"

        timestamp = request.headers["KALSHI-ACCESS-TIMESTAMP"]
        expected_message = (f"{timestamp}GET/trade-api/v2/portfolio/orders").encode()

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
            HTTPStatus.OK,
            json={
                "orders": [
                    {
                        "order_id": "order-123",
                        "ticker": "TEST-MARKET",
                        "side": "bid",
                        "yes_price_dollars": "0.4200",
                        "fill_count_fp": "0.50",
                        "remaining_count_fp": "1.50",
                        "initial_count_fp": "2.00",
                    }
                ],
                "cursor": "next-page",
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

            result = await client.get_orders(
                status="resting",
                ticker="TEST-MARKET",
                limit=50,
                cursor="previous-page",
            )

        order = result.orders[0]

        assert order.order_id == "order-123"
        assert order.ticker == "TEST-MARKET"
        assert order.remaining_count_fp == Decimal("1.50")
        assert result.cursor == "next-page"

    asyncio.run(run_test())


def test_get_orders_parses_order_side() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            HTTPStatus.OK,
            json={
                "orders": [
                    {
                        "order_id": "order-123",
                        "ticker": "TEST-MARKET",
                        "side": "bid",
                        "yes_price_dollars": "0.4200",
                        "fill_count_fp": "0.00",
                        "remaining_count_fp": "2.00",
                        "initial_count_fp": "2.00",
                    }
                ],
                "cursor": "",
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

            response = await client.get_orders(status="resting")

        assert response.orders[0].side is KalshiOrderSide.BID

    asyncio.run(run_test())


def test_get_orders_requires_credentials() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP request should not be sent.")

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            with pytest.raises(
                ValueError,
                match="API credentials are required to retrieve orders.",
            ):
                await client.get_orders(status="resting")

    asyncio.run(run_test())


@pytest.mark.parametrize("limit", [0, 1001])
def test_get_orders_rejects_invalid_limit(limit: int) -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP request should not be sent.")

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

            with pytest.raises(
                ValueError,
                match="Order limit must be between 1 and 1000.",
            ):
                await client.get_orders(
                    status="resting",
                    limit=limit,
                )

    asyncio.run(run_test())


def test_get_order_returns_specific_order() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == ("/trade-api/v2/portfolio/orders/order-123")
        assert request.headers["KALSHI-ACCESS-KEY"] == "test-key-id"

        return httpx.Response(
            HTTPStatus.OK,
            json={
                "order": {
                    "order_id": "order-123",
                    "client_order_id": "client-order-123",
                    "ticker": "TEST-MARKET",
                    "side": "bid",
                    "yes_price_dollars": "0.4200",
                    "fill_count_fp": "0.00",
                    "remaining_count_fp": "1.00",
                    "initial_count_fp": "1.00",
                }
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

            response = await client.get_order("order-123")

        assert isinstance(response, GetOrderResponse)
        assert response.order.order_id == "order-123"

    asyncio.run(run_test())


def test_get_order_requires_credentials() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP request should not be sent.")

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            with pytest.raises(
                ValueError,
                match="API credentials are required to retrieve an order.",
            ):
                await client.get_order("order-123")

    asyncio.run(run_test())


def test_get_order_raises_for_unsuccessful_response() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            HTTPStatus.NOT_FOUND,
            json={
                "code": "order_not_found",
                "message": "Order not found",
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

            with pytest.raises(httpx.HTTPStatusError) as error:
                await client.get_order("order-123")

        assert error.value.response.status_code == HTTPStatus.NOT_FOUND

    asyncio.run(run_test())


def test_get_market_raises_for_unsuccessful_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            HTTPStatus.NOT_FOUND,
            json={"error": "Market not found"},
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            with pytest.raises(httpx.HTTPStatusError) as error:
                await client.get_market("UNKNOWN-MARKET")

        assert error.value.response.status_code == HTTPStatus.NOT_FOUND

    asyncio.run(run_test())


def test_get_markets_retries_transient_connection_failure() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        if request_count == 1:
            raise httpx.ConnectError(
                "Connection failed.",
                request=request,
            )

        return httpx.Response(
            HTTPStatus.OK,
            json={
                "markets": [],
                "cursor": "",
            },
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            result = await client.get_markets()

        assert result.markets == []
        assert request_count == 2

    asyncio.run(run_test())


def test_get_markets_retries_with_exponential_backoff() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        if request_count < 3:
            raise httpx.ConnectError(
                "Connection failed.",
                request=request,
            )

        return httpx.Response(
            HTTPStatus.OK,
            json={
                "markets": [],
                "cursor": "",
            },
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            with patch(
                "kalshi_bot.api.client.asyncio.sleep",
                new_callable=AsyncMock,
            ) as sleep:
                result = await client.get_markets()

        assert result.markets == []
        assert request_count == 3
        assert sleep.await_args_list == [
            call(0.1),
            call(0.2),
        ]

    asyncio.run(run_test())


def test_get_markets_does_not_retry_unsuccessful_response() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        return httpx.Response(
            HTTPStatus.SERVICE_UNAVAILABLE,
            json={
                "error": "Service unavailable",
            },
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

        assert error.value.response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        assert request_count == 1

    asyncio.run(run_test())


def test_get_markets_raises_after_retry_limit_is_exhausted() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        raise httpx.ConnectError(
            "Connection failed.",
            request=request,
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            with (
                patch(
                    "kalshi_bot.api.client.asyncio.sleep",
                    new_callable=AsyncMock,
                ) as sleep,
                pytest.raises(httpx.ConnectError, match="Connection failed."),
            ):
                await client.get_markets()

        assert request_count == 3
        assert sleep.await_args_list == [
            call(0.1),
            call(0.2),
        ]

    asyncio.run(run_test())


def test_get_market_retries_transient_connection_failure() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        if request_count == 1:
            raise httpx.ConnectError(
                "Connection failed.",
                request=request,
            )

        return httpx.Response(
            HTTPStatus.OK,
            json={
                "market": {
                    "ticker": "TEST-MARKET",
                    "title": "Test market",
                    "yes_bid_dollars": "0.3700",
                    "yes_ask_dollars": "0.4200",
                    "no_bid_dollars": "0.5800",
                    "no_ask_dollars": "0.6300",
                    "last_price_dollars": "0.4000",
                    "status": "open",
                }
            },
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            result = await client.get_market("TEST-MARKET")

        assert result.market.ticker == "TEST-MARKET"
        assert request_count == 2

    asyncio.run(run_test())


def test_get_balance_retries_transient_connection_failure() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        if request_count == 1:
            raise httpx.ConnectError(
                "Connection failed.",
                request=request,
            )

        return httpx.Response(
            HTTPStatus.OK,
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

        assert result.balance_dollars == Decimal("12.5000")
        assert request_count == 2

    asyncio.run(run_test())


def test_get_market_orderbook_retries_transient_connection_failure() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        if request_count == 1:
            raise httpx.ConnectError(
                "Connection failed.",
                request=request,
            )

        return httpx.Response(
            HTTPStatus.OK,
            json={
                "orderbook_fp": {
                    "yes_dollars": [
                        ["0.3700", "125.00"],
                    ],
                    "no_dollars": [
                        ["0.5800", "80.00"],
                    ],
                },
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

            result = await client.get_market_orderbook(
                ticker="TEST-MARKET",
                depth=5,
            )

        assert result.orderbook_fp.yes_dollars == [
            (Decimal("0.3700"), Decimal("125.00")),
        ]
        assert request_count == 2

    asyncio.run(run_test())


def test_get_trades_retries_transient_connection_failure() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        if request_count == 1:
            raise httpx.ConnectError(
                "Connection failed.",
                request=request,
            )

        return httpx.Response(
            HTTPStatus.OK,
            json={
                "trades": [
                    {
                        "trade_id": "trade-123",
                        "ticker": "TEST-MARKET",
                        "count_fp": "12.50",
                        "yes_price_dollars": "0.4100",
                        "no_price_dollars": "0.5900",
                        "created_time": "2026-07-31T18:45:00Z",
                        "is_block_trade": False,
                    }
                ],
                "cursor": "",
            },
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            result = await client.get_trades(ticker="TEST-MARKET")

        assert result.trades[0].trade_id == "trade-123"
        assert request_count == 2

    asyncio.run(run_test())


def test_get_positions_retries_transient_connection_failure() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        if request_count == 1:
            raise httpx.ConnectError(
                "Connection failed.",
                request=request,
            )

        return httpx.Response(
            HTTPStatus.OK,
            json={
                "market_positions": [
                    {
                        "ticker": "TEST-MARKET",
                        "total_traded_dollars": "7.2500",
                        "position_fp": "-5.00",
                        "market_exposure_dollars": "2.0500",
                        "realized_pnl_dollars": "-0.3000",
                        "fees_paid_dollars": "0.1200",
                        "last_updated_ts": "2026-07-31T19:30:00Z",
                    }
                ],
                "event_positions": [],
                "cursor": "",
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

            result = await client.get_positions(ticker="TEST-MARKET")

        assert result.market_positions[0].ticker == "TEST-MARKET"
        assert request_count == 2

    asyncio.run(run_test())


def test_get_orders_retries_transient_connection_failure() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        if request_count == 1:
            raise httpx.ConnectError(
                "Connection failed.",
                request=request,
            )

        return httpx.Response(
            HTTPStatus.OK,
            json={
                "orders": [
                    {
                        "order_id": "order-123",
                        "ticker": "TEST-MARKET",
                        "side": "bid",
                        "yes_price_dollars": "0.4200",
                        "fill_count_fp": "0.00",
                        "remaining_count_fp": "2.00",
                        "initial_count_fp": "2.00",
                    }
                ],
                "cursor": "",
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

            result = await client.get_orders(status="resting")

        assert result.orders[0].order_id == "order-123"
        assert request_count == 2

    asyncio.run(run_test())


def test_get_order_retries_transient_connection_failure() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        if request_count == 1:
            raise httpx.ConnectError(
                "Connection failed.",
                request=request,
            )

        return httpx.Response(
            HTTPStatus.OK,
            json={
                "order": {
                    "order_id": "order-123",
                    "client_order_id": "client-order-123",
                    "ticker": "TEST-MARKET",
                    "side": "bid",
                    "yes_price_dollars": "0.4200",
                    "fill_count_fp": "0.00",
                    "remaining_count_fp": "1.00",
                    "initial_count_fp": "1.00",
                }
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

            result = await client.get_order("order-123")

        assert result.order.order_id == "order-123"
        assert request_count == 2

    asyncio.run(run_test())


def test_get_markets_retries_rate_limit_response() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        if request_count == 1:
            return httpx.Response(
                HTTPStatus.TOO_MANY_REQUESTS,
                json={"error": "Rate limit exceeded"},
            )

        return httpx.Response(
            HTTPStatus.OK,
            json={
                "markets": [],
                "cursor": "",
            },
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            with patch(
                "kalshi_bot.api.client.asyncio.sleep",
                new_callable=AsyncMock,
            ) as sleep:
                result = await client.get_markets()

        assert result.markets == []
        assert request_count == 2
        assert sleep.await_args_list == [call(0.1)]

    asyncio.run(run_test())


def test_get_markets_raises_after_rate_limit_retry_limit_is_exhausted() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        return httpx.Response(
            HTTPStatus.TOO_MANY_REQUESTS,
            json={"error": "Rate limit exceeded"},
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            with (
                patch(
                    "kalshi_bot.api.client.asyncio.sleep",
                    new_callable=AsyncMock,
                ) as sleep,
                pytest.raises(httpx.HTTPStatusError) as error,
            ):
                await client.get_markets()

        assert error.value.response.status_code == HTTPStatus.TOO_MANY_REQUESTS
        assert request_count == 3
        assert sleep.await_args_list == [
            call(0.1),
            call(0.2),
        ]

    asyncio.run(run_test())


def test_get_markets_honors_rate_limit_retry_after_header() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        if request_count == 1:
            return httpx.Response(
                HTTPStatus.TOO_MANY_REQUESTS,
                headers={"Retry-After": "1"},
                json={"error": "Rate limit exceeded"},
            )

        return httpx.Response(
            HTTPStatus.OK,
            json={
                "markets": [],
                "cursor": "",
            },
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            with patch(
                "kalshi_bot.api.client.asyncio.sleep",
                new_callable=AsyncMock,
            ) as sleep:
                result = await client.get_markets()

        assert result.markets == []
        assert request_count == 2
        assert sleep.await_args_list == [call(1.0)]

    asyncio.run(run_test())


def test_get_markets_uses_backoff_when_rate_limit_retry_after_header_is_invalid() -> (
    None
):
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        if request_count == 1:
            return httpx.Response(
                HTTPStatus.TOO_MANY_REQUESTS,
                headers={"Retry-After": "soon"},
                json={"error": "Rate limit exceeded"},
            )

        return httpx.Response(
            HTTPStatus.OK,
            json={
                "markets": [],
                "cursor": "",
            },
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            with patch(
                "kalshi_bot.api.client.asyncio.sleep",
                new_callable=AsyncMock,
            ) as sleep:
                result = await client.get_markets()

        assert result.markets == []
        assert request_count == 2
        assert sleep.await_args_list == [call(0.1)]

    asyncio.run(run_test())


def test_get_markets_uses_backoff_when_rate_limit_retry_after_header_is_negative() -> (
    None
):
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        if request_count == 1:
            return httpx.Response(
                HTTPStatus.TOO_MANY_REQUESTS,
                headers={"Retry-After": "-1"},
                json={"error": "Rate limit exceeded"},
            )

        return httpx.Response(
            HTTPStatus.OK,
            json={
                "markets": [],
                "cursor": "",
            },
        )

    async def run_test() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            base_url=KALSHI_API_BASE_URL,
            transport=transport,
        ) as http_client:
            client = KalshiClient(http_client)

            with patch(
                "kalshi_bot.api.client.asyncio.sleep",
                new_callable=AsyncMock,
            ) as sleep:
                result = await client.get_markets()

        assert result.markets == []
        assert request_count == 2
        assert sleep.await_args_list == [call(0.1)]

    asyncio.run(run_test())


def test_create_order_does_not_retry_transient_connection_failure() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    order_request = CreateOrderRequest(
        ticker="TEST-MARKET",
        client_order_id="client-order-123",
        side=KalshiOrderSide.BID,
        count=Decimal("2.00"),
        price=Decimal("0.4200"),
    )
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        raise httpx.ConnectError(
            "Connection failed.",
            request=request,
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

            with pytest.raises(httpx.ConnectError, match="Connection failed."):
                await client.create_order(order_request)

        assert request_count == 1

    asyncio.run(run_test())


def test_cancel_order_does_not_retry_transient_connection_failure() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        raise httpx.ConnectError(
            "Connection failed.",
            request=request,
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

            with pytest.raises(httpx.ConnectError, match="Connection failed."):
                await client.cancel_order("order-123")

        assert request_count == 1

    asyncio.run(run_test())

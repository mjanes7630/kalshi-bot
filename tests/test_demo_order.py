import asyncio
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, Mock, call, patch

import httpx
import pytest

from kalshi_bot.api.client import KALSHI_API_BASE_URL, KalshiClient
from kalshi_bot.api.models import (
    CancelOrderResponse,
    CreateOrderRequest,
    CreateOrderResponse,
    GetOrderResponse,
    KalshiOrderSide,
)
from kalshi_bot.config import Settings
from kalshi_bot.demo_order import run_demo_order, verify_demo_order


def test_verify_demo_order_does_not_submit_when_cancellation_disabled() -> None:
    order_request = CreateOrderRequest(
        ticker="TEST-MARKET",
        client_order_id="client-order-123",
        side=KalshiOrderSide.BID,
        count=Decimal("1.00"),
        price=Decimal("0.0100"),
    )
    client = AsyncMock(spec=KalshiClient)

    with pytest.raises(
        ValueError,
        match="Order submission and cancellation must both be enabled.",
    ):
        asyncio.run(
            verify_demo_order(
                order_request,
                client=client,
                order_submission_enabled=True,
                order_cancellation_enabled=False,
            )
        )

    client.create_order.assert_not_awaited()
    client.get_order.assert_not_awaited()
    client.cancel_order.assert_not_awaited()


def test_verify_demo_order_creates_retrieves_and_cancels_order() -> None:
    order_request = CreateOrderRequest(
        ticker="TEST-MARKET",
        client_order_id="client-order-123",
        side=KalshiOrderSide.BID,
        count=Decimal("1.00"),
        price=Decimal("0.0100"),
    )

    create_response = Mock(spec=CreateOrderResponse)
    create_response.order_id = "order-123"

    get_response = Mock(spec=GetOrderResponse)
    cancel_response = Mock(spec=CancelOrderResponse)

    client = AsyncMock(spec=KalshiClient)
    client.create_order.return_value = create_response
    client.get_order.return_value = get_response
    client.cancel_order.return_value = cancel_response

    result = asyncio.run(
        verify_demo_order(
            order_request,
            client=client,
            order_submission_enabled=True,
            order_cancellation_enabled=True,
        )
    )

    assert result is get_response
    assert client.mock_calls == [
        call.create_order(order_request),
        call.get_order("order-123"),
        call.cancel_order("order-123"),
    ]


def test_verify_demo_order_cancels_order_when_retrieval_fails() -> None:
    order_request = CreateOrderRequest(
        ticker="TEST-MARKET",
        client_order_id="client-order-123",
        side=KalshiOrderSide.BID,
        count=Decimal("1.00"),
        price=Decimal("0.0100"),
    )

    create_response = Mock(spec=CreateOrderResponse)
    create_response.order_id = "order-123"

    client = AsyncMock(spec=KalshiClient)
    client.create_order.return_value = create_response
    client.get_order.side_effect = RuntimeError("Retrieval failed")

    with pytest.raises(RuntimeError, match="Retrieval failed"):
        asyncio.run(
            verify_demo_order(
                order_request,
                client=client,
                order_submission_enabled=True,
                order_cancellation_enabled=True,
            )
        )

    client.cancel_order.assert_awaited_once_with("order-123")


def test_verify_demo_order_raises_when_cancellation_fails() -> None:
    order_request = CreateOrderRequest(
        ticker="TEST-MARKET",
        client_order_id="client-order-123",
        side=KalshiOrderSide.BID,
        count=Decimal("1.00"),
        price=Decimal("0.0100"),
    )

    create_response = Mock(spec=CreateOrderResponse)
    create_response.order_id = "order-123"

    get_response = Mock(spec=GetOrderResponse)

    client = AsyncMock(spec=KalshiClient)
    client.create_order.return_value = create_response
    client.get_order.return_value = get_response
    client.cancel_order.side_effect = RuntimeError("Cancellation failed")

    with pytest.raises(RuntimeError, match="Cancellation failed"):
        asyncio.run(
            verify_demo_order(
                order_request,
                client=client,
                order_submission_enabled=True,
                order_cancellation_enabled=True,
            )
        )

    client.cancel_order.assert_awaited_once_with("order-123")


def test_verify_demo_order_raises_both_errors_when_retrieval_and_cancellation_fail() -> (
    None
):
    order_request = CreateOrderRequest(
        ticker="TEST-MARKET",
        client_order_id="client-order-123",
        side=KalshiOrderSide.BID,
        count=Decimal("1.00"),
        price=Decimal("0.0100"),
    )

    create_response = Mock(spec=CreateOrderResponse)
    create_response.order_id = "order-123"

    client = AsyncMock(spec=KalshiClient)
    client.create_order.return_value = create_response
    client.get_order.side_effect = RuntimeError("Retrieval failed")
    client.cancel_order.side_effect = RuntimeError("Cancellation failed")

    with pytest.raises(ExceptionGroup) as error:
        asyncio.run(
            verify_demo_order(
                order_request,
                client=client,
                order_submission_enabled=True,
                order_cancellation_enabled=True,
            )
        )

    assert [str(exception) for exception in error.value.exceptions] == [
        "Retrieval failed",
        "Cancellation failed",
    ]


def test_verify_demo_order_does_not_retrieve_or_cancel_when_creation_fails() -> None:
    order_request = CreateOrderRequest(
        ticker="TEST-MARKET",
        client_order_id="client-order-123",
        side=KalshiOrderSide.BID,
        count=Decimal("1.00"),
        price=Decimal("0.0100"),
    )

    client = AsyncMock(spec=KalshiClient)
    client.create_order.side_effect = RuntimeError("Creation failed")

    with pytest.raises(RuntimeError, match="Creation failed"):
        asyncio.run(
            verify_demo_order(
                order_request,
                client=client,
                order_submission_enabled=True,
                order_cancellation_enabled=True,
            )
        )

    client.get_order.assert_not_awaited()
    client.cancel_order.assert_not_awaited()


def test_verify_demo_order_does_not_submit_when_submission_disabled() -> None:
    order_request = CreateOrderRequest(
        ticker="TEST-MARKET",
        client_order_id="client-order-123",
        side=KalshiOrderSide.BID,
        count=Decimal("1.00"),
        price=Decimal("0.0100"),
    )
    client = AsyncMock(spec=KalshiClient)

    with pytest.raises(
        ValueError,
        match="Order submission and cancellation must both be enabled.",
    ):
        asyncio.run(
            verify_demo_order(
                order_request,
                client=client,
                order_submission_enabled=False,
                order_cancellation_enabled=True,
            )
        )

    client.create_order.assert_not_awaited()
    client.get_order.assert_not_awaited()
    client.cancel_order.assert_not_awaited()


def test_run_demo_order_does_nothing_when_submission_is_disabled() -> None:
    settings = Settings(
        _env_file=None,
        order_submission_enabled=False,
        order_cancellation_enabled=True,
    )

    result = asyncio.run(run_demo_order(settings))

    assert result is None


def test_run_demo_order_requires_api_key_when_enabled() -> None:
    settings = Settings(
        _env_file=None,
        order_submission_enabled=True,
        order_cancellation_enabled=True,
        private_key_path=Path("test-private-key.pem"),
    )

    with pytest.raises(
        ValueError,
        match="KALSHI_BOT_API_KEY_ID is required.",
    ):
        asyncio.run(run_demo_order(settings))


def test_run_demo_order_requires_private_key_path_when_enabled() -> None:
    settings = Settings(
        _env_file=None,
        api_key_id="test-api-key-id",
        order_submission_enabled=True,
        order_cancellation_enabled=True,
    )

    with pytest.raises(
        ValueError,
        match="KALSHI_BOT_PRIVATE_KEY_PATH is required.",
    ):
        asyncio.run(run_demo_order(settings))


def test_run_demo_order_calls_verification_when_enabled() -> None:
    settings = Settings(
        _env_file=None,
        api_key_id="test-key-id",
        private_key_path=Path("test-private-key.pem"),
        order_submission_enabled=True,
        order_cancellation_enabled=True,
        demo_order_ticker="TEST-MARKET",
        demo_order_count=Decimal("2.00"),
        demo_order_price=Decimal("0.0200"),
    )

    private_key = Mock()
    http_client = Mock()
    logger = Mock()
    async_client_context = AsyncMock()
    async_client_context.__aenter__.return_value = http_client

    kalshi_client = Mock(spec=KalshiClient)
    verification_response = Mock()
    verification_response.order.order_id = "test-order-id"

    with (
        patch(
            "kalshi_bot.demo_order.load_private_key",
            return_value=private_key,
        ) as load_private_key_mock,
        patch(
            "kalshi_bot.demo_order.httpx.AsyncClient",
            return_value=async_client_context,
        ) as async_client_mock,
        patch(
            "kalshi_bot.demo_order.KalshiClient",
            return_value=kalshi_client,
        ) as client_mock,
        patch(
            "kalshi_bot.demo_order.verify_demo_order",
            new=AsyncMock(return_value=verification_response),
        ) as verification_mock,
        patch(
            "kalshi_bot.demo_order.logger",
            new=logger,
        ),
        patch(
            "kalshi_bot.demo_order.uuid4",
            return_value="generated-order-id",
        ) as uuid4_mock,
    ):
        result = asyncio.run(run_demo_order(settings))

    assert result is verification_response

    load_private_key_mock.assert_called_once_with(
        Path("test-private-key.pem"),
    )
    async_client_mock.assert_called_once_with(
        base_url=KALSHI_API_BASE_URL,
        timeout=httpx.Timeout(10.0),
    )
    client_mock.assert_called_once_with(
        http_client,
        api_key_id="test-key-id",
        private_key=private_key,
    )

    verification_mock.assert_awaited_once()

    verification_arguments = verification_mock.await_args.kwargs

    assert verification_arguments["client"] is kalshi_client
    assert verification_arguments["order_submission_enabled"] is True
    assert verification_arguments["order_cancellation_enabled"] is True

    order_request = verification_arguments["order_request"]

    assert order_request.ticker == "TEST-MARKET"
    assert order_request.side is KalshiOrderSide.BID
    assert order_request.count == Decimal("2.00")
    assert order_request.price == Decimal("0.0200")
    assert order_request.client_order_id == "generated-order-id"
    uuid4_mock.assert_called_once_with()

    async_client_context.__aenter__.assert_awaited_once()
    async_client_context.__aexit__.assert_awaited_once()

    logger.info.assert_has_calls(
        [
            call("demo_order_command_ready"),
            call(
                "demo_order_command_completed",
                order_id="test-order-id",
            ),
        ]
    )
    assert logger.info.call_count == 2


def test_run_demo_order_requires_demo_order_ticker_when_enabled() -> None:
    settings = Settings(
        _env_file=None,
        api_key_id="test-api-key-id",
        private_key_path=Path("test-private-key.pem"),
        order_submission_enabled=True,
        order_cancellation_enabled=True,
    )

    with pytest.raises(
        ValueError,
        match="KALSHI_BOT_DEMO_ORDER_TICKER is required.",
    ):
        asyncio.run(run_demo_order(settings))


def test_run_demo_order_requires_nonempty_demo_order_ticker_when_enabled() -> None:
    settings = Settings(
        _env_file=None,
        api_key_id="test-api-key-id",
        private_key_path=Path("test-private-key.pem"),
        order_submission_enabled=True,
        order_cancellation_enabled=True,
        demo_order_ticker="",
    )

    with pytest.raises(
        ValueError,
        match="KALSHI_BOT_DEMO_ORDER_TICKER is required.",
    ):
        asyncio.run(run_demo_order(settings))


def test_run_demo_order_requires_nonempty_demo_order_ticker_when_enabled_and_has_whitespace() -> (
    None
):
    settings = Settings(
        _env_file=None,
        api_key_id="test-api-key-id",
        private_key_path=Path("test-private-key.pem"),
        order_submission_enabled=True,
        order_cancellation_enabled=True,
        demo_order_ticker="   ",
    )

    with pytest.raises(
        ValueError,
        match="KALSHI_BOT_DEMO_ORDER_TICKER is required.",
    ):
        asyncio.run(run_demo_order(settings))


def test_run_demo_order_requires_demo_order_count_when_enabled() -> None:
    settings = Settings(
        _env_file=None,
        api_key_id="test-api-key-id",
        private_key_path=Path("test-private-key.pem"),
        order_submission_enabled=True,
        order_cancellation_enabled=True,
        demo_order_ticker="TEST-MARKET",
    )

    with pytest.raises(
        ValueError,
        match="KALSHI_BOT_DEMO_ORDER_COUNT is required.",
    ):
        asyncio.run(run_demo_order(settings))


def test_run_demo_order_requires_positive_demo_order_count_when_enabled() -> None:
    settings = Settings(
        _env_file=None,
        api_key_id="test-api-key-id",
        private_key_path=Path("test-private-key.pem"),
        order_submission_enabled=True,
        order_cancellation_enabled=True,
        demo_order_ticker="TEST-MARKET",
        demo_order_count=Decimal("0.00"),
    )

    with pytest.raises(
        ValueError,
        match="KALSHI_BOT_DEMO_ORDER_COUNT must be greater than zero.",
    ):
        asyncio.run(run_demo_order(settings))


def test_run_demo_order_requires_demo_order_price_when_enabled() -> None:
    settings = Settings(
        _env_file=None,
        api_key_id="test-api-key-id",
        private_key_path=Path("test-private-key.pem"),
        order_submission_enabled=True,
        order_cancellation_enabled=True,
        demo_order_ticker="TEST-MARKET",
        demo_order_count=Decimal("1.00"),
    )

    with pytest.raises(
        ValueError,
        match="KALSHI_BOT_DEMO_ORDER_PRICE is required.",
    ):
        asyncio.run(run_demo_order(settings))


def test_run_demo_order_requires_positive_demo_order_price_when_enabled() -> None:
    settings = Settings(
        _env_file=None,
        api_key_id="test-api-key-id",
        private_key_path=Path("test-private-key.pem"),
        order_submission_enabled=True,
        order_cancellation_enabled=True,
        demo_order_ticker="TEST-MARKET",
        demo_order_count=Decimal("1.00"),
        demo_order_price=Decimal("0.0000"),
    )

    with pytest.raises(
        ValueError,
        match="KALSHI_BOT_DEMO_ORDER_PRICE must be greater than zero.",
    ):
        asyncio.run(run_demo_order(settings))


def test_run_demo_order_requires_demo_order_price_below_one_when_enabled() -> None:
    settings = Settings(
        _env_file=None,
        api_key_id="test-api-key-id",
        private_key_path=Path("test-private-key.pem"),
        order_submission_enabled=True,
        order_cancellation_enabled=True,
        demo_order_ticker="TEST-MARKET",
        demo_order_count=Decimal("1.00"),
        demo_order_price=Decimal("1.0001"),
    )

    with pytest.raises(
        ValueError,
        match="KALSHI_BOT_DEMO_ORDER_PRICE must be less than one.",
    ):
        asyncio.run(run_demo_order(settings))

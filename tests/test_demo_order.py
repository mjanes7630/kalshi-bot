import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, call
from pathlib import Path

import pytest

from kalshi_bot.api.client import KalshiClient
from kalshi_bot.api.models import (
    CancelOrderResponse,
    CreateOrderRequest,
    CreateOrderResponse,
    GetOrderResponse,
    KalshiOrderSide,
)
from kalshi_bot.demo_order import verify_demo_order, run_demo_order
from kalshi_bot.config import Settings


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
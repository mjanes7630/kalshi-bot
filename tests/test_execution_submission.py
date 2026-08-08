import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, call
from uuid import UUID

import pytest

from kalshi_bot.api.client import KalshiClient
from kalshi_bot.api.models import (
    CreateOrderRequest,
    CreateOrderResponse,
    KalshiOrderSide,
)
from kalshi_bot.execution.models import ExecutionPlan, OrderIntent, OrderSide
from kalshi_bot.execution.submission import (
    build_create_order_request,
    submit_execution_plan,
)


@pytest.mark.parametrize(
    ("order_side", "expected_api_side"),
    [
        (OrderSide.BUY, KalshiOrderSide.BID),
        (OrderSide.SELL, KalshiOrderSide.ASK),
    ],
)
def test_build_create_order_request_maps_order_intent(
    order_side: OrderSide,
    expected_api_side: KalshiOrderSide,
) -> None:
    order_intent = OrderIntent(
        ticker="TEST-MARKET",
        side=order_side,
        price=Decimal("0.4200"),
        quantity=Decimal("2.00"),
    )

    order_request = build_create_order_request(
        order_intent,
        client_order_id="client-order-123",
    )

    assert order_request == CreateOrderRequest(
        ticker="TEST-MARKET",
        client_order_id="client-order-123",
        side=expected_api_side,
        count=Decimal("2.00"),
        price=Decimal("0.4200"),
    )


def test_submit_execution_plan_does_not_call_api_when_disabled() -> None:
    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(
            OrderIntent(
                ticker="TEST-MARKET",
                side=OrderSide.BUY,
                price=Decimal("0.4200"),
                quantity=Decimal("2.00"),
            ),
        ),
    )
    client = AsyncMock(spec=KalshiClient)

    responses = asyncio.run(
        submit_execution_plan(
            execution_plan,
            client=client,
            order_submission_enabled=False,
        )
    )

    assert responses == ()
    client.create_order.assert_not_awaited()


def test_submit_execution_plan_submits_each_intent_with_unique_ids() -> None:
    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(
            OrderIntent(
                ticker="TEST-MARKET",
                side=OrderSide.BUY,
                price=Decimal("0.4200"),
                quantity=Decimal("2.00"),
            ),
            OrderIntent(
                ticker="TEST-MARKET",
                side=OrderSide.SELL,
                price=Decimal("0.4400"),
                quantity=Decimal("3.00"),
            ),
        ),
    )
    buy_response = Mock(spec=CreateOrderResponse)
    sell_response = Mock(spec=CreateOrderResponse)
    client = AsyncMock(spec=KalshiClient)
    client.create_order.side_effect = [buy_response, sell_response]

    responses = asyncio.run(
        submit_execution_plan(
            execution_plan,
            client=client,
            order_submission_enabled=True,
        )
    )

    assert responses == (buy_response, sell_response)
    assert client.create_order.await_count == 2

    buy_request = client.create_order.await_args_list[0].args[0]
    sell_request = client.create_order.await_args_list[1].args[0]

    assert buy_request.side is KalshiOrderSide.BID
    assert sell_request.side is KalshiOrderSide.ASK

    buy_client_order_id = UUID(buy_request.client_order_id)
    sell_client_order_id = UUID(sell_request.client_order_id)

    assert buy_client_order_id != sell_client_order_id


def test_submit_execution_plan_cancels_submitted_order_after_failure() -> None:
    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(
            OrderIntent(
                ticker="TEST-MARKET",
                side=OrderSide.BUY,
                price=Decimal("0.4200"),
                quantity=Decimal("2.00"),
            ),
            OrderIntent(
                ticker="TEST-MARKET",
                side=OrderSide.SELL,
                price=Decimal("0.4400"),
                quantity=Decimal("3.00"),
            ),
        ),
    )
    buy_response = Mock(spec=CreateOrderResponse)
    buy_response.order_id = "buy-order-123"

    client = AsyncMock(spec=KalshiClient)
    client.create_order.side_effect = [
        buy_response,
        RuntimeError("sell order submission failed"),
    ]

    with pytest.raises(
        RuntimeError,
        match="sell order submission failed",
    ):
        asyncio.run(
            submit_execution_plan(
                execution_plan,
                client=client,
                order_submission_enabled=True,
            )
        )

    assert client.create_order.await_count == 2
    client.cancel_order.assert_awaited_once_with("buy-order-123")


def test_submit_execution_plan_reports_all_cleanup_failures() -> None:
    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(
            OrderIntent(
                ticker="TEST-MARKET",
                side=OrderSide.BUY,
                price=Decimal("0.4100"),
                quantity=Decimal("1.00"),
            ),
            OrderIntent(
                ticker="TEST-MARKET",
                side=OrderSide.SELL,
                price=Decimal("0.4500"),
                quantity=Decimal("1.00"),
            ),
            OrderIntent(
                ticker="TEST-MARKET",
                side=OrderSide.BUY,
                price=Decimal("0.4000"),
                quantity=Decimal("1.00"),
            ),
        ),
    )

    buy_response = Mock(spec=CreateOrderResponse)
    buy_response.order_id = "buy-order-123"

    sell_response = Mock(spec=CreateOrderResponse)
    sell_response.order_id = "sell-order-456"

    submission_error = RuntimeError("third order submission failed")
    sell_cancellation_error = RuntimeError("sell order cancellation failed")
    buy_cancellation_error = RuntimeError("buy order cancellation failed")

    client = AsyncMock(spec=KalshiClient)
    client.create_order.side_effect = [
        buy_response,
        sell_response,
        submission_error,
    ]
    client.cancel_order.side_effect = [
        sell_cancellation_error,
        buy_cancellation_error,
    ]

    with pytest.raises(ExceptionGroup) as error_info:
        asyncio.run(
            submit_execution_plan(
                execution_plan,
                client=client,
                order_submission_enabled=True,
            )
        )

    assert error_info.value.exceptions == (
        submission_error,
        sell_cancellation_error,
        buy_cancellation_error,
    )
    assert client.cancel_order.await_args_list == [
        call("sell-order-456"),
        call("buy-order-123"),
    ]

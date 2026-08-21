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
    KalshiTimeInForce,
)
from kalshi_bot.execution.models import (
    ExecutionPlan,
    OrderIntent,
    OrderSide,
    TimeInForce,
)
from kalshi_bot.execution.state import (
    LifecycleState,
    load_lifecycle_state,
    save_lifecycle_state,
)
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


def test_submit_execution_plan_cancels_submitted_order_after_failure(tmp_path) -> None:
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

    state_path = tmp_path / "lifecycle-state.json"
    save_lifecycle_state(
        LifecycleState(
            client_order_id_prefix="kbot-session-1234-",
            ticker="TEST-MARKET",
        ),
        state_path=state_path,
    )

    with pytest.raises(
        RuntimeError,
        match="sell order submission failed",
    ):
        asyncio.run(
            submit_execution_plan(
                execution_plan,
                client=client,
                order_submission_enabled=True,
                client_order_id_prefix="kbot-session-1234-",
                lifecycle_state_path=state_path,
            )
        )

    assert client.create_order.await_count == 2
    client.cancel_order.assert_awaited_once_with("buy-order-123")
    assert load_lifecycle_state(state_path).submitted_order_ids == ()


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


def test_build_create_order_request_allows_inventory_flattening_order_to_take_liquidity() -> (
    None
):
    order_intent = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4400"),
        quantity=Decimal("2.00"),
        post_only=False,
        time_in_force=TimeInForce.IMMEDIATE_OR_CANCEL,
    )

    order_request = build_create_order_request(
        order_intent,
        client_order_id="client-order-123",
    )

    assert order_request == CreateOrderRequest(
        ticker="TEST-MARKET",
        client_order_id="client-order-123",
        side=KalshiOrderSide.BID,
        count=Decimal("2.00"),
        price=Decimal("0.4400"),
        post_only=False,
        time_in_force=KalshiTimeInForce.IMMEDIATE_OR_CANCEL,
    )


def test_submit_execution_plan_persists_each_successful_order_id(
    tmp_path,
) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    save_lifecycle_state(
        LifecycleState(
            client_order_id_prefix="kbot-current-session-",
            ticker="TEST-MARKET",
        ),
        state_path=state_path,
    )

    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(
            OrderIntent(
                ticker="TEST-MARKET",
                side=OrderSide.BUY,
                price=Decimal("0.4200"),
                quantity=Decimal("1.00"),
            ),
            OrderIntent(
                ticker="TEST-MARKET",
                side=OrderSide.SELL,
                price=Decimal("0.4400"),
                quantity=Decimal("1.00"),
            ),
        ),
    )
    buy_response = Mock(spec=CreateOrderResponse)
    buy_response.order_id = "buy-order-123"
    sell_response = Mock(spec=CreateOrderResponse)
    sell_response.order_id = "sell-order-456"

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.create_order.side_effect = [
            buy_response,
            sell_response,
        ]

        await submit_execution_plan(
            execution_plan,
            client=client,
            order_submission_enabled=True,
            lifecycle_state_path=state_path,
        )

    asyncio.run(run_test())

    assert load_lifecycle_state(state_path).submitted_order_ids == (
        "buy-order-123",
        "sell-order-456",
    )

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, call

import pytest

from kalshi_bot.api.client import KalshiClient
from kalshi_bot.api.models import (
    CancelOrderResponse,
    CreateOrderRequest,
    GetOrdersResponse,
    KalshiContractSide,
    KalshiOrder,
    KalshiOrderSide,
    KalshiTimeInForce,
)
from kalshi_bot.execution.lifecycle import reconcile_execution_plan
from kalshi_bot.execution.models import (
    ExecutionPlan,
    OrderIntent,
    OrderSide,
    TimeInForce,
)
from kalshi_bot.execution.reconciliation import ReconciliationDecision


def test_reconcile_execution_plan_reads_scoped_orders_but_takes_no_actions_when_disabled() -> (
    None
):
    order_intent = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4200"),
        quantity=Decimal("2.00"),
    )
    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(order_intent,),
    )

    orders_response = Mock(spec=GetOrdersResponse)
    orders_response.orders = []
    orders_response.cursor = ""

    client = AsyncMock(spec=KalshiClient)
    client.get_orders.return_value = orders_response

    decision = asyncio.run(
        reconcile_execution_plan(
            execution_plan,
            client=client,
            order_submission_enabled=False,
            order_cancellation_enabled=False,
        )
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=(),
        order_intents_to_submit=(order_intent,),
    )
    client.get_orders.assert_awaited_once_with(
        status="resting",
        ticker="TEST-MARKET",
        limit=1000,
        cursor=None,
    )
    client.cancel_order.assert_not_awaited()
    client.create_order.assert_not_awaited()


def test_reconcile_execution_plan_cancels_unwanted_resting_order_when_enabled() -> None:
    resting_order = Mock(spec=KalshiOrder)
    resting_order.order_id = "resting-order-123"
    resting_order.ticker = "TEST-MARKET"
    resting_order.side = KalshiContractSide.YES
    resting_order.book_side = KalshiOrderSide.BID
    resting_order.yes_price_dollars = Decimal("0.4200")
    resting_order.remaining_count_fp = Decimal("2.00")

    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(),
    )

    orders_response = Mock(spec=GetOrdersResponse)
    orders_response.orders = [resting_order]
    orders_response.cursor = ""

    cancellation_response = Mock(spec=CancelOrderResponse)

    client = AsyncMock(spec=KalshiClient)
    client.get_orders.return_value = orders_response
    client.cancel_order.return_value = cancellation_response

    decision = asyncio.run(
        reconcile_execution_plan(
            execution_plan,
            client=client,
            order_submission_enabled=False,
            order_cancellation_enabled=True,
        )
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=("resting-order-123",),
        order_intents_to_submit=(),
    )
    client.cancel_order.assert_awaited_once_with("resting-order-123")
    client.create_order.assert_not_awaited()


def test_reconcile_execution_plan_submits_missing_order_when_enabled() -> None:
    order_intent = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4200"),
        quantity=Decimal("2.00"),
    )
    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(order_intent,),
    )

    orders_response = Mock(spec=GetOrdersResponse)
    orders_response.orders = []
    orders_response.cursor = ""

    client = AsyncMock(spec=KalshiClient)
    client.get_orders.return_value = orders_response

    decision = asyncio.run(
        reconcile_execution_plan(
            execution_plan,
            client=client,
            order_submission_enabled=True,
            order_cancellation_enabled=False,
        )
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=(),
        order_intents_to_submit=(order_intent,),
    )
    client.cancel_order.assert_not_awaited()

    client.create_order.assert_awaited_once()

    order_request = client.create_order.await_args.args[0]

    assert isinstance(order_request, CreateOrderRequest)
    assert order_request.ticker == "TEST-MARKET"
    assert order_request.side is KalshiOrderSide.BID
    assert order_request.count == Decimal("2.00")
    assert order_request.price == Decimal("0.4200")
    assert order_request.client_order_id


def test_reconcile_execution_plan_replaces_outdated_order_when_both_actions_enabled() -> (
    None
):
    outdated_order = Mock(spec=KalshiOrder)
    outdated_order.order_id = "outdated-order-123"
    outdated_order.ticker = "TEST-MARKET"
    outdated_order.side = KalshiContractSide.YES
    outdated_order.book_side = KalshiOrderSide.BID
    outdated_order.yes_price_dollars = Decimal("0.4100")
    outdated_order.remaining_count_fp = Decimal("2.00")

    replacement_intent = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4200"),
        quantity=Decimal("2.00"),
    )
    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(replacement_intent,),
    )

    orders_response = Mock(spec=GetOrdersResponse)
    orders_response.orders = [outdated_order]
    orders_response.cursor = ""

    client = AsyncMock(spec=KalshiClient)
    client.get_orders.return_value = orders_response

    decision = asyncio.run(
        reconcile_execution_plan(
            execution_plan,
            client=client,
            order_submission_enabled=True,
            order_cancellation_enabled=True,
        )
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=("outdated-order-123",),
        order_intents_to_submit=(replacement_intent,),
    )
    client.cancel_order.assert_awaited_once_with("outdated-order-123")

    client.create_order.assert_awaited_once()
    order_request = client.create_order.await_args.args[0]

    assert isinstance(order_request, CreateOrderRequest)
    assert order_request.ticker == "TEST-MARKET"
    assert order_request.side is KalshiOrderSide.BID
    assert order_request.count == Decimal("2.00")
    assert order_request.price == Decimal("0.4200")
    assert order_request.client_order_id


def test_reconcile_execution_plan_does_not_submit_replacement_when_cancellation_fails() -> (
    None
):
    outdated_order = Mock(spec=KalshiOrder)
    outdated_order.order_id = "outdated-order-123"
    outdated_order.ticker = "TEST-MARKET"
    outdated_order.side = KalshiContractSide.YES
    outdated_order.book_side = KalshiOrderSide.BID
    outdated_order.yes_price_dollars = Decimal("0.4100")
    outdated_order.remaining_count_fp = Decimal("2.00")

    replacement_intent = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4200"),
        quantity=Decimal("2.00"),
    )
    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(replacement_intent,),
    )

    orders_response = Mock(spec=GetOrdersResponse)
    orders_response.orders = [outdated_order]
    orders_response.cursor = ""

    client = AsyncMock(spec=KalshiClient)
    client.get_orders.return_value = orders_response
    client.cancel_order.side_effect = RuntimeError("Cancellation failed.")

    with pytest.raises(
        ExceptionGroup, match="One or more lifecycle order cancellations failed."
    ):
        asyncio.run(
            reconcile_execution_plan(
                execution_plan,
                client=client,
                order_submission_enabled=True,
                order_cancellation_enabled=True,
            )
        )

    client.cancel_order.assert_awaited_once_with("outdated-order-123")
    client.create_order.assert_not_awaited()


def test_reconcile_execution_plan_does_not_submit_replacement_when_cancellation_is_disabled() -> (
    None
):
    outdated_order = Mock(spec=KalshiOrder)
    outdated_order.order_id = "outdated-order-123"
    outdated_order.ticker = "TEST-MARKET"
    outdated_order.side = KalshiContractSide.YES
    outdated_order.book_side = KalshiOrderSide.BID
    outdated_order.yes_price_dollars = Decimal("0.4100")
    outdated_order.remaining_count_fp = Decimal("2.00")

    replacement_intent = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4200"),
        quantity=Decimal("2.00"),
    )
    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(replacement_intent,),
    )

    orders_response = Mock(spec=GetOrdersResponse)
    orders_response.orders = [outdated_order]
    orders_response.cursor = ""

    client = AsyncMock(spec=KalshiClient)
    client.get_orders.return_value = orders_response

    decision = asyncio.run(
        reconcile_execution_plan(
            execution_plan,
            client=client,
            order_submission_enabled=True,
            order_cancellation_enabled=False,
        )
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=("outdated-order-123",),
        order_intents_to_submit=(replacement_intent,),
    )
    client.cancel_order.assert_not_awaited()
    client.create_order.assert_not_awaited()


def test_reconcile_execution_plan_attempts_every_cancellation_before_raising() -> None:
    first_order = Mock(spec=KalshiOrder)
    first_order.order_id = "first-order-123"
    first_order.ticker = "TEST-MARKET"
    first_order.side = KalshiContractSide.YES
    first_order.book_side = KalshiOrderSide.BID
    first_order.yes_price_dollars = Decimal("0.4100")
    first_order.remaining_count_fp = Decimal("2.00")

    second_order = Mock(spec=KalshiOrder)
    second_order.order_id = "second-order-456"
    second_order.ticker = "TEST-MARKET"
    second_order.side = KalshiContractSide.YES
    second_order.book_side = KalshiOrderSide.BID
    second_order.yes_price_dollars = Decimal("0.4300")
    second_order.remaining_count_fp = Decimal("2.00")

    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(),
    )

    orders_response = Mock(spec=GetOrdersResponse)
    orders_response.orders = [first_order, second_order]
    orders_response.cursor = ""

    client = AsyncMock(spec=KalshiClient)
    client.get_orders.return_value = orders_response
    client.cancel_order.side_effect = [
        RuntimeError("First cancellation failed."),
        Mock(spec=CancelOrderResponse),
    ]

    with pytest.raises(
        ExceptionGroup,
        match="One or more lifecycle order cancellations failed.",
    ):
        asyncio.run(
            reconcile_execution_plan(
                execution_plan,
                client=client,
                order_submission_enabled=False,
                order_cancellation_enabled=True,
            )
        )

    assert client.cancel_order.await_args_list == [
        call("first-order-123"),
        call("second-order-456"),
    ]
    client.create_order.assert_not_awaited()


def test_reconcile_execution_plan_cancels_before_submitting_replacement() -> None:
    outdated_order = Mock(spec=KalshiOrder)
    outdated_order.order_id = "outdated-order-123"
    outdated_order.ticker = "TEST-MARKET"
    outdated_order.side = KalshiContractSide.YES
    outdated_order.book_side = KalshiOrderSide.BID
    outdated_order.yes_price_dollars = Decimal("0.4100")
    outdated_order.remaining_count_fp = Decimal("2.00")

    replacement_intent = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4200"),
        quantity=Decimal("2.00"),
    )
    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(replacement_intent,),
    )

    orders_response = Mock(spec=GetOrdersResponse)
    orders_response.orders = [outdated_order]
    orders_response.cursor = ""

    actions: list[str] = []

    async def cancel_order(order_id: str) -> Mock:
        actions.append(f"cancel:{order_id}")
        return Mock(spec=CancelOrderResponse)

    async def create_order(_request: CreateOrderRequest) -> Mock:
        actions.append("submit")
        return Mock()

    client = AsyncMock(spec=KalshiClient)
    client.get_orders.return_value = orders_response
    client.cancel_order.side_effect = cancel_order
    client.create_order.side_effect = create_order

    asyncio.run(
        reconcile_execution_plan(
            execution_plan,
            client=client,
            order_submission_enabled=True,
            order_cancellation_enabled=True,
        )
    )

    assert actions == [
        "cancel:outdated-order-123",
        "submit",
    ]


def test_reconcile_execution_plan_takes_no_actions_when_resting_order_matches_plan() -> (
    None
):
    matching_order = Mock(spec=KalshiOrder)
    matching_order.order_id = "matching-order-123"
    matching_order.ticker = "TEST-MARKET"
    matching_order.side = KalshiContractSide.YES
    matching_order.book_side = KalshiOrderSide.BID
    matching_order.yes_price_dollars = Decimal("0.4200")
    matching_order.remaining_count_fp = Decimal("2.00")

    matching_intent = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4200"),
        quantity=Decimal("2.00"),
    )
    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(matching_intent,),
    )

    orders_response = Mock(spec=GetOrdersResponse)
    orders_response.orders = [matching_order]
    orders_response.cursor = ""

    client = AsyncMock(spec=KalshiClient)
    client.get_orders.return_value = orders_response

    decision = asyncio.run(
        reconcile_execution_plan(
            execution_plan,
            client=client,
            order_submission_enabled=True,
            order_cancellation_enabled=True,
        )
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=(),
        order_intents_to_submit=(),
    )
    client.cancel_order.assert_not_awaited()
    client.create_order.assert_not_awaited()


def test_reconcile_execution_plan_submits_every_missing_order_when_enabled() -> None:
    first_intent = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4100"),
        quantity=Decimal("2.00"),
    )
    second_intent = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4200"),
        quantity=Decimal("3.00"),
    )
    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(first_intent, second_intent),
    )

    orders_response = Mock(spec=GetOrdersResponse)
    orders_response.orders = []
    orders_response.cursor = ""

    client = AsyncMock(spec=KalshiClient)
    client.get_orders.return_value = orders_response

    decision = asyncio.run(
        reconcile_execution_plan(
            execution_plan,
            client=client,
            order_submission_enabled=True,
            order_cancellation_enabled=False,
        )
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=(),
        order_intents_to_submit=(first_intent, second_intent),
    )
    client.cancel_order.assert_not_awaited()
    assert client.create_order.await_count == 2

    first_request, second_request = [
        call.args[0] for call in client.create_order.await_args_list
    ]

    assert first_request.ticker == "TEST-MARKET"
    assert first_request.price == Decimal("0.4100")
    assert first_request.count == Decimal("2.00")
    assert first_request.side is KalshiOrderSide.BID
    assert first_request.client_order_id

    assert second_request.ticker == "TEST-MARKET"
    assert second_request.price == Decimal("0.4200")
    assert second_request.count == Decimal("3.00")
    assert second_request.side is KalshiOrderSide.BID
    assert second_request.client_order_id
    assert first_request.client_order_id != second_request.client_order_id


def test_reconcile_execution_plan_submits_only_missing_order_when_one_order_already_matches() -> (
    None
):
    matching_order = Mock(spec=KalshiOrder)
    matching_order.order_id = "matching-order-123"
    matching_order.ticker = "TEST-MARKET"
    matching_order.side = KalshiContractSide.YES
    matching_order.book_side = KalshiOrderSide.BID
    matching_order.yes_price_dollars = Decimal("0.4100")
    matching_order.remaining_count_fp = Decimal("2.00")

    matching_intent = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4100"),
        quantity=Decimal("2.00"),
    )
    missing_intent = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4200"),
        quantity=Decimal("3.00"),
    )
    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(matching_intent, missing_intent),
    )

    orders_response = Mock(spec=GetOrdersResponse)
    orders_response.orders = [matching_order]
    orders_response.cursor = ""

    client = AsyncMock(spec=KalshiClient)
    client.get_orders.return_value = orders_response

    decision = asyncio.run(
        reconcile_execution_plan(
            execution_plan,
            client=client,
            order_submission_enabled=True,
            order_cancellation_enabled=True,
        )
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=(),
        order_intents_to_submit=(missing_intent,),
    )
    client.cancel_order.assert_not_awaited()

    client.create_order.assert_awaited_once()
    order_request = client.create_order.await_args.args[0]

    assert isinstance(order_request, CreateOrderRequest)
    assert order_request.ticker == "TEST-MARKET"
    assert order_request.side is KalshiOrderSide.BID
    assert order_request.price == Decimal("0.4200")
    assert order_request.count == Decimal("3.00")
    assert order_request.client_order_id


def test_reconcile_execution_plan_does_not_cancel_unowned_resting_order() -> None:
    order_intent = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4200"),
        quantity=Decimal("2.00"),
    )
    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(order_intent,),
    )

    unowned_order = Mock(spec=KalshiOrder)
    unowned_order.order_id = "manual-order-123"
    unowned_order.client_order_id = "manual-order-id"
    unowned_order.ticker = "TEST-MARKET"
    unowned_order.side = KalshiContractSide.YES
    unowned_order.book_side = KalshiOrderSide.BID
    unowned_order.yes_price_dollars = Decimal("0.4100")
    unowned_order.remaining_count_fp = Decimal("2.00")

    orders_response = Mock(spec=GetOrdersResponse)
    orders_response.orders = [unowned_order]
    orders_response.cursor = ""

    client = AsyncMock(spec=KalshiClient)
    client.get_orders.return_value = orders_response

    decision = asyncio.run(
        reconcile_execution_plan(
            execution_plan,
            client=client,
            client_order_id_prefix="kbot-session-1234-",
            order_submission_enabled=True,
            order_cancellation_enabled=True,
        )
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=(),
        order_intents_to_submit=(order_intent,),
    )
    client.cancel_order.assert_not_awaited()
    client.create_order.assert_awaited_once()

    submitted_request = client.create_order.await_args.args[0]

    assert submitted_request.client_order_id.startswith(
        "kbot-session-1234-",
    )


def test_reconcile_execution_plan_cancels_resting_quote_before_submitting_flattening_order() -> (
    None
):
    resting_order = Mock(spec=KalshiOrder)
    resting_order.order_id = "resting-order-123"
    resting_order.ticker = "TEST-MARKET"
    resting_order.side = KalshiContractSide.YES
    resting_order.book_side = KalshiOrderSide.ASK
    resting_order.yes_price_dollars = Decimal("0.4200")
    resting_order.remaining_count_fp = Decimal("2.00")

    flattening_order = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.SELL,
        price=Decimal("0.4200"),
        quantity=Decimal("2.00"),
        post_only=False,
        time_in_force=TimeInForce.IMMEDIATE_OR_CANCEL,
    )
    execution_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(flattening_order,),
    )

    orders_response = Mock(spec=GetOrdersResponse)
    orders_response.orders = [resting_order]
    orders_response.cursor = ""

    actions: list[str] = []

    async def cancel_order(order_id: str) -> Mock:
        actions.append(f"cancel:{order_id}")
        return Mock(spec=CancelOrderResponse)

    async def create_order(order_request: CreateOrderRequest) -> Mock:
        actions.append("submit")
        assert order_request.post_only is False
        assert order_request.time_in_force is KalshiTimeInForce.IMMEDIATE_OR_CANCEL
        return Mock()

    client = AsyncMock(spec=KalshiClient)
    client.get_orders.return_value = orders_response
    client.cancel_order.side_effect = cancel_order
    client.create_order.side_effect = create_order

    asyncio.run(
        reconcile_execution_plan(
            execution_plan,
            client=client,
            order_submission_enabled=True,
            order_cancellation_enabled=True,
        )
    )

    assert actions == [
        "cancel:resting-order-123",
        "submit",
    ]

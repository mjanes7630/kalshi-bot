from decimal import Decimal
from unittest.mock import Mock

import pytest

from kalshi_bot.api.models import KalshiOrder, KalshiOrderSide
from kalshi_bot.execution.models import OrderIntent, OrderSide, TimeInForce
from kalshi_bot.execution.reconciliation import (
    ReconciliationDecision,
    reconcile_orders,
)


def test_reconcile_orders_does_nothing_when_resting_orders_match_desired_quotes() -> (
    None
):
    desired_orders = (
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
            quantity=Decimal("2.00"),
        ),
    )

    resting_bid = Mock(spec=KalshiOrder)
    resting_bid.order_id = "bid-order-123"
    resting_bid.ticker = "TEST-MARKET"
    resting_bid.side = KalshiOrderSide.BID
    resting_bid.yes_price_dollars = Decimal("0.4200")
    resting_bid.remaining_count_fp = Decimal("2.00")

    resting_ask = Mock(spec=KalshiOrder)
    resting_ask.order_id = "ask-order-456"
    resting_ask.ticker = "TEST-MARKET"
    resting_ask.side = KalshiOrderSide.ASK
    resting_ask.yes_price_dollars = Decimal("0.4400")
    resting_ask.remaining_count_fp = Decimal("2.00")

    decision = reconcile_orders(
        desired_orders=desired_orders,
        resting_orders=(resting_bid, resting_ask),
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=(),
        order_intents_to_submit=(),
    )


def test_reconcile_orders_replaces_resting_order_that_differs_from_desired_quote() -> (
    None
):
    desired_order = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4200"),
        quantity=Decimal("2.00"),
    )

    stale_resting_bid = Mock(spec=KalshiOrder)
    stale_resting_bid.order_id = "stale-bid-123"
    stale_resting_bid.ticker = "TEST-MARKET"
    stale_resting_bid.side = KalshiOrderSide.BID
    stale_resting_bid.yes_price_dollars = Decimal("0.4100")
    stale_resting_bid.remaining_count_fp = Decimal("2.00")

    decision = reconcile_orders(
        desired_orders=(desired_order,),
        resting_orders=(stale_resting_bid,),
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=("stale-bid-123",),
        order_intents_to_submit=(desired_order,),
    )


def test_reconcile_orders_replaces_partially_filled_order() -> None:
    desired_order = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4200"),
        quantity=Decimal("2.00"),
    )

    partially_filled_bid = Mock(spec=KalshiOrder)
    partially_filled_bid.order_id = "partial-bid-123"
    partially_filled_bid.ticker = "TEST-MARKET"
    partially_filled_bid.side = KalshiOrderSide.BID
    partially_filled_bid.yes_price_dollars = Decimal("0.4200")
    partially_filled_bid.remaining_count_fp = Decimal("1.00")

    decision = reconcile_orders(
        desired_orders=(desired_order,),
        resting_orders=(partially_filled_bid,),
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=("partial-bid-123",),
        order_intents_to_submit=(desired_order,),
    )


def test_reconcile_orders_submits_desired_quote_when_no_resting_orders_exist() -> None:
    desired_order = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.SELL,
        price=Decimal("0.4400"),
        quantity=Decimal("2.00"),
    )

    decision = reconcile_orders(
        desired_orders=(desired_order,),
        resting_orders=(),
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=(),
        order_intents_to_submit=(desired_order,),
    )


def test_reconcile_orders_cancels_duplicate_resting_order() -> None:
    desired_order = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4200"),
        quantity=Decimal("2.00"),
    )

    first_resting_bid = Mock(spec=KalshiOrder)
    first_resting_bid.order_id = "bid-order-123"
    first_resting_bid.ticker = "TEST-MARKET"
    first_resting_bid.side = KalshiOrderSide.BID
    first_resting_bid.yes_price_dollars = Decimal("0.4200")
    first_resting_bid.remaining_count_fp = Decimal("2.00")

    duplicate_resting_bid = Mock(spec=KalshiOrder)
    duplicate_resting_bid.order_id = "duplicate-bid-456"
    duplicate_resting_bid.ticker = "TEST-MARKET"
    duplicate_resting_bid.side = KalshiOrderSide.BID
    duplicate_resting_bid.yes_price_dollars = Decimal("0.4200")
    duplicate_resting_bid.remaining_count_fp = Decimal("2.00")

    decision = reconcile_orders(
        desired_orders=(desired_order,),
        resting_orders=(first_resting_bid, duplicate_resting_bid),
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=("duplicate-bid-456",),
        order_intents_to_submit=(),
    )


def test_reconcile_orders_cancels_resting_order_when_strategy_wants_no_quotes() -> None:
    resting_bid = Mock(spec=KalshiOrder)
    resting_bid.order_id = "bid-order-123"
    resting_bid.ticker = "TEST-MARKET"
    resting_bid.side = KalshiOrderSide.BID
    resting_bid.yes_price_dollars = Decimal("0.4200")
    resting_bid.remaining_count_fp = Decimal("2.00")

    decision = reconcile_orders(
        desired_orders=(),
        resting_orders=(resting_bid,),
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=("bid-order-123",),
        order_intents_to_submit=(),
    )


def test_reconcile_orders_replaces_resting_order_from_different_market() -> None:
    desired_order = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4200"),
        quantity=Decimal("2.00"),
    )

    other_market_bid = Mock(spec=KalshiOrder)
    other_market_bid.order_id = "other-market-bid-123"
    other_market_bid.ticker = "OTHER-MARKET"
    other_market_bid.side = KalshiOrderSide.BID
    other_market_bid.yes_price_dollars = Decimal("0.4200")
    other_market_bid.remaining_count_fp = Decimal("2.00")

    decision = reconcile_orders(
        desired_orders=(desired_order,),
        resting_orders=(other_market_bid,),
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=("other-market-bid-123",),
        order_intents_to_submit=(desired_order,),
    )


def test_reconcile_orders_submits_missing_duplicate_desired_quote() -> None:
    desired_order = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4200"),
        quantity=Decimal("2.00"),
    )

    resting_bid = Mock(spec=KalshiOrder)
    resting_bid.order_id = "bid-order-123"
    resting_bid.ticker = "TEST-MARKET"
    resting_bid.side = KalshiOrderSide.BID
    resting_bid.yes_price_dollars = Decimal("0.4200")
    resting_bid.remaining_count_fp = Decimal("2.00")

    decision = reconcile_orders(
        desired_orders=(desired_order, desired_order),
        resting_orders=(resting_bid,),
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=(),
        order_intents_to_submit=(desired_order,),
    )


def test_reconcile_orders_rejects_unmatched_resting_order_without_order_id() -> None:
    resting_bid = Mock(spec=KalshiOrder)
    resting_bid.order_id = ""
    resting_bid.ticker = "TEST-MARKET"
    resting_bid.side = KalshiOrderSide.BID
    resting_bid.yes_price_dollars = Decimal("0.4200")
    resting_bid.remaining_count_fp = Decimal("2.00")

    with pytest.raises(ValueError, match="order_id"):
        reconcile_orders(
            desired_orders=(),
            resting_orders=(resting_bid,),
        )


def test_reconcile_orders_replaces_resting_quote_with_inventory_flattening_order() -> (
    None
):
    resting_order = Mock(spec=KalshiOrder)
    resting_order.order_id = "resting-order-123"
    resting_order.ticker = "TEST-MARKET"
    resting_order.side = KalshiOrderSide.ASK
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

    decision = reconcile_orders(
        desired_orders=(flattening_order,),
        resting_orders=(resting_order,),
    )

    assert decision == ReconciliationDecision(
        order_ids_to_cancel=("resting-order-123",),
        order_intents_to_submit=(flattening_order,),
    )

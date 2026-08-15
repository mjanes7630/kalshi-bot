from datetime import UTC, datetime
from decimal import Decimal

import pytest

from kalshi_bot.execution.inventory import (
    InventoryAction,
    create_flattening_order_intent,
)
from kalshi_bot.execution.models import OrderIntent, OrderSide, TimeInForce
from kalshi_bot.marketdata.models import MarketSnapshot, OrderBookLevel


def test_create_flattening_order_intent_sells_long_yes_at_best_yes_bid() -> None:
    snapshot = MarketSnapshot(
        ticker="TEST-MARKET",
        title="Test market",
        status="open",
        last_price=Decimal("0.4200"),
        yes_bids=(
            OrderBookLevel(
                price=Decimal("0.4200"),
                quantity=Decimal("10.00"),
            ),
        ),
        yes_asks=(),
        recent_trades=(),
        observed_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    order_intent = create_flattening_order_intent(
        ticker="TEST-MARKET",
        inventory_action=InventoryAction(
            side=OrderSide.SELL,
            quantity=Decimal("2.00"),
        ),
        snapshot=snapshot,
    )

    assert order_intent == OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.SELL,
        price=Decimal("0.4200"),
        quantity=Decimal("2.00"),
        post_only=False,
        time_in_force=TimeInForce.IMMEDIATE_OR_CANCEL,
    )
    assert order_intent.post_only is False
    assert order_intent.time_in_force is TimeInForce.IMMEDIATE_OR_CANCEL


def test_create_flattening_order_intent_buys_short_yes_at_best_yes_ask() -> None:
    snapshot = MarketSnapshot(
        ticker="TEST-MARKET",
        title="Test market",
        status="open",
        last_price=Decimal("0.4200"),
        yes_bids=(),
        yes_asks=(
            OrderBookLevel(
                price=Decimal("0.4400"),
                quantity=Decimal("10.00"),
            ),
        ),
        recent_trades=(),
        observed_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    order_intent = create_flattening_order_intent(
        ticker="TEST-MARKET",
        inventory_action=InventoryAction(
            side=OrderSide.BUY,
            quantity=Decimal("2.00"),
        ),
        snapshot=snapshot,
    )

    assert order_intent == OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.BUY,
        price=Decimal("0.4400"),
        quantity=Decimal("2.00"),
        post_only=False,
        time_in_force=TimeInForce.IMMEDIATE_OR_CANCEL,
    )
    assert order_intent.post_only is False
    assert order_intent.time_in_force is TimeInForce.IMMEDIATE_OR_CANCEL


def test_create_flattening_order_intent_rejects_long_yes_without_best_yes_bid() -> None:
    snapshot = MarketSnapshot(
        ticker="TEST-MARKET",
        title="Test market",
        status="open",
        last_price=Decimal("0.4200"),
        yes_bids=(),
        yes_asks=(),
        recent_trades=(),
        observed_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    with pytest.raises(
        ValueError,
        match="A flattening order requires a matching best YES price.",
    ):
        create_flattening_order_intent(
            ticker="TEST-MARKET",
            inventory_action=InventoryAction(
                side=OrderSide.SELL,
                quantity=Decimal("2.00"),
            ),
            snapshot=snapshot,
        )


def test_create_flattening_order_intent_rejects_ticker_that_differs_from_snapshot() -> (
    None
):
    snapshot = MarketSnapshot(
        ticker="MARKET-A",
        title="Test market",
        status="open",
        last_price=Decimal("0.4200"),
        yes_bids=(
            OrderBookLevel(
                price=Decimal("0.4200"),
                quantity=Decimal("10.00"),
            ),
        ),
        yes_asks=(),
        recent_trades=(),
        observed_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="ticker must match snapshot.ticker"):
        create_flattening_order_intent(
            ticker="MARKET-B",
            inventory_action=InventoryAction(
                side=OrderSide.SELL,
                quantity=Decimal("2.00"),
            ),
            snapshot=snapshot,
        )


def test_create_flattening_order_intent_rejects_closed_market() -> None:
    snapshot = MarketSnapshot(
        ticker="TEST-MARKET",
        title="Test market",
        status="closed",
        last_price=Decimal("0.4200"),
        yes_bids=(
            OrderBookLevel(
                price=Decimal("0.4200"),
                quantity=Decimal("10.00"),
            ),
        ),
        yes_asks=(),
        recent_trades=(),
        observed_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="market must be open"):
        create_flattening_order_intent(
            ticker="TEST-MARKET",
            inventory_action=InventoryAction(
                side=OrderSide.SELL,
                quantity=Decimal("2.00"),
            ),
            snapshot=snapshot,
        )


def test_create_flattening_order_intent_rejects_non_positive_quantity() -> None:
    snapshot = MarketSnapshot(
        ticker="TEST-MARKET",
        title="Test market",
        status="open",
        last_price=Decimal("0.4200"),
        yes_bids=(
            OrderBookLevel(
                price=Decimal("0.4200"),
                quantity=Decimal("10.00"),
            ),
        ),
        yes_asks=(),
        recent_trades=(),
        observed_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="quantity must be positive"):
        create_flattening_order_intent(
            ticker="TEST-MARKET",
            inventory_action=InventoryAction(
                side=OrderSide.SELL,
                quantity=Decimal("0.00"),
            ),
            snapshot=snapshot,
        )

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from kalshi_bot.api.models import KalshiMarketStatus
from kalshi_bot.execution.inventory import (
    InventoryAction,
    can_flatten_inventory,
    decide_inventory_action,
)
from kalshi_bot.execution.models import OrderSide


def test_decide_inventory_action_sells_yes_to_flatten_long_position() -> None:
    decision = decide_inventory_action(
        position=Decimal("2.00"),
    )

    assert decision == InventoryAction(
        side=OrderSide.SELL,
        quantity=Decimal("2.00"),
    )


def test_decide_inventory_action_buys_yes_to_flatten_short_position() -> None:
    decision = decide_inventory_action(
        position=Decimal("-2.00"),
    )

    assert decision == InventoryAction(
        side=OrderSide.BUY,
        quantity=Decimal("2.00"),
    )


def test_decide_inventory_action_returns_none_for_zero_position() -> None:
    decision = decide_inventory_action(
        position=Decimal("0.00"),
    )

    assert decision is None


def test_decide_inventory_action_rejects_non_decimal_position() -> None:
    with pytest.raises(TypeError, match="position must be a Decimal"):
        decide_inventory_action(
            position=2.0,
        )


def test_decide_inventory_action_rejects_non_finite_position() -> None:
    with pytest.raises(ValueError, match="position must be finite"):
        decide_inventory_action(
            position=Decimal("NaN"),
        )


def test_can_flatten_inventory_returns_false_for_closed_market() -> None:
    observed_at = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

    assert (
        can_flatten_inventory(
            market_status=KalshiMarketStatus.CLOSED,
            observed_at=observed_at,
            now=observed_at,
            max_observed_age_seconds=30,
        )
        is False
    )


def test_can_flatten_inventory_returns_false_for_stale_market_data() -> None:
    observed_at = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

    assert (
        can_flatten_inventory(
            market_status=KalshiMarketStatus.ACTIVE,
            observed_at=observed_at,
            now=observed_at + timedelta(seconds=31),
            max_observed_age_seconds=30,
        )
        is False
    )


def test_can_flatten_inventory_returns_true_for_open_fresh_market() -> None:
    observed_at = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

    assert (
        can_flatten_inventory(
            market_status=KalshiMarketStatus.ACTIVE,
            observed_at=observed_at,
            now=observed_at + timedelta(seconds=30),
            max_observed_age_seconds=30,
        )
        is True
    )

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from kalshi_bot.marketdata.models import (
    MarketSnapshot,
    MarketTrade,
    OrderBookLevel,
)


@pytest.fixture
def snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        ticker="TEST-MARKET",
        title="Test market",
        status="open",
        last_price=Decimal("0.4300"),
        yes_bids=(
            OrderBookLevel(Decimal("0.4200"), Decimal("13.00")),
            OrderBookLevel(Decimal("0.4100"), Decimal("10.00")),
        ),
        yes_asks=(
            OrderBookLevel(Decimal("0.4400"), Decimal("17.00")),
            OrderBookLevel(Decimal("0.4500"), Decimal("20.00")),
        ),
        recent_trades=(
            MarketTrade(
                trade_id="trade-123",
                price=Decimal("0.4300"),
                quantity=Decimal("2.00"),
                created_time=datetime(2026, 8, 2, 18, 30, tzinfo=UTC),
                is_block_trade=False,
            ),
        ),
        observed_at=datetime(2026, 8, 2, 18, 31, tzinfo=UTC),
    )


def test_returns_best_yes_bid(snapshot: MarketSnapshot) -> None:
    assert snapshot.best_yes_bid == OrderBookLevel(
        Decimal("0.4200"),
        Decimal("13.00"),
    )


def test_returns_best_yes_ask(snapshot: MarketSnapshot) -> None:
    assert snapshot.best_yes_ask == OrderBookLevel(
        Decimal("0.4400"),
        Decimal("17.00"),
    )


def test_calculates_yes_spread_and_midpoint(
    snapshot: MarketSnapshot,
) -> None:
    assert snapshot.yes_spread == Decimal("0.0200")
    assert snapshot.yes_midpoint == Decimal("0.4300")


def test_returns_none_when_one_side_has_no_liquidity(
    snapshot: MarketSnapshot,
) -> None:
    snapshot_without_asks = replace(snapshot, yes_asks=())

    assert snapshot_without_asks.best_yes_ask is None
    assert snapshot_without_asks.yes_spread is None
    assert snapshot_without_asks.yes_midpoint is None

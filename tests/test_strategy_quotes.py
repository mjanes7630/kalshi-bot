from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from kalshi_bot.api.models import KalshiMarketStatus
from kalshi_bot.marketdata.models import MarketSnapshot, OrderBookLevel
from kalshi_bot.strategy.models import (
    QuoteDecision,
    QuoteDecisionReason,
    QuoteProposal,
)
from kalshi_bot.strategy.quotes import decide_quotes


@pytest.fixture
def snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        ticker="TEST-MARKET",
        title="Test market",
        status=KalshiMarketStatus.ACTIVE,
        last_price=Decimal("0.4300"),
        yes_bids=(
            OrderBookLevel(
                price=Decimal("0.4200"),
                quantity=Decimal("13.00"),
            ),
        ),
        yes_asks=(
            OrderBookLevel(
                price=Decimal("0.4400"),
                quantity=Decimal("17.00"),
            ),
        ),
        recent_trades=(),
        observed_at=datetime(2026, 8, 3, 19, 30, tzinfo=UTC),
    )


def test_proposes_quotes_at_best_prices(
    snapshot: MarketSnapshot,
) -> None:
    decision = decide_quotes(
        snapshot,
        quote_quantity=Decimal("2.00"),
    )

    assert decision == QuoteDecision(
        ticker="TEST-MARKET",
        yes_bid=QuoteProposal(
            price=Decimal("0.4200"),
            quantity=Decimal("2.00"),
        ),
        yes_ask=QuoteProposal(
            price=Decimal("0.4400"),
            quantity=Decimal("2.00"),
        ),
        reason=QuoteDecisionReason.TWO_SIDED_BOOK,
    )
    assert decision.should_quote is True


def test_skips_quotes_when_yes_asks_are_missing(
    snapshot: MarketSnapshot,
) -> None:
    one_sided_snapshot = replace(snapshot, yes_asks=())

    decision = decide_quotes(
        one_sided_snapshot,
        quote_quantity=Decimal("2.00"),
    )

    assert decision.yes_bid is None
    assert decision.yes_ask is None
    assert decision.reason is QuoteDecisionReason.INCOMPLETE_BOOK
    assert decision.should_quote is False


def test_skips_quotes_when_yes_bids_are_missing(
    snapshot: MarketSnapshot,
) -> None:
    one_sided_snapshot = replace(snapshot, yes_bids=())

    decision = decide_quotes(
        one_sided_snapshot,
        quote_quantity=Decimal("2.00"),
    )

    assert decision.yes_bid is None
    assert decision.yes_ask is None
    assert decision.reason is QuoteDecisionReason.INCOMPLETE_BOOK
    assert decision.should_quote is False


def test_skips_quotes_when_orderbook_is_empty(
    snapshot: MarketSnapshot,
) -> None:
    empty_snapshot = replace(
        snapshot,
        yes_bids=(),
        yes_asks=(),
    )

    decision = decide_quotes(
        empty_snapshot,
        quote_quantity=Decimal("2.00"),
    )

    assert decision.yes_bid is None
    assert decision.yes_ask is None
    assert decision.reason is QuoteDecisionReason.INCOMPLETE_BOOK
    assert decision.should_quote is False


@pytest.mark.parametrize(
    ("best_yes_bid", "best_yes_ask"),
    [
        (Decimal("0.4400"), Decimal("0.4400")),
        (Decimal("0.4500"), Decimal("0.4400")),
    ],
)
def test_skips_quotes_when_yes_book_is_crossed(
    snapshot: MarketSnapshot,
    best_yes_bid: Decimal,
    best_yes_ask: Decimal,
) -> None:
    crossed_snapshot = replace(
        snapshot,
        yes_bids=(
            OrderBookLevel(
                price=best_yes_bid,
                quantity=Decimal("13.00"),
            ),
        ),
        yes_asks=(
            OrderBookLevel(
                price=best_yes_ask,
                quantity=Decimal("17.00"),
            ),
        ),
    )

    decision = decide_quotes(
        crossed_snapshot,
        quote_quantity=Decimal("2.00"),
    )

    assert decision == QuoteDecision(
        ticker="TEST-MARKET",
        yes_bid=None,
        yes_ask=None,
        reason=QuoteDecisionReason.CROSSED_BOOK,
    )
    assert decision.should_quote is False


def test_skips_quotes_when_yes_spread_exceeds_configured_limit(
    snapshot: MarketSnapshot,
) -> None:
    wide_spread_snapshot = replace(
        snapshot,
        yes_bids=(
            OrderBookLevel(
                price=Decimal("0.0100"),
                quantity=Decimal("13.00"),
            ),
        ),
        yes_asks=(
            OrderBookLevel(
                price=Decimal("0.9900"),
                quantity=Decimal("17.00"),
            ),
        ),
    )

    decision = decide_quotes(
        wide_spread_snapshot,
        quote_quantity=Decimal("2.00"),
        max_yes_spread_dollars=Decimal("0.05"),
    )

    assert decision == QuoteDecision(
        ticker="TEST-MARKET",
        yes_bid=None,
        yes_ask=None,
        reason=QuoteDecisionReason.WIDE_SPREAD,
    )
    assert decision.should_quote is False

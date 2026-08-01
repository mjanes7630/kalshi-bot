from decimal import Decimal

import pytest

from kalshi_bot.models.market import Market


@pytest.fixture
def market() -> Market:
    return Market(
        ticker="FEDRATE-2026-SEP",
        title="Federal Funds Rate",
        best_bid=Decimal("0.42"),
        best_ask=Decimal("0.44"),
        recent_trade_prices=[
            Decimal("0.41"),
            Decimal("0.42"),
            Decimal("0.43"),
            Decimal("0.42"),
            Decimal("0.45"),
        ],
    )


def test_calculate_spread(market: Market) -> None:
    result = market.calculate_spread()

    assert result == Decimal("0.02")


def test_calculate_midpoint(market: Market) -> None:
    result = market.calculate_midpoint()

    assert result == Decimal("0.43")


def test_calculate_average_trade_price(market: Market) -> None:
    result = market.calculate_average_trade_price()

    assert result == Decimal("0.426")


@pytest.mark.parametrize(
    (
        "best_bid",
        "best_ask",
        "recent_trade_prices",
        "expected_message",
    ),
    [
        pytest.param(
            Decimal("1.01"),
            Decimal(1),
            [Decimal("0.50")],
            "best_bid must be between 0 and 1",
            id="bid-above-maximum",
        ),
        pytest.param(
            Decimal("0.42"),
            Decimal("1.01"),
            [Decimal("0.50")],
            "best_ask must be between 0 and 1",
            id="ask-above-maximum",
        ),
        pytest.param(
            Decimal("0.42"),
            Decimal("0.44"),
            [Decimal("0.41"), Decimal("1.05")],
            "trade_prices must be between 0 and 1",
            id="trade-above-maximum",
        ),
        pytest.param(
            Decimal("0.42"),
            Decimal("0.44"),
            [Decimal("-0.01"), Decimal("0.43")],
            "trade_prices must be between 0 and 1",
            id="bid-below-minimum",
        ),
    ],
)
def test_rejects_prices_outside_valid_range(
    best_bid: Decimal,
    best_ask: Decimal,
    recent_trade_prices: list[Decimal],
    expected_message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        Market(
            ticker="INVALID",
            title="Invalid Market",
            best_bid=best_bid,
            best_ask=best_ask,
            recent_trade_prices=recent_trade_prices,
        )


def test_rejects_crossed_market() -> None:
    with pytest.raises(
        ValueError,
        match="best_bid cannot be greater than best_ask",
    ):
        Market(
            ticker="INVALID",
            title="Invalid Market",
            best_bid=Decimal("0.60"),
            best_ask=Decimal("0.40"),
            recent_trade_prices=[Decimal("0.50")],
        )


def test_rejects_non_decimal_price() -> None:
    with pytest.raises(
        TypeError,
        match="best_bid must be a Decimal",
    ):
        Market(
            ticker="INVALID",
            title="Invalid Market",
            best_bid=42.5,
            best_ask=Decimal("0.44"),
            recent_trade_prices=[Decimal("0.43")],
        )


def test_average_rejects_empty_trade_list() -> None:
    market = Market(
        ticker="NO-TRADES",
        title="Market Without Trades",
        best_bid=Decimal("0.42"),
        best_ask=Decimal("0.44"),
        recent_trade_prices=[],
    )

    with pytest.raises(
        ValueError,
        match="Cannot calculate average trade price with no recent trade prices",
    ):
        market.calculate_average_trade_price()


def test_market_accepts_decimal_prices() -> None:
    market = Market(
        ticker="TEST-MARKET",
        title="Test Decimal Market",
        best_bid=Decimal("0.4500"),
        best_ask=Decimal("0.5500"),
        recent_trade_prices=[Decimal("0.5000")],
    )

    assert market.calculate_spread() == Decimal("0.1000")

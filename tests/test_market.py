import pytest

from kalshi_bot.models.market import Market

@pytest.fixture
def market() -> Market:
    return Market(
        ticker="FEDRATE-2026-SEP",
        title="Federal Funds Rate",
        best_bid=42,
        best_ask=44,
        recent_trade_prices=[41, 42, 43, 42, 45],
    )


def test_calculate_spread(market: Market) -> None:
    result = market.calculate_spread()

    assert result == 2


def test_calculate_midpoint(market: Market) -> None:
    result = market.calculate_midpoint()

    assert result == 43.0


def test_calculate_average_trade_price(market: Market) -> None:
    result = market.calculate_average_trade_price()

    assert result == 42.6


@pytest.mark.parametrize(
    (
        "best_bid",
        "best_ask",
        "recent_trade_prices",
        "expected_message",
    ),
    [
        pytest.param(
            101,
            100,
            [50],
            "best_bid must be between 0 and 100",
            id="bid-above-maximum",
        ),
        pytest.param(
            42,
            101,
            [50],
            "best_ask must be between 0 and 100",
            id="ask-above-maximum",
        ),
        pytest.param(
            42,
            44,
            [41, 105],
            "trade_prices must be between 0 and 100",
            id="trade-above-maximum",
        ),
        pytest.param(
            42,
            44,
            [-1, 43],
            "trade_prices must be between 0 and 100",
            id="bid-below-minimum",
        ),
    ]
)
def test_rejects_prices_outside_valid_range(
    best_bid: int,
    best_ask: int,
    recent_trade_prices: list[int],
    expected_message: str,
)-> None:
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
        match = "best_bid cannot be greater than best_ask",
    ):
        Market(
            ticker="INVALID",
            title="Invalid Market",
            best_bid = 60,
            best_ask = 40,
            recent_trade_prices = [50],
        )


def test_rejects_non_integer_price() -> None:
    with pytest.raises(
        TypeError,
        match = "best_bid must be an integer",
    ):
        Market(
            ticker="INVALID",
            title="Invalid Market",
            best_bid = 42.5,
            best_ask = 44,
            recent_trade_prices = [43],
        )


def test_average_rejects_empty_trade_list() -> None:
    market = Market(
        ticker = "NO-TRADES",
        title = "Market Without Trades",
        best_bid = 42,
        best_ask = 44,
        recent_trade_prices = [],
    )

    with pytest.raises(
        ValueError,
        match = "Cannot calculate average trade price with no recent trade prices"
    ):
        market.calculate_average_trade_price()
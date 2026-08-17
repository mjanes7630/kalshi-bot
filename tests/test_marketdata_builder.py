from datetime import UTC, datetime
from decimal import Decimal

import pytest

from kalshi_bot.api.models import (
    GetMarketOrderbookResponse,
    GetTradesResponse,
    KalshiMarket,
    KalshiMarketStatus,
    KalshiOrderbook,
    KalshiTrade,
)
from kalshi_bot.marketdata.builder import build_market_snapshot
from kalshi_bot.marketdata.models import MarketTrade, OrderBookLevel

OBSERVED_AT = datetime(2026, 8, 2, 19, 30, tzinfo=UTC)


@pytest.fixture
def market() -> KalshiMarket:
    return KalshiMarket(
        ticker="TEST-MARKET",
        title="Test market",
        status=KalshiMarketStatus.ACTIVE,
        yes_bid_dollars=Decimal("0.4200"),
        yes_ask_dollars=Decimal("0.4400"),
        no_bid_dollars=Decimal("0.5600"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4300"),
    )


@pytest.fixture
def orderbook_response() -> GetMarketOrderbookResponse:
    return GetMarketOrderbookResponse(
        orderbook_fp=KalshiOrderbook(
            yes_dollars=[
                (Decimal("0.3900"), Decimal("8.00")),
                (Decimal("0.4200"), Decimal("13.00")),
                (Decimal("0.4100"), Decimal("10.00")),
            ],
            no_dollars=[
                (Decimal("0.5500"), Decimal("20.00")),
                (Decimal("0.5600"), Decimal("17.00")),
            ],
        )
    )


@pytest.fixture
def trades_response() -> GetTradesResponse:
    return GetTradesResponse(
        trades=[
            KalshiTrade(
                trade_id="trade-123",
                ticker="TEST-MARKET",
                count_fp=Decimal("2.00"),
                yes_price_dollars=Decimal("0.4300"),
                no_price_dollars=Decimal("0.5700"),
                created_time=datetime(
                    2026,
                    8,
                    2,
                    19,
                    29,
                    tzinfo=UTC,
                ),
                is_block_trade=False,
            ),
            KalshiTrade(
                trade_id="other-trade",
                ticker="OTHER-MARKET",
                count_fp=Decimal("5.00"),
                yes_price_dollars=Decimal("0.6000"),
                no_price_dollars=Decimal("0.4000"),
                created_time=datetime(
                    2026,
                    8,
                    2,
                    19,
                    28,
                    tzinfo=UTC,
                ),
                is_block_trade=False,
            ),
        ],
        cursor="",
    )


def test_builds_snapshot_metadata_and_matching_trades(
    market: KalshiMarket,
    orderbook_response: GetMarketOrderbookResponse,
    trades_response: GetTradesResponse,
) -> None:
    snapshot = build_market_snapshot(
        market,
        orderbook_response,
        trades_response,
        observed_at=OBSERVED_AT,
    )

    assert snapshot.ticker == "TEST-MARKET"
    assert snapshot.title == "Test market"
    assert snapshot.status is KalshiMarketStatus.ACTIVE
    assert snapshot.last_price == Decimal("0.4300")
    assert snapshot.observed_at == OBSERVED_AT
    assert snapshot.recent_trades == (
        MarketTrade(
            trade_id="trade-123",
            price=Decimal("0.4300"),
            quantity=Decimal("2.00"),
            created_time=datetime(
                2026,
                8,
                2,
                19,
                29,
                tzinfo=UTC,
            ),
            is_block_trade=False,
        ),
    )


def test_orders_yes_bids_highest_price_first(
    market: KalshiMarket,
    orderbook_response: GetMarketOrderbookResponse,
    trades_response: GetTradesResponse,
) -> None:
    snapshot = build_market_snapshot(
        market,
        orderbook_response,
        trades_response,
        observed_at=OBSERVED_AT,
    )

    assert snapshot.yes_bids == (
        OrderBookLevel(Decimal("0.4200"), Decimal("13.00")),
        OrderBookLevel(Decimal("0.4100"), Decimal("10.00")),
        OrderBookLevel(Decimal("0.3900"), Decimal("8.00")),
    )


def test_converts_no_bids_to_ordered_yes_asks(
    market: KalshiMarket,
    orderbook_response: GetMarketOrderbookResponse,
    trades_response: GetTradesResponse,
) -> None:
    snapshot = build_market_snapshot(
        market,
        orderbook_response,
        trades_response,
        observed_at=OBSERVED_AT,
    )

    assert snapshot.yes_asks == (
        OrderBookLevel(Decimal("0.4400"), Decimal("17.00")),
        OrderBookLevel(Decimal("0.4500"), Decimal("20.00")),
    )

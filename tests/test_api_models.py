from decimal import Decimal

from kalshi_bot.api.models import (
    GetMarketOrderbookResponse,
    GetMarketsResponse,
    GetPositionsResponse,
    GetTradesResponse,
    KalshiMarket,
)


def test_kalshi_market_parses_fixed_point_price_strings() -> None:
    market = KalshiMarket.model_validate(
        {
            "ticker": "TEST-MARKET",
            "title": "Test market",
            "yes_bid_dollars": "0.3700",
            "yes_ask_dollars": "0.4200",
            "no_bid_dollars": "0.5800",
            "no_ask_dollars": "0.6300",
            "last_price_dollars": "0.4000",
            "event_ticker": "TEST-EVENT",
        }
    )

    assert market.yes_bid_dollars == Decimal("0.3700")
    assert market.yes_ask_dollars == Decimal("0.4200")
    assert market.no_bid_dollars == Decimal("0.5800")
    assert market.no_ask_dollars == Decimal("0.6300")
    assert market.last_price_dollars == Decimal("0.4000")


def test_get_markets_response_parses_markets_and_cursor() -> None:
    response = GetMarketsResponse.model_validate(
        {
            "markets": [
                {
                    "ticker": "TEST-MARKET",
                    "title": "Test market",
                    "yes_bid_dollars": "0.3700",
                    "yes_ask_dollars": "0.4200",
                    "no_bid_dollars": "0.5800",
                    "no_ask_dollars": "0.6300",
                    "last_price_dollars": "0.4000",
                }
            ],
            "cursor": "next-page-token",
        }
    )

    assert len(response.markets) == 1
    assert response.markets[0].ticker == "TEST-MARKET"
    assert response.cursor == "next-page-token"


def test_get_market_orderbook_response_parses_fixed_point_levels() -> None:
    response = GetMarketOrderbookResponse.model_validate(
        {
            "orderbook_fp": {
                "yes_dollars": [
                    ["0.3700", "125.00"],
                    ["0.3600", "40.50"],
                ],
                "no_dollars": [
                    ["0.5800", "80.00"],
                ],
            }
        }
    )

    assert response.orderbook_fp.yes_dollars == [
        (Decimal("0.3700"), Decimal("125.00")),
        (Decimal("0.3600"), Decimal("40.50")),
    ]
    assert response.orderbook_fp.no_dollars == [
        (Decimal("0.5800"), Decimal("80.00")),
    ]


def test_get_trades_response_parses_fixed_point_values() -> None:
    response = GetTradesResponse.model_validate(
        {
            "trades": [
                {
                    "trade_id": "trade-123",
                    "ticker": "TEST-MARKET",
                    "count_fp": "12.50",
                    "yes_price_dollars": "0.4100",
                    "no_price_dollars": "0.5900",
                    "created_time": "2026-07-31T18:45:00Z",
                    "is_block_trade": False,
                }
            ],
            "cursor": "next-page",
        }
    )

    trade = response.trades[0]

    assert trade.trade_id == "trade-123"
    assert trade.ticker == "TEST-MARKET"
    assert trade.count_fp == Decimal("12.50")
    assert trade.yes_price_dollars == Decimal("0.4100")
    assert trade.no_price_dollars == Decimal("0.5900")
    assert trade.created_time.isoformat() == "2026-07-31T18:45:00+00:00"
    assert trade.is_block_trade is False
    assert response.cursor == "next-page"


def test_get_positions_response_parses_fixed_point_values() -> None:
    response = GetPositionsResponse.model_validate(
        {
            "market_positions": [
                {
                    "ticker": "TEST-MARKET",
                    "total_traded_dollars": "7.2500",
                    "position_fp": "-5.00",
                    "market_exposure_dollars": "2.0500",
                    "realized_pnl_dollars": "-0.3000",
                    "fees_paid_dollars": "0.1200",
                    "last_updated_ts": "2026-07-31T19:30:00Z",
                }
            ],
            "event_positions": [
                {
                    "event_ticker": "TEST-EVENT",
                    "total_cost_dollars": "4.2000",
                    "total_cost_shares_fp": "8.00",
                    "event_exposure_dollars": "3.1500",
                    "realized_pnl_dollars": "-0.3000",
                    "fees_paid_dollars": "0.1500",
                }
            ],
            "cursor": "next-page",
        }
    )

    market_position = response.market_positions[0]
    event_position = response.event_positions[0]

    assert market_position.ticker == "TEST-MARKET"
    assert market_position.total_traded_dollars == Decimal("7.2500")
    assert market_position.position_fp == Decimal("-5.00")
    assert market_position.market_exposure_dollars == Decimal("2.0500")
    assert market_position.realized_pnl_dollars == Decimal("-0.3000")
    assert market_position.fees_paid_dollars == Decimal("0.1200")
    assert market_position.last_updated_ts.isoformat() == "2026-07-31T19:30:00+00:00"

    assert event_position.event_ticker == "TEST-EVENT"
    assert event_position.total_cost_dollars == Decimal("4.2000")
    assert event_position.total_cost_shares_fp == Decimal("8.00")
    assert event_position.event_exposure_dollars == Decimal("3.1500")
    assert event_position.realized_pnl_dollars == Decimal("-0.3000")
    assert event_position.fees_paid_dollars == Decimal("0.1500")
    assert response.cursor == "next-page"

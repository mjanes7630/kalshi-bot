from decimal import Decimal

from kalshi_bot.api.models import (
    CancelOrderResponse,
    CreateOrderRequest,
    CreateOrderResponse,
    GetMarketOrderbookResponse,
    GetMarketResponse,
    GetMarketsResponse,
    GetOrderResponse,
    GetOrdersResponse,
    GetPositionsResponse,
    GetTradesResponse,
    KalshiMarket,
    KalshiOrderSide,
    KalshiSelfTradePreventionType,
    KalshiTimeInForce,
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


def test_get_orders_response_parses_fixed_point_values() -> None:
    response = GetOrdersResponse.model_validate(
        {
            "orders": [
                {
                    "order_id": "order-123",
                    "ticker": "TEST-MARKET",
                    "side": "bid",
                    "yes_price_dollars": "0.4200",
                    "fill_count_fp": "0.50",
                    "remaining_count_fp": "1.50",
                    "initial_count_fp": "2.00",
                    "future_field": "ignored",
                }
            ],
            "cursor": "next-page",
        }
    )

    order = response.orders[0]

    assert order.order_id == "order-123"
    assert order.ticker == "TEST-MARKET"
    assert order.yes_price_dollars == Decimal("0.4200")
    assert order.fill_count_fp == Decimal("0.50")
    assert order.remaining_count_fp == Decimal("1.50")
    assert order.initial_count_fp == Decimal("2.00")
    assert order.client_order_id is None
    assert response.cursor == "next-page"


def test_get_order_response_parses_order() -> None:
    response = GetOrderResponse.model_validate(
        {
            "order": {
                "order_id": "order-123",
                "client_order_id": "client-order-123",
                "ticker": "TEST-MARKET",
                "side": "bid",
                "yes_price_dollars": "0.4200",
                "fill_count_fp": "0.00",
                "remaining_count_fp": "1.00",
                "initial_count_fp": "1.00",
                "future_field": "ignored",
            }
        }
    )

    order = response.order

    assert order.order_id == "order-123"
    assert order.client_order_id == "client-order-123"
    assert order.ticker == "TEST-MARKET"
    assert order.yes_price_dollars == Decimal("0.4200")
    assert order.fill_count_fp == Decimal("0.00")
    assert order.remaining_count_fp == Decimal("1.00")
    assert order.initial_count_fp == Decimal("1.00")


def test_create_order_request_uses_safe_defaults() -> None:
    request = CreateOrderRequest(
        ticker="TEST-MARKET",
        client_order_id="client-order-123",
        side=KalshiOrderSide.BID,
        count=Decimal("2.00"),
        price=Decimal("0.4200"),
    )

    assert request.time_in_force is KalshiTimeInForce.GOOD_TILL_CANCELED
    assert (
        request.self_trade_prevention_type
        is KalshiSelfTradePreventionType.TAKER_AT_CROSS
    )
    assert request.post_only is True
    assert request.cancel_order_on_pause is True

    assert request.model_dump(mode="json") == {
        "ticker": "TEST-MARKET",
        "client_order_id": "client-order-123",
        "side": "bid",
        "count": "2.00",
        "price": "0.4200",
        "time_in_force": "good_till_canceled",
        "self_trade_prevention_type": "taker_at_cross",
        "post_only": True,
        "cancel_order_on_pause": True,
    }


def test_create_order_response_parses_fixed_point_values() -> None:
    response = CreateOrderResponse.model_validate(
        {
            "order_id": "order-123",
            "client_order_id": "client-order-123",
            "fill_count": "0.50",
            "remaining_count": "1.50",
            "ts_ms": 1785970800000,
            "average_fill_price": "0.4200",
            "average_fee_paid": "0.0012",
            "future_field": "ignored",
        }
    )

    assert response.order_id == "order-123"
    assert response.client_order_id == "client-order-123"
    assert response.fill_count == Decimal("0.50")
    assert response.remaining_count == Decimal("1.50")
    assert response.ts_ms == 1785970800000
    assert response.average_fill_price == Decimal("0.4200")
    assert response.average_fee_paid == Decimal("0.0012")


def test_create_order_response_preserves_exchange_order_id() -> None:
    response = CreateOrderResponse.model_validate(
        {
            "order_id": "exchange-order-id",
            "client_order_id": "client-order-id",
            "fill_count": "0.00",
            "remaining_count": "1.00",
            "ts_ms": 1_715_793_600_123,
        }
    )

    assert response.order_id == "exchange-order-id"
    assert response.client_order_id == "client-order-id"


def test_cancel_order_response_parses_fixed_point_values() -> None:
    response = CancelOrderResponse.model_validate(
        {
            "order_id": "order-123",
            "client_order_id": "client-order-123",
            "reduced_by": "1.50",
            "ts_ms": 1785970800000,
            "future_field": "ignored",
        }
    )

    assert response.order_id == "order-123"
    assert response.client_order_id == "client-order-123"
    assert response.reduced_by == Decimal("1.50")
    assert response.ts_ms == 1785970800000


def test_get_market_response_parses_market() -> None:
    response = GetMarketResponse.model_validate(
        {
            "market": {
                "ticker": "TEST-MARKET",
                "title": "Test market",
                "yes_bid_dollars": "0.3700",
                "yes_ask_dollars": "0.4200",
                "no_bid_dollars": "0.5800",
                "no_ask_dollars": "0.6300",
                "last_price_dollars": "0.4000",
            }
        }
    )

    assert response.market.ticker == "TEST-MARKET"
    assert response.market.yes_bid_dollars == Decimal("0.3700")

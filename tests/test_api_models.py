from decimal import Decimal

from kalshi_bot.api.models import GetMarketsResponse, KalshiMarket


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

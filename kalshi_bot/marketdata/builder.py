from datetime import datetime
from decimal import Decimal

from kalshi_bot.api.models import (
    GetMarketOrderbookResponse,
    GetTradesResponse,
    KalshiMarket,
)
from kalshi_bot.marketdata.models import (
    MarketSnapshot,
    MarketTrade,
    OrderBookLevel,
)


def build_market_snapshot(
    market: KalshiMarket,
    orderbook_response: GetMarketOrderbookResponse,
    trades_response: GetTradesResponse,
    *,
    observed_at: datetime,
) -> MarketSnapshot:
    yes_bids = tuple(
        OrderBookLevel(price=price, quantity=quantity)
        for price, quantity in sorted(
            orderbook_response.orderbook_fp.yes_dollars,
            key=lambda level: level[0],
            reverse=True,
        )
    )

    yes_asks = tuple(
        sorted(
            (
                OrderBookLevel(
                    price=Decimal(1) - no_bid_price,
                    quantity=quantity,
                )
                for no_bid_price, quantity in (
                    orderbook_response.orderbook_fp.no_dollars
                )
            ),
            key=lambda level: level.price,
        )
    )

    recent_trades = tuple(
        MarketTrade(
            trade_id=trade.trade_id,
            price=trade.yes_price_dollars,
            quantity=trade.count_fp,
            created_time=trade.created_time,
            is_block_trade=trade.is_block_trade,
        )
        for trade in trades_response.trades
        if trade.ticker == market.ticker
    )

    return MarketSnapshot(
        ticker=market.ticker,
        title=market.title,
        last_price=market.last_price_dollars,
        yes_bids=yes_bids,
        yes_asks=yes_asks,
        recent_trades=recent_trades,
        observed_at=observed_at,
    )

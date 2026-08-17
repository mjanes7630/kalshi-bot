from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from kalshi_bot.api.models import KalshiMarketStatus


@dataclass(frozen=True)
class OrderBookLevel:
    price: Decimal
    quantity: Decimal


@dataclass(frozen=True)
class MarketTrade:
    trade_id: str
    price: Decimal
    quantity: Decimal
    created_time: datetime
    is_block_trade: bool


@dataclass(frozen=True)
class MarketSnapshot:
    """Strategy-ready market data with levels ordered best-first."""

    ticker: str
    title: str
    status: KalshiMarketStatus
    last_price: Decimal
    yes_bids: tuple[OrderBookLevel, ...]
    yes_asks: tuple[OrderBookLevel, ...]
    recent_trades: tuple[MarketTrade, ...]
    observed_at: datetime

    @property
    def best_yes_bid(self) -> OrderBookLevel | None:
        return self.yes_bids[0] if self.yes_bids else None

    @property
    def best_yes_ask(self) -> OrderBookLevel | None:
        return self.yes_asks[0] if self.yes_asks else None

    @property
    def yes_spread(self) -> Decimal | None:
        if self.best_yes_bid is None or self.best_yes_ask is None:
            return None

        return self.best_yes_ask.price - self.best_yes_bid.price

    @property
    def yes_midpoint(self) -> Decimal | None:
        if self.best_yes_bid is None or self.best_yes_ask is None:
            return None

        return (self.best_yes_bid.price + self.best_yes_ask.price) / Decimal(2)

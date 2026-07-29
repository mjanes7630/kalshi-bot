from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Market:
    ticker: str
    title: str
    best_bid: Decimal
    best_ask: Decimal
    recent_trade_prices: list[Decimal]

    def __post_init__(self) -> None:
        self._validate_price(self.best_bid, "best_bid")
        self._validate_price(self.best_ask, "best_ask")

        for trade_price in self.recent_trade_prices:
            self._validate_price(trade_price, "trade_prices")

        if self.best_bid >= self.best_ask:
            raise ValueError(
                "best_bid cannot be greater than best_ask"
                f"Received bid={self.best_bid}, ask={self.best_ask}"
            )

    @staticmethod
    def _validate_price(price: object, field_name: str) -> None:
        if not isinstance(price, Decimal):
            raise TypeError(
                f"{field_name} must be an Decimal.  "
                f"Received type: {type(price).__name__}"
            )

        if not Decimal(0) <= price <= Decimal(1):
            raise ValueError(
                f"{field_name} must be between 0 and 100.  Received: {price}"
            )

    def calculate_spread(self) -> Decimal:
        return self.best_ask - self.best_bid

    def calculate_midpoint(self) -> Decimal:
        return (self.best_bid + self.best_ask) / 2

    def calculate_average_trade_price(self) -> Decimal:
        if not self.recent_trade_prices:
            raise ValueError(
                "Cannot calculate average trade price with no recent trade prices"
            )

        return sum(self.recent_trade_prices) / len(self.recent_trade_prices)

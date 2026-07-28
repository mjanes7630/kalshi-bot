from dataclasses import dataclass


@dataclass
class Market:
    ticker: str
    title: str
    best_bid: int
    best_ask: int
    recent_trade_prices: list[int]

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
    def _validate_price(price: int, field_name: str) -> None:
        if not isinstance(price, int) or isinstance(price, bool):
            raise TypeError(
                f"{field_name} must be an integer.  "
                f"Received type: {type(price).__name__}"
            )

        if not 0 <= price <= 100:
            raise ValueError(
                f"{field_name} must be between 0 and 100.  Received: {price}"
            )

    def calculate_spread(self) -> int:
        return self.best_ask - self.best_bid

    def calculate_midpoint(self) -> float:
        return (self.best_bid + self.best_ask) / 2

    def calculate_average_trade_price(self) -> float:
        if not self.recent_trade_prices:
            raise ValueError(
                "Cannot calculate average trade price with no recent trade prices"
            )

        return sum(self.recent_trade_prices) / len(self.recent_trade_prices)

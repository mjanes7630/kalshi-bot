from dataclasses import dataclass

@dataclass
class Market:
    ticker: str
    title: str
    best_bid: int
    best_ask: int
    recent_trade_prices: list[int]


    def calculate_spread(self) -> int:
        return self.best_ask - self.best_bid

    def calculate_midpoint(self) -> float:
        return (self.best_bid + self.best_ask) / 2

    def calculate_average_trade_price(self) -> float:
        if not self.recent_trade_prices:
            raise ValueError("Cannot calculate average trade price with no recent trade prices")

        return sum(self.recent_trade_prices) / len(self.recent_trade_prices)
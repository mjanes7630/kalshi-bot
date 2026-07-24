from kalshi_bot.models.market import Market

def classify_trade(price: int, midpoint: float) -> str:
    if price > midpoint:
        return "Above Midpoint"
    elif price < midpoint:
        return "Below Midpoint"
    else:
        return "At Midpoint"


def display_trade_prices(prices: list[int], midpoint: float) -> None:
    for price in prices:
        classification = classify_trade(price, midpoint)
        print(f"Trade Price: {price} - {classification}")


def main() -> None:
    market = Market(
        ticker="FEDRATE-2026-SEP",
        title="Federal Funds Rate",
        best_bid=42,
        best_ask=44,
        recent_trade_prices=[41, 42, 43, 42, 45],
    )

    spread = market.calculate_spread()
    midpoint = market.calculate_midpoint()
    average_price = market.calculate_average_trade_price()

    print(f"Ticker: {market.ticker}")
    print(f"Title: {market.title}")
    print(f"Best Bid: {market.best_bid}")
    print(f"Best Ask: {market.best_ask}")
    print(f"Spread: {spread}")
    print(f"Average Price: {average_price:.2f}")

    display_trade_prices(market.recent_trade_prices, midpoint)


if __name__ == "__main__":
    main()
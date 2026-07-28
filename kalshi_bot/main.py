import structlog

from kalshi_bot.config import Settings
from kalshi_bot.logging_config import configure_logging
from kalshi_bot.models.market import Market

logger = structlog.get_logger(__name__)


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

        logger.info(
            "trade_price_classified",
            price=price,
            classification=classification,
        )


def main() -> None:
    settings = Settings()
    configure_logging(settings)

    logger.info(
        "application_started",
        environment=settings.environment,
        log_level=settings.log_level,
    )

    try:
        market = Market(
            ticker="FEDRATE-2026-SEP",
            title="Federal Funds Rate",
            best_bid=42,
            best_ask=44,
            recent_trade_prices=[41, 42, 43, 42, 45],
        )
    except (TypeError, ValueError) as error:
        logger.error(
            "market_creation_failed",
            error=str(error),
            error_type=type(error).__name__,
        )
        return

    spread = market.calculate_spread()
    midpoint = market.calculate_midpoint()
    average_price = market.calculate_average_trade_price()

    logger.info(
        "market_analyzed",
        ticker=market.ticker,
        title=market.title,
        best_bid=market.best_bid,
        best_ask=market.best_ask,
        spread=spread,
        midpoint=midpoint,
        average_price=round(average_price, 2),
    )

    display_trade_prices(market.recent_trade_prices, midpoint)


if __name__ == "__main__":
    main()

import asyncio
from decimal import Decimal

import httpx
import structlog

from kalshi_bot.api.auth import load_private_key
from kalshi_bot.api.client import KALSHI_API_BASE_URL, KalshiClient
from kalshi_bot.config import Settings
from kalshi_bot.logging_config import configure_logging
from kalshi_bot.models.market import Market

logger = structlog.get_logger(__name__)


def classify_trade(price: Decimal, midpoint: Decimal) -> str:
    if price > midpoint:
        return "Above Midpoint"
    elif price < midpoint:
        return "Below Midpoint"
    else:
        return "At Midpoint"


def display_trade_prices(prices: list[Decimal], midpoint: Decimal) -> None:
    for price in prices:
        classification = classify_trade(price, midpoint)

        logger.info(
            "trade_price_classified",
            price=price,
            classification=classification,
        )


async def retrieve_demo_balence(settings: Settings) -> None:
    if settings.api_key_id is None:
        raise ValueError("KALSHI_BOT_API_KEY_ID is required.")

    if settings.private_key_path is None:
        raise ValueError("KALSHI_BOT_PRIVATE_KEY_PATH is required.")

    private_key = load_private_key(settings.private_key_path)
    async with httpx.AsyncClient(
        base_url=KALSHI_API_BASE_URL,
        timeout=10.0,
    ) as http_client:
        client = KalshiClient(
            http_client,
            api_key_id=settings.api_key_id,
            private_key=private_key,
        )

        balance = await client.get_balance()

    logger.info(
        "demo_balence_retrieved",
        balance_dollars=str(balance.balance_dollars),
        portfolio_value_cents=balance.portfolio_value,
        updated_ts=balance.updated_ts,
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
            best_bid=Decimal("0.42"),
            best_ask=Decimal("0.44"),
            recent_trade_prices=[
                Decimal("0.41"),
                Decimal("0.42"),
                Decimal("0.43"),
                Decimal("0.42"),
                Decimal("0.45"),
            ],
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

    try:
        asyncio.run(retrieve_demo_balence(settings))
    except (OSError, ValueError, httpx.HTTPError) as error:
        logger.error(
            "demo_balance_retrieval_failed",
            error=str(error),
            error_type=type(error).__name__,
        )


if __name__ == "__main__":
    main()

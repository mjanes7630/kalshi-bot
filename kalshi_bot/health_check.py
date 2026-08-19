import asyncio

from kalshi_bot.api.session import authenticated_kalshi_client
from kalshi_bot.config import Settings
from kalshi_bot.health import MarketHealth, run_market_health_check
from kalshi_bot.logging_config import configure_logging


async def run_demo_market_health_check(
    settings: Settings,
) -> MarketHealth:
    if settings.demo_market_ticker is None:
        raise ValueError("KALSHI_BOT_DEMO_MARKET_TICKER is required.")

    async with authenticated_kalshi_client(settings) as client:
        return await run_market_health_check(
            client=client,
            ticker=settings.demo_market_ticker,
        )


def main() -> None:
    settings = Settings()
    configure_logging(settings)
    asyncio.run(run_demo_market_health_check(settings))


if __name__ == "__main__":
    main()

import asyncio

import structlog

from kalshi_bot.api.models import KalshiMarket
from kalshi_bot.api.session import authenticated_kalshi_client
from kalshi_bot.config import Settings
from kalshi_bot.logging_config import configure_logging
from kalshi_bot.market_selection import (
    find_open_eligible_markets,
    is_quoteable_yes_orderbook,
)

logger = structlog.get_logger()


async def run_demo_market_scan(
    settings: Settings,
) -> tuple[KalshiMarket, ...]:
    async with authenticated_kalshi_client(settings) as client:
        preliminary_candidates = await find_open_eligible_markets(
            client,
            excluded_categories=frozenset(
                settings.demo_market_scan_excluded_categories.split(",")
            ),
            max_results=settings.demo_market_scan_max_orderbook_checks,
            max_pages=settings.demo_market_scan_max_pages,
            page_delay_seconds=settings.demo_market_scan_page_delay_seconds,
        )

        markets: list[KalshiMarket] = []

        for candidate_index, market in enumerate(preliminary_candidates):
            live_orderbook = await client.get_market_orderbook(
                ticker=market.ticker,
                depth=1,
            )

            if is_quoteable_yes_orderbook(
                live_orderbook,
                max_yes_spread_dollars=settings.demo_max_yes_spread_dollars,
            ):
                markets.append(market)

                if len(markets) == settings.demo_market_scan_max_results:
                    break

            if candidate_index < len(preliminary_candidates) - 1:
                await asyncio.sleep(
                    float(settings.demo_market_scan_page_delay_seconds),
                )

    for market in markets:
        logger.info(
            "quoteable_demo_market_found",
            ticker=market.ticker,
            title=market.title,
            yes_bid_dollars=str(market.yes_bid_dollars),
            yes_ask_dollars=str(market.yes_ask_dollars),
        )

    return tuple(markets)


def main() -> None:
    settings = Settings()
    configure_logging(settings)
    asyncio.run(run_demo_market_scan(settings))


if __name__ == "__main__":
    main()

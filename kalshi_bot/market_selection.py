import asyncio
from decimal import Decimal

from kalshi_bot.api.client import KalshiClient
from kalshi_bot.api.models import (
    GetMarketOrderbookResponse,
    KalshiMarket,
    KalshiMarketStatus,
)


def select_quoteable_markets(
    markets: list[KalshiMarket],
    *,
    max_yes_spread_dollars: Decimal = Decimal("0.05"),
) -> tuple[KalshiMarket, ...]:
    if max_yes_spread_dollars < 0:
        raise ValueError("max_yes_spread_dollars cannot be negative.")

    return tuple(
        market
        for market in markets
        if market.status is KalshiMarketStatus.ACTIVE
        and market.yes_bid_dollars > 0
        and market.yes_ask_dollars > 0
        and market.yes_bid_dollars < market.yes_ask_dollars
        and market.yes_ask_dollars - market.yes_bid_dollars <= max_yes_spread_dollars
    )


async def find_quoteable_markets(
    client: KalshiClient,
    *,
    max_results: int = 10,
    max_pages: int = 10,
    page_delay_seconds: Decimal = Decimal("0.25"),
    max_yes_spread_dollars: Decimal = Decimal("0.05"),
) -> tuple[KalshiMarket, ...]:
    if max_results < 1:
        raise ValueError("max_results must be at least 1")

    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")

    if page_delay_seconds < 0:
        raise ValueError("page_delay_seconds cannot be negative.")

    if max_yes_spread_dollars < 0:
        raise ValueError("max_yes_spread_dollars cannot be negative.")

    quoteable_markets: list[KalshiMarket] = []
    seen_cursor: set[str] = set()
    cursor: str | None = None

    for _ in range(max_pages):
        request_arguments: dict[str, int | str] = {
            "limit": 1000,
            "status": "open",
        }

        if cursor is not None:
            request_arguments["cursor"] = cursor

        response = await client.get_markets(**request_arguments)

        for market in select_quoteable_markets(
            response.markets,
            max_yes_spread_dollars=max_yes_spread_dollars,
        ):
            quoteable_markets.append(market)

            if len(quoteable_markets) == max_results:
                return tuple(quoteable_markets)

        if not response.cursor:
            return tuple(quoteable_markets)

        if response.cursor in seen_cursor:
            raise ValueError("Kalshi returned a repeated market-pagination cursor.")

        seen_cursor.add(response.cursor)
        cursor = response.cursor

        await asyncio.sleep(float(page_delay_seconds))

    return tuple(quoteable_markets)


def is_quoteable_yes_orderbook(
    orderbook_response: GetMarketOrderbookResponse,
    *,
    max_yes_spread_dollars: Decimal,
) -> bool:
    if max_yes_spread_dollars < 0:
        raise ValueError("max_yes_spread_dollars must be greater than zero.")

    yes_bids = orderbook_response.orderbook_fp.yes_dollars
    no_bids = orderbook_response.orderbook_fp.no_dollars

    if not yes_bids or not no_bids:
        return False

    best_yes_bid = max(price for price, _ in yes_bids)
    best_yes_ask = min(Decimal(1) - no_bid_price for no_bid_price, _ in no_bids)

    return (
        best_yes_bid > 0
        and best_yes_ask > 0
        and best_yes_bid < best_yes_ask
        and best_yes_ask - best_yes_bid <= max_yes_spread_dollars
    )


async def find_open_markets(
    client: KalshiClient,
    *,
    max_results: int,
    max_pages: int,
    page_delay_seconds: Decimal = Decimal("0.25"),
) -> tuple[KalshiMarket, ...]:
    if max_results < 1:
        raise ValueError("max_results must be at least 1")

    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")

    if page_delay_seconds < 0:
        raise ValueError("page_delay_seconds cannot be negative.")

    open_markets: list[KalshiMarket] = []
    seen_cursor: set[str] = set()
    cursor: str | None = None

    for _ in range(max_pages):
        request_arguments: dict[str, int | str] = {
            "limit": 1000,
            "status": "open",
            "mve_filter": "exclude",
        }

        if cursor is not None:
            request_arguments["cursor"] = cursor

        response = await client.get_markets(**request_arguments)

        for market in response.markets:
            if market.status is not KalshiMarketStatus.ACTIVE:
                continue

            open_markets.append(market)

            if len(open_markets) == max_results:
                return tuple(open_markets)

        if not response.cursor:
            return tuple(open_markets)

        if response.cursor in seen_cursor:
            raise ValueError("Kalshi returned a repeated market-pagination cursor.")

        seen_cursor.add(response.cursor)
        cursor = response.cursor

        await asyncio.sleep(float(page_delay_seconds))

    return tuple(open_markets)


async def find_open_eligible_markets(
    client: KalshiClient,
    *,
    excluded_categories: frozenset[str],
    max_results: int,
    max_pages: int,
    page_delay_seconds: Decimal,
) -> tuple[KalshiMarket, ...]:
    normalized_excluded_categories = {
        category.casefold() for category in excluded_categories
    }

    eligable_markets: list[KalshiMarket] = []
    cursor: str | None = None
    seen_cursor: set[str] = set()

    for page_number in range(max_pages):
        if cursor is None:
            response = await client.get_events(
                limit=200,
                status="open",
                with_nested_markets=True,
            )
        else:
            response = await client.get_events(
                limit=200,
                status="open",
                cursor=cursor,
                with_nested_markets=True,
            )

        for event in response.events:
            if event.category.casefold() in normalized_excluded_categories:
                continue

            for market in event.markets:
                if market.status is not KalshiMarketStatus.ACTIVE:
                    continue

                eligable_markets.append(market)

                if len(eligable_markets) >= max_results:
                    return tuple(eligable_markets)

        next_cursor = response.cursor

        if not next_cursor or next_cursor in seen_cursor:
            break

        seen_cursor.add(next_cursor)
        cursor = next_cursor

        if page_number < max_pages - 1:
            await asyncio.sleep(float(page_delay_seconds))

    return tuple(eligable_markets)

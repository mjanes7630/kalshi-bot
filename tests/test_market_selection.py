import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, call, patch

from kalshi_bot.api.client import KalshiClient
from kalshi_bot.api.models import (
    GetEventsResponse,
    GetMarketOrderbookResponse,
    GetMarketsResponse,
    KalshiEvent,
    KalshiMarket,
    KalshiMarketStatus,
)
from kalshi_bot.market_selection import (
    find_open_eligible_markets,
    find_open_markets,
    find_quoteable_markets,
    is_quoteable_yes_orderbook,
    select_quoteable_markets,
)


def test_select_quoteable_markets_returns_only_active_two_sided_markets() -> None:
    quoteable_market = KalshiMarket(
        ticker="QUOTEABLE-MARKET",
        title="Quoteable market",
        yes_bid_dollars=Decimal("0.4200"),
        yes_ask_dollars=Decimal("0.4300"),
        no_bid_dollars=Decimal("0.5700"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4250"),
        status=KalshiMarketStatus.ACTIVE,
    )
    inactive_market = KalshiMarket(
        ticker="INACTIVE-MARKET",
        title="Inactive market",
        yes_bid_dollars=Decimal("0.4200"),
        yes_ask_dollars=Decimal("0.4300"),
        no_bid_dollars=Decimal("0.5700"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4250"),
        status=KalshiMarketStatus.INACTIVE,
    )
    incomplete_market = KalshiMarket(
        ticker="INCOMPLETE-MARKET",
        title="Incomplete market",
        yes_bid_dollars=Decimal("0.4200"),
        yes_ask_dollars=Decimal("0.0000"),
        no_bid_dollars=Decimal("0.5700"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4250"),
        status=KalshiMarketStatus.ACTIVE,
    )
    crossed_market = KalshiMarket(
        ticker="CROSSED-MARKET",
        title="Crossed market",
        yes_bid_dollars=Decimal("0.4300"),
        yes_ask_dollars=Decimal("0.4200"),
        no_bid_dollars=Decimal("0.5700"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4250"),
        status=KalshiMarketStatus.ACTIVE,
    )

    result = select_quoteable_markets(
        [
            quoteable_market,
            inactive_market,
            incomplete_market,
            crossed_market,
        ],
    )

    assert result == (quoteable_market,)


def test_find_quoteable_markets_checks_every_page() -> None:
    incomplete_market = KalshiMarket(
        ticker="INCOMPLETE-MARKET",
        title="Incomplete market",
        yes_bid_dollars=Decimal("0.4200"),
        yes_ask_dollars=Decimal("0.0000"),
        no_bid_dollars=Decimal("0.5700"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4250"),
        status=KalshiMarketStatus.ACTIVE,
    )
    quoteable_market = KalshiMarket(
        ticker="QUOTEABLE-MARKET",
        title="Quoteable market",
        yes_bid_dollars=Decimal("0.4200"),
        yes_ask_dollars=Decimal("0.4300"),
        no_bid_dollars=Decimal("0.5700"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4250"),
        status=KalshiMarketStatus.ACTIVE,
    )

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.get_markets.side_effect = [
            GetMarketsResponse(
                markets=[incomplete_market],
                cursor="next-page",
            ),
            GetMarketsResponse(
                markets=[quoteable_market],
                cursor="",
            ),
        ]

        result = await find_quoteable_markets(
            client,
            max_results=1,
            max_pages=2,
            page_delay_seconds=Decimal("0.0"),
        )

        assert result == (quoteable_market,)
        assert client.get_markets.await_args_list == [
            call(limit=1000, status="open"),
            call(
                limit=1000,
                status="open",
                cursor="next-page",
            ),
        ]

    asyncio.run(run_test())


def test_find_quoteable_markets_retrieves_open_markets_and_filters_them() -> None:
    quoteable_market = KalshiMarket(
        ticker="QUOTEABLE-MARKET",
        title="Quoteable market",
        yes_bid_dollars=Decimal("0.4200"),
        yes_ask_dollars=Decimal("0.4300"),
        no_bid_dollars=Decimal("0.5700"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4250"),
        status=KalshiMarketStatus.ACTIVE,
    )
    incomplete_market = KalshiMarket(
        ticker="INCOMPLETE-MARKET",
        title="Incomplete market",
        yes_bid_dollars=Decimal("0.4200"),
        yes_ask_dollars=Decimal("0.0000"),
        no_bid_dollars=Decimal("0.5700"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4250"),
        status=KalshiMarketStatus.ACTIVE,
    )

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.get_markets.return_value = GetMarketsResponse(
            markets=[quoteable_market, incomplete_market],
            cursor="",
        )

        result = await find_quoteable_markets(client)

        assert result == (quoteable_market,)
        client.get_markets.assert_awaited_once_with(
            limit=1000,
            status="open",
        )

    asyncio.run(run_test())


def test_find_quoteable_markets_stops_after_requested_candidate_count() -> None:
    first_quoteable_market = KalshiMarket(
        ticker="FIRST-QUOTEABLE-MARKET",
        title="First quoteable market",
        yes_bid_dollars=Decimal("0.4200"),
        yes_ask_dollars=Decimal("0.4300"),
        no_bid_dollars=Decimal("0.5700"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4250"),
        status=KalshiMarketStatus.ACTIVE,
    )
    second_quoteable_market = KalshiMarket(
        ticker="SECOND-QUOTEABLE-MARKET",
        title="Second quoteable market",
        yes_bid_dollars=Decimal("0.4100"),
        yes_ask_dollars=Decimal("0.4200"),
        no_bid_dollars=Decimal("0.5800"),
        no_ask_dollars=Decimal("0.5900"),
        last_price_dollars=Decimal("0.4150"),
        status=KalshiMarketStatus.ACTIVE,
    )

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.get_markets.return_value = GetMarketsResponse(
            markets=[
                first_quoteable_market,
                second_quoteable_market,
            ],
            cursor="next-page",
        )

        result = await find_quoteable_markets(
            client,
            max_results=1,
        )

        assert result == (first_quoteable_market,)
        client.get_markets.assert_awaited_once_with(
            limit=1000,
            status="open",
        )

    asyncio.run(run_test())


def test_find_quoteable_markets_uses_configured_page_delay() -> None:
    incomplete_market = KalshiMarket(
        ticker="INCOMPLETE-MARKET",
        title="Incomplete market",
        yes_bid_dollars=Decimal("0.4200"),
        yes_ask_dollars=Decimal("0.0000"),
        no_bid_dollars=Decimal("0.5700"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4250"),
        status=KalshiMarketStatus.ACTIVE,
    )
    quoteable_market = KalshiMarket(
        ticker="QUOTEABLE-MARKET",
        title="Quoteable market",
        yes_bid_dollars=Decimal("0.4200"),
        yes_ask_dollars=Decimal("0.4300"),
        no_bid_dollars=Decimal("0.5700"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4250"),
        status=KalshiMarketStatus.ACTIVE,
    )

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.get_markets.side_effect = [
            GetMarketsResponse(
                markets=[incomplete_market],
                cursor="next-page",
            ),
            GetMarketsResponse(
                markets=[quoteable_market],
                cursor="",
            ),
        ]

        with patch(
            "kalshi_bot.market_selection.asyncio.sleep",
            new_callable=AsyncMock,
        ) as sleep:
            result = await find_quoteable_markets(
                client,
                page_delay_seconds=Decimal("0.50"),
            )

        assert result == (quoteable_market,)
        assert sleep.await_args_list == [call(0.5)]
        assert isinstance(sleep.await_args.args[0], float)

    asyncio.run(run_test())


def test_select_quoteable_markets_excludes_markets_with_too_wide_a_spread() -> None:
    tight_market = KalshiMarket(
        ticker="TIGHT-MARKET",
        title="Tight market",
        yes_bid_dollars=Decimal("0.4200"),
        yes_ask_dollars=Decimal("0.4300"),
        no_bid_dollars=Decimal("0.5700"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4250"),
        status=KalshiMarketStatus.ACTIVE,
    )
    wide_market = KalshiMarket(
        ticker="WIDE-MARKET",
        title="Wide market",
        yes_bid_dollars=Decimal("0.0100"),
        yes_ask_dollars=Decimal("0.9900"),
        no_bid_dollars=Decimal("0.0100"),
        no_ask_dollars=Decimal("0.9900"),
        last_price_dollars=Decimal("0.5000"),
        status=KalshiMarketStatus.ACTIVE,
    )

    result = select_quoteable_markets(
        [tight_market, wide_market],
        max_yes_spread_dollars=Decimal("0.05"),
    )

    assert result == (tight_market,)


def test_is_quoteable_yes_orderbook_requires_a_tight_two_sided_book() -> None:
    quoteable_orderbook = GetMarketOrderbookResponse.model_validate(
        {
            "orderbook_fp": {
                "yes_dollars": [
                    ["0.0100", "10.00"],
                ],
                "no_dollars": [
                    ["0.9500", "10.00"],
                ],
            },
        },
    )
    incomplete_orderbook = GetMarketOrderbookResponse.model_validate(
        {
            "orderbook_fp": {
                "yes_dollars": [
                    ["0.0100", "10.00"],
                ],
                "no_dollars": [],
            },
        },
    )
    wide_orderbook = GetMarketOrderbookResponse.model_validate(
        {
            "orderbook_fp": {
                "yes_dollars": [
                    ["0.0100", "10.00"],
                ],
                "no_dollars": [
                    ["0.0100", "10.00"],
                ],
            },
        },
    )

    assert is_quoteable_yes_orderbook(
        quoteable_orderbook,
        max_yes_spread_dollars=Decimal("0.05"),
    )
    assert not is_quoteable_yes_orderbook(
        incomplete_orderbook,
        max_yes_spread_dollars=Decimal("0.05"),
    )
    assert not is_quoteable_yes_orderbook(
        wide_orderbook,
        max_yes_spread_dollars=Decimal("0.05"),
    )


def test_find_open_markets_ignores_stale_summary_prices() -> None:
    active_market_with_wide_summary = KalshiMarket(
        ticker="ACTIVE-MARKET",
        title="Active market",
        yes_bid_dollars=Decimal("0.0100"),
        yes_ask_dollars=Decimal("0.9900"),
        no_bid_dollars=Decimal("0.0100"),
        no_ask_dollars=Decimal("0.9900"),
        last_price_dollars=Decimal("0.5000"),
        status=KalshiMarketStatus.ACTIVE,
    )
    inactive_market = KalshiMarket(
        ticker="INACTIVE-MARKET",
        title="Inactive market",
        yes_bid_dollars=Decimal("0.4200"),
        yes_ask_dollars=Decimal("0.4300"),
        no_bid_dollars=Decimal("0.5700"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4250"),
        status=KalshiMarketStatus.INACTIVE,
    )

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.get_markets.return_value = GetMarketsResponse(
            markets=[
                active_market_with_wide_summary,
                inactive_market,
            ],
            cursor="",
        )

        result = await find_open_markets(
            client,
            max_results=10,
            max_pages=1,
            page_delay_seconds=Decimal("0.50"),
        )

        assert result == (active_market_with_wide_summary,)
        client.get_markets.assert_awaited_once_with(
            limit=1000,
            status="open",
            mve_filter="exclude",
        )

    asyncio.run(run_test())


def test_find_open_eligible_markets_excludes_configured_categories() -> None:
    economics_market = KalshiMarket(
        ticker="ECONOMICS-MARKET",
        title="Economics market",
        yes_bid_dollars=Decimal("0.4200"),
        yes_ask_dollars=Decimal("0.4300"),
        no_bid_dollars=Decimal("0.5700"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4250"),
        status=KalshiMarketStatus.ACTIVE,
    )
    sports_market = KalshiMarket(
        ticker="SPORTS-MARKET",
        title="Sports market",
        yes_bid_dollars=Decimal("0.4200"),
        yes_ask_dollars=Decimal("0.4300"),
        no_bid_dollars=Decimal("0.5700"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4250"),
        status=KalshiMarketStatus.ACTIVE,
    )

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.get_events.return_value = GetEventsResponse(
            events=[
                KalshiEvent(
                    event_ticker="ECONOMICS-EVENT",
                    series_ticker="ECONOMICS-SERIES",
                    title="Economics event",
                    category="Economics",
                    markets=[economics_market],
                ),
                KalshiEvent(
                    event_ticker="SPORTS-EVENT",
                    series_ticker="SPORTS-SERIES",
                    title="Sports event",
                    category="Sports",
                    markets=[sports_market],
                ),
            ],
            cursor="",
        )

        result = await find_open_eligible_markets(
            client,
            excluded_categories=frozenset(
                {"sports", "elections", "entertainment"},
            ),
            max_results=10,
            max_pages=3,
            page_delay_seconds=Decimal(0),
        )

        assert result == (economics_market,)
        client.get_events.assert_awaited_once_with(
            limit=200,
            status="open",
            with_nested_markets=True,
        )

    asyncio.run(run_test())


def test_find_open_eligible_markets_checks_every_event_page() -> None:
    sports_market = KalshiMarket(
        ticker="SPORTS-MARKET",
        title="Sports market",
        yes_bid_dollars=Decimal("0.4200"),
        yes_ask_dollars=Decimal("0.4300"),
        no_bid_dollars=Decimal("0.5700"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4250"),
        status=KalshiMarketStatus.ACTIVE,
    )
    economics_market = KalshiMarket(
        ticker="ECONOMICS-MARKET",
        title="Economics market",
        yes_bid_dollars=Decimal("0.4200"),
        yes_ask_dollars=Decimal("0.4300"),
        no_bid_dollars=Decimal("0.5700"),
        no_ask_dollars=Decimal("0.5800"),
        last_price_dollars=Decimal("0.4250"),
        status=KalshiMarketStatus.ACTIVE,
    )

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.get_events.side_effect = [
            GetEventsResponse(
                events=[
                    KalshiEvent(
                        event_ticker="SPORTS-EVENT",
                        series_ticker="SPORTS-SERIES",
                        title="Sports event",
                        category="Sports",
                        markets=[sports_market],
                    ),
                ],
                cursor="next-page",
            ),
            GetEventsResponse(
                events=[
                    KalshiEvent(
                        event_ticker="ECONOMICS-EVENT",
                        series_ticker="ECONOMICS-SERIES",
                        title="Economics event",
                        category="Economics",
                        markets=[economics_market],
                    ),
                ],
                cursor="",
            ),
        ]

        result = await find_open_eligible_markets(
            client,
            excluded_categories=frozenset(
                {"sports", "elections", "entertainment"},
            ),
            max_results=10,
            max_pages=3,
            page_delay_seconds=Decimal(0),
        )

        assert result == (economics_market,)
        assert client.get_events.await_args_list == [
            call(
                limit=200,
                status="open",
                with_nested_markets=True,
            ),
            call(
                limit=200,
                status="open",
                cursor="next-page",
                with_nested_markets=True,
            ),
        ]

    asyncio.run(run_test())

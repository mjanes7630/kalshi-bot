import asyncio
from contextlib import asynccontextmanager
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, call, patch

from kalshi_bot.api.client import KalshiClient
from kalshi_bot.api.models import KalshiMarket, KalshiMarketStatus
from kalshi_bot.config import Settings
from kalshi_bot.market_scan import main, run_demo_market_scan


def test_run_demo_market_scan_uses_shared_authenticated_client() -> None:
    settings = Mock(spec=Settings)
    settings.demo_market_scan_max_results = 5
    settings.demo_market_scan_max_pages = 3
    settings.demo_market_scan_page_delay_seconds = Decimal("0.50")
    settings.demo_max_yes_spread_dollars = Decimal("0.03")
    settings.demo_market_scan_max_orderbook_checks = 10
    settings.demo_market_scan_excluded_categories = "sports,elections,entertainment"
    client = AsyncMock(spec=KalshiClient)
    expected_markets = (
        KalshiMarket(
            ticker="QUOTEABLE-MARKET",
            title="Quoteable market",
            yes_bid_dollars=Decimal("0.4200"),
            yes_ask_dollars=Decimal("0.4300"),
            no_bid_dollars=Decimal("0.5700"),
            no_ask_dollars=Decimal("0.5800"),
            last_price_dollars=Decimal("0.4250"),
            status=KalshiMarketStatus.ACTIVE,
        ),
    )
    received_settings: list[Settings] = []

    @asynccontextmanager
    async def authenticated_client_stub(received: Settings):
        received_settings.append(received)
        yield client

    async def run_test() -> None:
        with (
            patch(
                "kalshi_bot.market_scan.authenticated_kalshi_client",
                authenticated_client_stub,
            ),
            patch(
                "kalshi_bot.market_scan.find_open_eligible_markets",
                new=AsyncMock(return_value=expected_markets),
            ) as find_open_eligible_markets,
            patch(
                "kalshi_bot.market_scan.is_quoteable_yes_orderbook",
                return_value=True,
            ),
        ):
            result = await run_demo_market_scan(settings)

        assert result == expected_markets
        assert received_settings == [settings]
        find_open_eligible_markets.assert_awaited_once_with(
            client,
            excluded_categories=frozenset({"sports", "elections", "entertainment"}),
            max_results=10,
            max_pages=3,
            page_delay_seconds=Decimal("0.50"),
        )

    asyncio.run(run_test())


def test_main_configures_logging_and_runs_demo_market_scan() -> None:
    settings = Mock(spec=Settings)
    market_scan_coroutine = Mock()

    with (
        patch(
            "kalshi_bot.market_scan.Settings",
            return_value=settings,
        ) as settings_constructor,
        patch("kalshi_bot.market_scan.configure_logging") as configure_logging,
        patch(
            "kalshi_bot.market_scan.run_demo_market_scan",
            new=Mock(return_value=market_scan_coroutine),
        ) as run_demo_market_scan,
        patch("kalshi_bot.market_scan.asyncio.run") as asyncio_run,
    ):
        main()

    settings_constructor.assert_called_once_with()
    configure_logging.assert_called_once_with(settings)
    run_demo_market_scan.assert_called_once_with(settings)
    asyncio_run.assert_called_once_with(market_scan_coroutine)


def test_run_demo_market_scan_excludes_candidate_without_quoteable_live_orderbook() -> (
    None
):
    settings = Mock(spec=Settings)
    settings.demo_market_scan_max_results = 1
    settings.demo_market_scan_max_pages = 3
    settings.demo_market_scan_page_delay_seconds = Decimal("0.50")
    settings.demo_market_scan_max_orderbook_checks = 2
    settings.demo_max_yes_spread_dollars = Decimal("0.03")
    settings.demo_market_scan_excluded_categories = "sports,elections,entertainment"

    candidate_market = KalshiMarket(
        ticker="CANDIDATE-MARKET",
        title="Candidate market",
        yes_bid_dollars=Decimal("0.0100"),
        yes_ask_dollars=Decimal("0.0500"),
        no_bid_dollars=Decimal("0.9500"),
        no_ask_dollars=Decimal("0.9900"),
        last_price_dollars=Decimal("0.0300"),
        status=KalshiMarketStatus.ACTIVE,
    )

    client = AsyncMock(spec=KalshiClient)
    live_orderbook = Mock()
    client.get_market_orderbook.return_value = live_orderbook

    @asynccontextmanager
    async def authenticated_client_stub(_: Settings):
        yield client

    async def run_test() -> None:
        with (
            patch(
                "kalshi_bot.market_scan.authenticated_kalshi_client",
                authenticated_client_stub,
            ),
            patch(
                "kalshi_bot.market_scan.find_open_eligible_markets",
                new=AsyncMock(return_value=(candidate_market,)),
            ) as find_open_eligible_markets,
            patch(
                "kalshi_bot.market_scan.is_quoteable_yes_orderbook",
                return_value=False,
            ) as is_quoteable_yes_orderbook,
        ):
            result = await run_demo_market_scan(settings)

        assert result == ()
        find_open_eligible_markets.assert_awaited_once_with(
            client,
            excluded_categories=frozenset({"sports", "elections", "entertainment"}),
            max_results=2,
            max_pages=3,
            page_delay_seconds=Decimal("0.50"),
        )
        client.get_market_orderbook.assert_awaited_once_with(
            ticker="CANDIDATE-MARKET",
            depth=1,
        )
        is_quoteable_yes_orderbook.assert_called_once_with(
            live_orderbook,
            max_yes_spread_dollars=Decimal("0.03"),
        )

    asyncio.run(run_test())


def test_run_demo_market_scan_waits_between_live_orderbook_checks() -> None:
    settings = Mock(spec=Settings)
    settings.demo_market_scan_max_results = 1
    settings.demo_market_scan_max_pages = 1
    settings.demo_market_scan_page_delay_seconds = Decimal("0.50")
    settings.demo_market_scan_max_orderbook_checks = 2
    settings.demo_max_yes_spread_dollars = Decimal("0.03")
    settings.demo_market_scan_excluded_categories = "sports,elections,entertainment"

    first_candidate = Mock(spec=KalshiMarket)
    first_candidate.ticker = "FIRST-MARKET"
    second_candidate = Mock(spec=KalshiMarket)
    second_candidate.ticker = "SECOND-MARKET"

    client = AsyncMock(spec=KalshiClient)
    client.get_market_orderbook.side_effect = [
        Mock(),
        Mock(),
    ]

    @asynccontextmanager
    async def authenticated_client_stub(_: Settings):
        yield client

    async def run_test() -> None:
        with (
            patch(
                "kalshi_bot.market_scan.authenticated_kalshi_client",
                authenticated_client_stub,
            ),
            patch(
                "kalshi_bot.market_scan.find_open_eligible_markets",
                new=AsyncMock(
                    return_value=(
                        first_candidate,
                        second_candidate,
                    ),
                ),
            ),
            patch(
                "kalshi_bot.market_scan.is_quoteable_yes_orderbook",
                return_value=False,
            ),
            patch(
                "kalshi_bot.market_scan.asyncio.sleep",
                new_callable=AsyncMock,
            ) as sleep,
        ):
            result = await run_demo_market_scan(settings)

        assert result == ()
        assert client.get_market_orderbook.await_args_list == [
            call(ticker="FIRST-MARKET", depth=1),
            call(ticker="SECOND-MARKET", depth=1),
        ]
        assert sleep.await_args_list == [call(0.5)]

    asyncio.run(run_test())

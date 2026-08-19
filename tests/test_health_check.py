import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest

from kalshi_bot.api.client import KalshiClient
from kalshi_bot.api.models import KalshiMarketStatus
from kalshi_bot.config import Settings
from kalshi_bot.health import MarketHealth
from kalshi_bot.health_check import main, run_demo_market_health_check


def test_run_demo_market_health_check_requires_market_ticker() -> None:
    settings = Mock(spec=Settings)
    settings.demo_market_ticker = None

    with pytest.raises(
        ValueError,
        match="KALSHI_BOT_DEMO_MARKET_TICKER is required.",
    ):
        asyncio.run(run_demo_market_health_check(settings))


def test_run_demo_market_health_check_uses_shared_authenticated_client() -> None:
    settings = Mock(spec=Settings)
    settings.demo_market_ticker = "TEST-MARKET"

    client = AsyncMock(spec=KalshiClient)
    expected_result = MarketHealth(
        ticker="TEST-MARKET",
        market_status=KalshiMarketStatus.ACTIVE,
        is_healthy=True,
    )
    received_settings: list[Settings] = []

    @asynccontextmanager
    async def authenticated_client_stub(received: Settings):
        received_settings.append(received)
        yield client

    async def run_test() -> None:
        with (
            patch(
                "kalshi_bot.health_check.authenticated_kalshi_client",
                authenticated_client_stub,
            ),
            patch(
                "kalshi_bot.health_check.run_market_health_check",
                new=AsyncMock(return_value=expected_result),
            ) as run_market_health_check,
        ):
            result = await run_demo_market_health_check(settings)

        assert result == expected_result
        assert received_settings == [settings]
        run_market_health_check.assert_awaited_once_with(
            client=client,
            ticker="TEST-MARKET",
        )

    asyncio.run(run_test())


def test_main_configures_logging_and_runs_demo_market_health_check() -> None:
    settings = Mock(spec=Settings)
    health_check_coroutine = Mock()

    with (
        patch(
            "kalshi_bot.health_check.Settings",
            return_value=settings,
        ) as settings_constructor,
        patch("kalshi_bot.health_check.configure_logging") as configure_logging,
        patch(
            "kalshi_bot.health_check.run_demo_market_health_check",
            new=Mock(return_value=health_check_coroutine),
        ) as run_demo_market_health_check,
        patch("kalshi_bot.health_check.asyncio.run") as asyncio_run,
    ):
        main()

    settings_constructor.assert_called_once_with()
    configure_logging.assert_called_once_with(settings)
    run_demo_market_health_check.assert_called_once_with(settings)
    asyncio_run.assert_called_once_with(health_check_coroutine)

import asyncio
import pytest
import httpx
from unittest.mock import AsyncMock, Mock, patch

from kalshi_bot.api.client import KalshiClient
from kalshi_bot.api.models import KalshiMarketStatus
from kalshi_bot.health import check_market_health, run_market_health_check


def test_check_market_health_reports_active_market_as_healthy() -> None:
    market = Mock()
    market.ticker = "TEST-MARKET"
    market.status = KalshiMarketStatus.ACTIVE

    market_response = Mock()
    market_response.market = market

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.get_market.return_value = market_response

        result = await check_market_health(
            client=client,
            ticker="TEST-MARKET",
        )

        client.get_market.assert_awaited_once_with("TEST-MARKET")

        assert result.ticker == "TEST-MARKET"
        assert result.market_status is KalshiMarketStatus.ACTIVE
        assert result.is_healthy is True

    asyncio.run(run_test())


def test_check_market_health_reports_non_active_market_as_unhealthy() -> None:
    market = Mock()
    market.ticker = "TEST-MARKET"
    market.status = KalshiMarketStatus.CLOSED

    market_response = Mock()
    market_response.market = market

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.get_market.return_value = market_response

        result = await check_market_health(
            client=client,
            ticker="TEST-MARKET",
        )

        assert result.ticker == "TEST-MARKET"
        assert result.market_status is KalshiMarketStatus.CLOSED
        assert result.is_healthy is False

    asyncio.run(run_test())


def test_check_market_health_raises_when_market_request_fails() -> None:
    connection_error = httpx.ConnectError("Connection failed.")

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.get_market.side_effect = connection_error

        with pytest.raises(httpx.ConnectError, match="Connection failed."):
            await check_market_health(
                client=client,
                ticker="TEST-MARKET",
            )

        client.get_market.assert_awaited_once_with("TEST-MARKET")

    asyncio.run(run_test())


def test_run_market_health_check_logs_connection_failure() -> None:
    connection_error = httpx.ConnectError("Connection failed.")

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.get_market.side_effect = connection_error

        with (
            patch("kalshi_bot.health.logger.error") as logger_error,
            pytest.raises(httpx.ConnectError, match="Connection failed."),
        ):
            await run_market_health_check(
                client=client,
                ticker="TEST-MARKET",
            )

        logger_error.assert_called_once_with(
            "market_health_check_failed",
            ticker="TEST-MARKET",
            error="Connection failed.",
            error_type="ConnectError",
        )

    asyncio.run(run_test())


def test_run_market_health_check_logs_successful_result() -> None:
    market = Mock()
    market.ticker = "TEST-MARKET"
    market.status = KalshiMarketStatus.ACTIVE

    market_response = Mock()
    market_response.market = market

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.get_market.return_value = market_response

        with patch("kalshi_bot.health.logger.info") as logger_info:
            result = await run_market_health_check(
                client=client,
                ticker="TEST-MARKET",
            )

        assert result.is_healthy is True
        logger_info.assert_called_once_with(
            "market_health_check_completed",
            ticker="TEST-MARKET",
            market_status="active",
            is_healthy=True,
        )

    asyncio.run(run_test())


def test_run_market_health_check_logs_warning_for_non_active_market() -> None:
    market = Mock()
    market.ticker = "TEST-MARKET"
    market.status = KalshiMarketStatus.CLOSED

    market_response = Mock()
    market_response.market = market

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.get_market.return_value = market_response

        with (
            patch("kalshi_bot.health.logger.info") as logger_info,
            patch("kalshi_bot.health.logger.warning") as logger_warning,
        ):
            result = await run_market_health_check(
                client=client,
                ticker="TEST-MARKET",
            )

        assert result.is_healthy is False
        logger_info.assert_not_called()
        logger_warning.assert_called_once_with(
            "market_health_check_completed",
            ticker="TEST-MARKET",
            market_status="closed",
            is_healthy=False,
        )

    asyncio.run(run_test())
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from kalshi_bot import cancel_orders
from kalshi_bot.api.client import KALSHI_API_BASE_URL, KalshiClient
from kalshi_bot.api.models import CancelOrderResponse
from kalshi_bot.cancel_orders import run_order_cancellation
from kalshi_bot.config import Settings


def test_run_order_cancellation_does_nothing_when_disabled() -> None:
    settings = Settings(
        _env_file=None,
        order_cancellation_enabled=False,
    )

    result = asyncio.run(run_order_cancellation(settings))

    assert result == ()


@pytest.mark.parametrize(
    (
        "api_key_id",
        "private_key_path",
        "expected_message",
    ),
    [
        (
            None,
            Path("test-private-key.pem"),
            "KALSHI_BOT_API_KEY_ID is required.",
        ),
        (
            "test-key-id",
            None,
            "KALSHI_BOT_PRIVATE_KEY_PATH is required.",
        ),
    ],
)
def test_run_order_cancellation_requires_credentials_when_enabled(
    api_key_id: str | None,
    private_key_path: Path | None,
    expected_message: str,
) -> None:
    settings = Settings(
        _env_file=None,
        order_cancellation_enabled=True,
        api_key_id=api_key_id,
        private_key_path=private_key_path,
    )

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        asyncio.run(run_order_cancellation(settings))


def test_run_order_cancellation_calls_cancellation_when_enabled() -> None:
    settings = Settings(
        _env_file=None,
        order_cancellation_enabled=True,
        api_key_id="test-key-id",
        private_key_path=Path("test-private-key.pem"),
    )

    private_key = Mock()
    http_client = Mock()
    logger = Mock()
    async_client_context = AsyncMock()
    async_client_context.__aenter__.return_value = http_client

    kalshi_client = Mock(spec=KalshiClient)
    cancellation_response = Mock(spec=CancelOrderResponse)

    with (
        patch(
            "kalshi_bot.cancel_orders.load_private_key",
            return_value=private_key,
        ) as load_private_key_mock,
        patch(
            "kalshi_bot.cancel_orders.httpx.AsyncClient",
            return_value=async_client_context,
        ) as async_client_mock,
        patch(
            "kalshi_bot.cancel_orders.KalshiClient",
            return_value=kalshi_client,
        ) as client_mock,
        patch(
            "kalshi_bot.cancel_orders.cancel_all_resting_orders",
            new=AsyncMock(return_value=(cancellation_response,)),
        ) as cancellation_mock,
        patch(
            "kalshi_bot.cancel_orders.logger",
            new=logger,
        ),
    ):
        result = asyncio.run(run_order_cancellation(settings))

    assert result == (cancellation_response,)

    load_private_key_mock.assert_called_once_with(Path("test-private-key.pem"))
    async_client_mock.assert_called_once_with(
        base_url=KALSHI_API_BASE_URL,
        timeout=10.0,
    )
    client_mock.assert_called_once_with(
        http_client,
        api_key_id="test-key-id",
        private_key=private_key,
    )
    cancellation_mock.assert_awaited_once_with(
        client=kalshi_client,
        order_cancellation_enabled=True,
    )
    async_client_context.__aenter__.assert_awaited_once()
    async_client_context.__aexit__.assert_awaited_once()

    logger.info.assert_called_once_with(
        "order_cancellation_completed",
        canceled_order_count=1,
    )


def test_main_runs_order_cancellation() -> None:
    settings = Mock(spec=Settings)
    cancellation_coroutine = Mock()

    with (
        patch(
            "kalshi_bot.cancel_orders.Settings",
            return_value=settings,
        ) as settings_mock,
        patch(
            "kalshi_bot.cancel_orders.configure_logging",
            new_callable=Mock,
        ) as configure_logging_mock,
        patch(
            "kalshi_bot.cancel_orders.run_order_cancellation",
            new_callable=Mock,
            return_value=cancellation_coroutine,
        ) as cancellation_mock,
        patch(
            "kalshi_bot.cancel_orders.asyncio.run",
        ) as asyncio_run_mock,
    ):
        result = cancel_orders.main()

    assert result is None
    settings_mock.assert_called_once_with()
    configure_logging_mock.assert_called_once_with(settings)
    cancellation_mock.assert_called_once_with(settings)
    asyncio_run_mock.assert_called_once_with(cancellation_coroutine)


def test_run_order_cancellation_logs_when_disabled() -> None:
    settings = Settings(
        _env_file=None,
        order_cancellation_enabled=False,
    )
    logger = Mock()

    with patch(
        "kalshi_bot.cancel_orders.logger",
        new=logger,
    ):
        result = asyncio.run(run_order_cancellation(settings))

    assert result == ()
    logger.info.assert_called_once_with("order_cancellation_disabled")

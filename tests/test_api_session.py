import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from kalshi_bot.api.client import KALSHI_API_BASE_URL, KalshiClient
from kalshi_bot.api.session import authenticated_kalshi_client, validate_api_credentials
from kalshi_bot.config import Settings


def test_validate_api_credentials_requires_api_key_id() -> None:
    settings = Mock(spec=Settings)
    settings.api_key_id = None
    settings.private_key_path = Mock()

    with pytest.raises(ValueError, match="KALSHI_BOT_API_KEY_ID is required."):
        validate_api_credentials(settings)


def test_validate_api_credentials_requires_private_key_path() -> None:
    settings = Mock(spec=Settings)
    settings.api_key_id = "test-key-id"
    settings.private_key_path = None

    with pytest.raises(ValueError, match="KALSHI_BOT_PRIVATE_KEY_PATH is required."):
        validate_api_credentials(settings)


def test_authenticated_kalshi_client_yields_client_and_closes_http_client() -> None:
    settings = Mock(spec=Settings)
    settings.api_key_id = "test-key-id"
    settings.private_key_path = Mock()

    private_key = Mock()
    http_client = AsyncMock()
    http_client.__aenter__.return_value = http_client
    client = Mock(spec=KalshiClient)

    async def run_test() -> None:
        with (
            patch(
                "kalshi_bot.api.session.load_private_key",
                return_value=private_key,
            ) as load_private_key,
            patch(
                "kalshi_bot.api.session.httpx.AsyncClient",
                return_value=http_client,
            ) as async_client,
            patch(
                "kalshi_bot.api.session.KalshiClient",
                return_value=client,
            ) as kalshi_client,
        ):
            async with authenticated_kalshi_client(settings) as received_client:
                assert received_client is client

        load_private_key.assert_called_once_with(settings.private_key_path)
        async_client.assert_called_once_with(
            base_url=KALSHI_API_BASE_URL,
            timeout=10.0,
        )
        kalshi_client.assert_called_once_with(
            http_client,
            api_key_id="test-key-id",
            private_key=private_key,
        )
        http_client.__aexit__.assert_awaited_once_with(None, None, None)

    asyncio.run(run_test())


def test_authenticated_kalshi_client_closes_http_client_when_work_fails() -> None:
    settings = Mock(spec=Settings)
    settings.api_key_id = "test-key-id"
    settings.private_key_path = Mock()

    http_client = AsyncMock()
    http_client.__aenter__.return_value = http_client
    client = Mock(spec=KalshiClient)
    work_error = RuntimeError("Work failed.")

    async def run_test() -> None:
        with (
            patch("kalshi_bot.api.session.load_private_key"),
            patch(
                "kalshi_bot.api.session.httpx.AsyncClient",
                return_value=http_client,
            ),
            patch(
                "kalshi_bot.api.session.KalshiClient",
                return_value=client,
            ),
            pytest.raises(RuntimeError, match="Work failed."),
        ):
            async with authenticated_kalshi_client(settings) as received_client:
                assert received_client is client
                raise work_error

        exit_arguments = http_client.__aexit__.await_args.args

        assert exit_arguments[0] is RuntimeError
        assert exit_arguments[1] is work_error
        assert exit_arguments[2] is not None

    asyncio.run(run_test())

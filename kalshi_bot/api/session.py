from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from kalshi_bot.api.auth import load_private_key
from kalshi_bot.api.client import KALSHI_API_BASE_URL, KalshiClient
from kalshi_bot.config import Settings


def validate_api_credentials(settings: Settings) -> None:
    if settings.api_key_id is None:
        raise ValueError("KALSHI_BOT_API_KEY_ID is required.")

    if settings.private_key_path is None:
        raise ValueError("KALSHI_BOT_PRIVATE_KEY_PATH is required.")


@asynccontextmanager
async def authenticated_kalshi_client(
    settings: Settings,
    *,
    timeout: float = 10.0,
) -> AsyncIterator[KalshiClient]:
    validate_api_credentials(settings)

    private_key = load_private_key(settings.private_key_path)

    async with httpx.AsyncClient(
        base_url=KALSHI_API_BASE_URL,
        timeout=timeout,
    ) as http_client:
        yield KalshiClient(
            http_client,
            api_key_id=settings.api_key_id,
            private_key=private_key,
        )

import asyncio

import httpx
import structlog

from kalshi_bot.api.auth import load_private_key
from kalshi_bot.api.client import KALSHI_API_BASE_URL, KalshiClient
from kalshi_bot.api.models import CancelOrderResponse
from kalshi_bot.config import Settings
from kalshi_bot.execution.cancellation import cancel_all_resting_orders
from kalshi_bot.logging_config import configure_logging

logger = structlog.get_logger(__name__)


async def run_order_cancellation(settings: Settings) -> tuple[CancelOrderResponse, ...]:
    if not settings.order_cancellation_enabled:
        logger.info("order_cancellation_disabled")
        return ()

    if not settings.api_key_id:
        raise ValueError("KALSHI_BOT_API_KEY_ID is required.")

    if not settings.private_key_path:
        raise ValueError("KALSHI_BOT_PRIVATE_KEY_PATH is required.")

    private_key = load_private_key(settings.private_key_path)

    async with httpx.AsyncClient(
        base_url=KALSHI_API_BASE_URL,
        timeout=10.0,
    ) as http_client:
        client = KalshiClient(
            http_client,
            api_key_id=settings.api_key_id,
            private_key=private_key,
        )

        cancellation_responses = await cancel_all_resting_orders(
            client=client,
            order_cancellation_enabled=(settings.order_cancellation_enabled),
        )

        logger.info(
            "order_cancellation_completed",
            canceled_order_count=len(cancellation_responses),
        )

        return cancellation_responses


def main() -> None:
    settings = Settings()
    configure_logging(settings)
    asyncio.run(run_order_cancellation(settings))


if __name__ == "__main__":
    main()

import asyncio

import structlog

from kalshi_bot.api.models import CancelOrderResponse
from kalshi_bot.api.session import authenticated_kalshi_client
from kalshi_bot.config import Settings
from kalshi_bot.execution.cancellation import cancel_all_resting_orders
from kalshi_bot.logging_config import configure_logging

logger = structlog.get_logger(__name__)


async def run_order_cancellation(settings: Settings) -> tuple[CancelOrderResponse, ...]:
    if not settings.order_cancellation_enabled:
        logger.info("order_cancellation_disabled")
        return ()

    async with authenticated_kalshi_client(settings) as client:
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

import asyncio
from decimal import Decimal
from uuid import uuid4

import structlog

from kalshi_bot.api.client import KalshiClient
from kalshi_bot.api.models import (
    CreateOrderRequest,
    CreateOrderResponse,
    KalshiOrderSide,
)
from kalshi_bot.api.session import authenticated_kalshi_client
from kalshi_bot.config import Settings
from kalshi_bot.logging_config import configure_logging

logger = structlog.get_logger()


async def verify_demo_order(
    order_request: CreateOrderRequest,
    client: KalshiClient,
    order_submission_enabled: bool,
    order_cancellation_enabled: bool,
) -> CreateOrderResponse:
    if not order_submission_enabled or not order_cancellation_enabled:
        raise ValueError("Order submission and cancellation must both be enabled.")

    create_response = await client.create_order(order_request)
    order_id = create_response.order_id

    logger.info(
        "demo_order_created",
        order_id=order_id,
        client_order_id=create_response.client_order_id,
        ticker=order_request.ticker,
        count=order_request.count,
        price=order_request.price,
    )

    await client.cancel_order(order_id)

    return create_response


async def run_demo_order(settings: Settings) -> CreateOrderResponse | None:
    if not settings.order_submission_enabled or not settings.order_cancellation_enabled:
        return

    if not settings.demo_order_ticker or not settings.demo_order_ticker.strip():
        raise ValueError("KALSHI_BOT_DEMO_ORDER_TICKER is required.")

    if settings.demo_order_count is None:
        raise ValueError("KALSHI_BOT_DEMO_ORDER_COUNT is required.")

    if settings.demo_order_count <= Decimal("0.00"):
        raise ValueError("KALSHI_BOT_DEMO_ORDER_COUNT must be greater than zero.")

    if settings.demo_order_price is None:
        raise ValueError("KALSHI_BOT_DEMO_ORDER_PRICE is required.")

    if settings.demo_order_price <= Decimal("0.00"):
        raise ValueError("KALSHI_BOT_DEMO_ORDER_PRICE must be greater than zero.")

    if settings.demo_order_price >= Decimal("1.00"):
        raise ValueError("KALSHI_BOT_DEMO_ORDER_PRICE must be less than one.")

    logger.info("demo_order_command_ready")

    async with authenticated_kalshi_client(settings) as client:
        response = await verify_demo_order(
            client=client,
            order_request=CreateOrderRequest(  # type: ignore
                ticker=settings.demo_order_ticker,
                client_order_id=str(uuid4()),
                side=KalshiOrderSide.BID,
                count=settings.demo_order_count,
                price=settings.demo_order_price,
            ),
            order_submission_enabled=settings.order_submission_enabled,
            order_cancellation_enabled=settings.order_cancellation_enabled,
        )

        logger.info(
            "demo_order_command_completed",
            order_id=response.order_id,
        )

        return response


def main() -> None:
    settings = Settings()
    configure_logging(settings)
    asyncio.run(run_demo_order(settings))


if __name__ == "__main__":
    main()

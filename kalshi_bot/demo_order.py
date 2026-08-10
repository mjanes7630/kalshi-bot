from kalshi_bot.api.client import KalshiClient
from kalshi_bot.api.models import CreateOrderRequest
from kalshi_bot.config import Settings

import structlog

logger = structlog.get_logger()


async def verify_demo_order(
    order_request: CreateOrderRequest,
    *,
    client: KalshiClient,
    order_submission_enabled: bool,
    order_cancellation_enabled: bool,
) -> None:
    if not order_submission_enabled or not order_cancellation_enabled:
        raise ValueError("Order submission and cancellation must both be enabled.")

    create_response = await client.create_order(order_request)
    order_id = create_response.order_id

    try:
        get_response = await client.get_order(order_id)
    except Exception as retrieval_error:
        try:
            await client.cancel_order(order_id)
        except Exception as cancellation_error:  # noqa: BLE001
            raise ExceptionGroup(
                "Demo-order verification and cleanup both failed.",
                [retrieval_error, cancellation_error],
            ) from None
        raise
    else:
        await client.cancel_order(order_id)

    return get_response


async def run_demo_order(settings: Settings) -> None:
    if (
        not settings.order_submission_enabled
        or not settings.order_cancellation_enabled
    ):
        return

    if settings.api_key_id is None:
        raise ValueError("KALSHI_BOT_API_KEY_ID is required.")

    if settings.private_key_path is None:
        raise ValueError("KALSHI_BOT_PRIVATE_KEY_PATH is required.")

    logger.info("demo_order_command_ready")
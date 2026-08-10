from kalshi_bot.api.client import KalshiClient
from kalshi_bot.api.models import CreateOrderRequest


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

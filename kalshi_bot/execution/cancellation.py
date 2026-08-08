from kalshi_bot.api.client import KalshiClient
from kalshi_bot.api.models import CancelOrderResponse, KalshiOrder


async def retrieve_all_resting_orders(
    *,
    client: KalshiClient,
) -> tuple[KalshiOrder, ...]:
    resting_orders: list[KalshiOrder] = []
    seen_cursors: set[str] = set()
    cursor: str | None = None

    while True:
        response = await client.get_orders(
            status="resting",
            limit=1000,
            cursor=cursor,
        )

        resting_orders.extend(response.orders)

        if not response.cursor:
            break

        if response.cursor in seen_cursors:
            raise RuntimeError("Order pagination returned a repeated cursor.")

        seen_cursors.add(response.cursor)
        cursor = response.cursor

    return tuple(resting_orders)


async def cancel_all_resting_orders(
    *,
    client: KalshiClient,
    order_cancellation_enabled: bool,
) -> tuple[CancelOrderResponse, ...]:
    if not order_cancellation_enabled:
        return ()

    resting_orders = await retrieve_all_resting_orders(client=client)
    cancellation_responses: list[CancelOrderResponse] = []
    cancellation_errors: list[Exception] = []

    for order in resting_orders:
        try:
            response = await client.cancel_order(order.order_id)
            cancellation_responses.append(response)
        except Exception as error:  # noqa: BLE001
            cancellation_errors.append(error)

    if cancellation_errors:
        raise ExceptionGroup(
            "One or more resting order cancellations failed.",
            cancellation_errors,
        )

    return tuple(cancellation_responses)

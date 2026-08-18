from pathlib import Path

from kalshi_bot.api.client import KalshiClient
from kalshi_bot.execution.cancellation import retrieve_all_resting_orders
from kalshi_bot.execution.state import clear_lifecycle_state, load_lifecycle_state


async def recover_interrupted_lifecycle(
    *,
    client: KalshiClient,
    state_path: Path,
    order_cancellation_enabled: bool = True,
) -> None:
    if not order_cancellation_enabled:
        return

    try:
        lifecycle_state = load_lifecycle_state(state_path)
    except FileNotFoundError:
        return

    resting_orders = await retrieve_all_resting_orders(
        client=client,
        ticker=lifecycle_state.ticker,
    )

    cancellation_errors = []

    for order in resting_orders:
        if order.client_order_id is not None and order.client_order_id.startswith(
            lifecycle_state.client_order_id_prefix
        ):
            try:
                await client.cancel_order(order.order_id)
            except Exception as error:  # noqa: BLE001
                cancellation_errors.append(error)

    if cancellation_errors:
        raise ExceptionGroup(
            "One or more interrupted lifecycle order cancellations failed.",
            cancellation_errors,
        )

    clear_lifecycle_state(state_path)

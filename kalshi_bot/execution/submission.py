from uuid import uuid4

from kalshi_bot.api.client import KalshiClient
from kalshi_bot.api.models import (
    CreateOrderRequest,
    CreateOrderResponse,
    KalshiOrderSide,
)
from kalshi_bot.execution.models import ExecutionPlan, OrderIntent, OrderSide


def build_create_order_request(
    order_intent: OrderIntent,
    *,
    client_order_id: str,
) -> CreateOrderRequest:
    side_mapping = {
        OrderSide.BUY: KalshiOrderSide.BID,
        OrderSide.SELL: KalshiOrderSide.ASK,
    }

    return CreateOrderRequest(
        ticker=order_intent.ticker,
        client_order_id=client_order_id,
        side=side_mapping[order_intent.side],
        count=order_intent.quantity,
        price=order_intent.price,
    )


async def submit_execution_plan(
    execution_plan: ExecutionPlan,
    *,
    client: KalshiClient,
    order_submission_enabled: bool,
) -> tuple[CreateOrderResponse, ...]:
    if not order_submission_enabled:
        return ()

    order_responses: list[CreateOrderResponse] = []
    try:
        for order_intent in execution_plan.order_intents:
            order_request = build_create_order_request(
                order_intent,
                client_order_id=str(uuid4()),
            )

            order_response = await client.create_order(order_request)
            order_responses.append(order_response)

    except Exception as submission_error:
        cancellation_errors: list[Exception] = []

        for order_response in reversed(order_responses):
            try:
                await client.cancel_order(order_response.order_id)
            except Exception as cancellation_error:  # noqa: BLE001
                cancellation_errors.append(cancellation_error)

        if cancellation_errors:
            raise ExceptionGroup(
                "Order submission and cleanup failed",
                [submission_error, *cancellation_errors],
            )

        raise

    return tuple(order_responses)  # type: ignore[reportReturnAnyType]

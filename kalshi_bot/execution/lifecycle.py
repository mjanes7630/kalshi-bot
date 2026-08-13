from kalshi_bot.api.client import KalshiClient
from kalshi_bot.execution.cancellation import retrieve_all_resting_orders
from kalshi_bot.execution.models import ExecutionPlan
from kalshi_bot.execution.reconciliation import (
    ReconciliationDecision,
    reconcile_orders,
)
from kalshi_bot.execution.submission import submit_execution_plan


async def reconcile_execution_plan(
    execution_plan: ExecutionPlan,
    *,
    client: KalshiClient,
    order_submission_enabled: bool,
    order_cancellation_enabled: bool,
    client_order_id_prefix: str | None = None,
) -> ReconciliationDecision:
    resting_orders = await retrieve_all_resting_orders(
        client=client,
        ticker=execution_plan.ticker,
    )

    if client_order_id_prefix is not None:
        resting_orders = tuple(
            order
            for order in resting_orders
            if order.client_order_id is not None
            and order.client_order_id.startswith(client_order_id_prefix)
        )

    decision = reconcile_orders(
        desired_orders=execution_plan.order_intents,
        resting_orders=resting_orders,
    )

    cancellation_errors: list[Exception] = []

    if order_cancellation_enabled:
        for order_id in decision.order_ids_to_cancel:
            try:
                await client.cancel_order(order_id)
            except Exception as error:  # noqa: BLE001
                cancellation_errors.append(error)

    if cancellation_errors:
        raise ExceptionGroup(
            "One or more lifecycle order cancellations failed.",
            cancellation_errors,
        )

    if order_submission_enabled and (
        order_cancellation_enabled or not decision.order_ids_to_cancel
    ):
        reconciliation_plan = ExecutionPlan(
            ticker=execution_plan.ticker,
            order_intents=decision.order_intents_to_submit,
        )

        await submit_execution_plan(
            reconciliation_plan,
            client=client,
            order_submission_enabled=True,
            client_order_id_prefix=client_order_id_prefix or "",
        )

    return decision

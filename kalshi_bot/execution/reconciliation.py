from collections.abc import Sequence
from dataclasses import dataclass

from kalshi_bot.api.models import KalshiOrder, KalshiOrderSide
from kalshi_bot.execution.models import OrderIntent, OrderSide


@dataclass(frozen=True)
class ReconciliationDecision:
    order_ids_to_cancel: Sequence[str]
    order_intents_to_submit: Sequence[OrderIntent]


def reconcile_orders(
    *,
    desired_orders: tuple[OrderIntent, ...],
    resting_orders: tuple[KalshiOrder, ...],
) -> ReconciliationDecision:
    unmatched_resting_orders = list(resting_orders)
    order_intents_to_submit: list[OrderIntent] = []

    for desired_order in desired_orders:
        expected_side = (
            KalshiOrderSide.BID
            if desired_order.side is OrderSide.BUY
            else KalshiOrderSide.ASK
        )
        matching_order = next(
            (
                resting_order
                for resting_order in unmatched_resting_orders
                if resting_order.ticker == desired_order.ticker
                and resting_order.side is expected_side
                and resting_order.yes_price_dollars == desired_order.price
                and resting_order.remaining_count_fp == desired_order.quantity
            ),
            None,
        )

        if matching_order is None:
            order_intents_to_submit.append(desired_order)
        else:
            unmatched_resting_orders.remove(matching_order)

    order_ids_to_cancel: list[str] = []

    for resting_order in unmatched_resting_orders:
        if not resting_order.order_id:
            raise ValueError("Unmatched resting order must have an order_id")

        order_ids_to_cancel.append(resting_order.order_id)

    return ReconciliationDecision(
        order_ids_to_cancel=tuple(order_ids_to_cancel),
        order_intents_to_submit=tuple(order_intents_to_submit),
    )

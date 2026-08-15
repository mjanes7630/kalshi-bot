from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class TimeInForce(StrEnum):
    IMMEDIATE_OR_CANCEL = "immediate_or_cancel"
    GOOD_TILL_CANCELED = "good_till_canceled"


@dataclass(frozen=True)
class OrderIntent:
    ticker: str
    side: OrderSide
    price: Decimal
    quantity: Decimal
    post_only: bool = True
    time_in_force: TimeInForce = TimeInForce.GOOD_TILL_CANCELED


@dataclass(frozen=True)
class ExecutionPlan:
    ticker: str
    order_intents: tuple[OrderIntent, ...]

    @property
    def has_order_intents(self) -> bool:
        return bool(self.order_intents)

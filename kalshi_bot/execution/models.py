from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class OrderIntent:
    ticker: str
    side: OrderSide
    price: Decimal
    quantity: Decimal


@dataclass(frozen=True)
class ExecutionPlan:
    ticker: str
    order_intents: tuple[OrderIntent, ...]

    @property
    def has_order_intents(self) -> bool:
        return bool(self.order_intents)

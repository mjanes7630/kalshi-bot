from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from kalshi_bot.execution.models import OrderIntent, OrderSide, TimeInForce
from kalshi_bot.marketdata.models import MarketSnapshot
from kalshi_bot.risk.checks import is_market_data_fresh, is_market_open


@dataclass(frozen=True)
class InventoryAction:
    side: OrderSide
    quantity: Decimal


def decide_inventory_action(
    position: Decimal,
) -> InventoryAction | None:
    if not isinstance(position, Decimal):
        raise TypeError("position must be a Decimal")

    if not position.is_finite():
        raise ValueError("position must be finite")

    if position > Decimal("0.00"):
        return InventoryAction(
            side=OrderSide.SELL,
            quantity=position,
        )
    elif position < Decimal("0.00"):
        return InventoryAction(
            side=OrderSide.BUY,
            quantity=abs(position),
        )
    return None


def can_flatten_inventory(
    *,
    market_status: str,
    observed_at: datetime,
    now: datetime,
    max_observed_age_seconds: int,
) -> bool:
    return is_market_open(market_status) and is_market_data_fresh(
        observed_at, now=now, max_age_seconds=max_observed_age_seconds
    )


def create_flattening_order_intent(
    *,
    ticker: str,
    inventory_action: InventoryAction,
    snapshot: MarketSnapshot,
) -> OrderIntent:
    if ticker != snapshot.ticker:
        raise ValueError("ticker must match snapshot.ticker")

    if snapshot.status != "open":
        raise ValueError("market must be open.")

    if inventory_action.quantity <= Decimal("0.00"):
        raise ValueError("quantity must be positive")

    if inventory_action.side is OrderSide.SELL:
        price_level = snapshot.best_yes_bid
    else:
        price_level = snapshot.best_yes_ask

    if price_level is None:
        raise ValueError("A flattening order requires a matching best YES price.")

    return OrderIntent(
        ticker=ticker,
        side=inventory_action.side,
        price=price_level.price,
        quantity=inventory_action.quantity,
        post_only=False,
        time_in_force=TimeInForce.IMMEDIATE_OR_CANCEL,
    )

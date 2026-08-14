from datetime import datetime, timedelta
from decimal import Decimal

from kalshi_bot.risk.models import RiskDecision, RiskDecisionReason
from kalshi_bot.strategy.models import QuoteDecision


def evaluate_quote_risk(
    quote_decision: QuoteDecision,
    *,
    max_quote_quantity: Decimal,
    market_status: str,
    observed_at: datetime,
    now: datetime,
    max_observed_age_seconds: int,
    market_exposure_dollars: Decimal,
    max_market_exposure_dollars: Decimal,
    available_balance_dollars: Decimal,
    minimum_available_balance_dollars: Decimal,
) -> RiskDecision:
    if max_quote_quantity <= Decimal("0.00"):
        raise ValueError("max_quote_quantity must be greater than zero")

    if quote_decision.yes_bid is None or quote_decision.yes_ask is None:
        return RiskDecision(
            ticker=quote_decision.ticker,
            reason=RiskDecisionReason.INCOMPLETE_QUOTE,
        )

    if (
        quote_decision.yes_bid.quantity > max_quote_quantity
        or quote_decision.yes_ask.quantity > max_quote_quantity
    ):
        return RiskDecision(
            ticker=quote_decision.ticker,
            reason=RiskDecisionReason.QUOTE_SIZE_EXCEEDS_LIMIT,
        )

    quote_reservation_dollars = calculate_quote_reservation_dollars(quote_decision)

    projected_market_exposure_dollars = (
        market_exposure_dollars + quote_reservation_dollars
    )

    if not is_market_exposure_within_limit(
        projected_market_exposure_dollars,
        max_market_exposure_dollars=max_market_exposure_dollars,
    ):
        return RiskDecision(
            ticker=quote_decision.ticker,
            reason=RiskDecisionReason.MARKET_EXPOSURE_EXCEEDS_LIMIT,
        )

    projected_available_balance_dollars = (
        available_balance_dollars - quote_reservation_dollars
    )

    if not has_minimum_available_balance(
        projected_available_balance_dollars,
        minimum_available_balance_dollars=minimum_available_balance_dollars,
    ):
        return RiskDecision(
            ticker=quote_decision.ticker,
            reason=RiskDecisionReason.AVAILABLE_BALANCE_BELOW_FLOOR,
        )

    if not is_market_open(market_status):
        return RiskDecision(
            ticker=quote_decision.ticker,
            reason=RiskDecisionReason.MARKET_NOT_OPEN,
        )

    if not is_market_data_fresh(
        observed_at,
        now=now,
        max_age_seconds=max_observed_age_seconds,
    ):
        return RiskDecision(
            ticker=quote_decision.ticker,
            reason=RiskDecisionReason.STALE_MARKET_DATA,
        )

    return RiskDecision(
        ticker=quote_decision.ticker,
        reason=RiskDecisionReason.APPROVED,
    )


def is_market_open(status: str) -> bool:
    return status == "open"


def is_market_data_fresh(
    observed_at: datetime,
    *,
    now: datetime,
    max_age_seconds: int,
) -> bool:
    if max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be greater than zero")

    return now - observed_at <= timedelta(seconds=max_age_seconds)


def is_market_exposure_within_limit(
    market_exposure_dollars: Decimal,
    *,
    max_market_exposure_dollars: Decimal,
) -> bool:
    if max_market_exposure_dollars <= Decimal("0.00"):
        raise ValueError("max_market_exposure_dollars must be greater than zero")

    return market_exposure_dollars <= max_market_exposure_dollars


def has_minimum_available_balance(
    available_balance_dollars: Decimal,
    *,
    minimum_available_balance_dollars: Decimal,
) -> bool:
    if minimum_available_balance_dollars <= Decimal("0.00"):
        raise ValueError("minimum_available_balance_dollars must be greater than zero")

    return available_balance_dollars >= minimum_available_balance_dollars


def calculate_quote_reservation_dollars(
    quote_decision: QuoteDecision,
) -> Decimal:
    if quote_decision.yes_bid is None or quote_decision.yes_ask is None:
        raise ValueError("A complete quote is required to calculate reservation.")

    yes_bid_reservation = quote_decision.yes_bid.quantity * quote_decision.yes_bid.price
    yes_ask_reservation = (
        Decimal("1.0000") - quote_decision.yes_ask.price
    ) * quote_decision.yes_ask.quantity
    return yes_bid_reservation + yes_ask_reservation

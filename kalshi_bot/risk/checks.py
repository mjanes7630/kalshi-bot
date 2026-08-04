from decimal import Decimal

from kalshi_bot.risk.models import RiskDecision, RiskDecisionReason
from kalshi_bot.strategy.models import QuoteDecision


def evaluate_quote_risk(
    quote_decision: QuoteDecision,
    *,
    max_quote_quantity: Decimal,
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

    return RiskDecision(
        ticker=quote_decision.ticker,
        reason=RiskDecisionReason.APPROVED,
    )

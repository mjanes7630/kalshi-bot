from kalshi_bot.execution.models import ExecutionPlan, OrderIntent, OrderSide
from kalshi_bot.risk.models import RiskDecision, RiskDecisionReason
from kalshi_bot.strategy.models import QuoteDecision


def create_execution_plan(
    quote_decision: QuoteDecision,
    risk_decision: RiskDecision,
) -> ExecutionPlan:
    if quote_decision.ticker != risk_decision.ticker:
        raise ValueError("quote and risk decisions must have matching tickers")

    if risk_decision.reason is not RiskDecisionReason.APPROVED:
        return ExecutionPlan(
            ticker=quote_decision.ticker,
            order_intents=(),
        )

    if quote_decision.yes_bid is None or quote_decision.yes_ask is None:
        raise ValueError("approved quote decision must contain both proposals")

    return ExecutionPlan(
        ticker=quote_decision.ticker,
        order_intents=(
            OrderIntent(
                ticker=quote_decision.ticker,
                side=OrderSide.BUY,
                price=quote_decision.yes_bid.price,
                quantity=quote_decision.yes_bid.quantity,
            ),
            OrderIntent(
                ticker=quote_decision.ticker,
                side=OrderSide.SELL,
                price=quote_decision.yes_ask.price,
                quantity=quote_decision.yes_ask.quantity,
            ),
        ),
    )

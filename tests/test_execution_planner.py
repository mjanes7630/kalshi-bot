from dataclasses import FrozenInstanceError, replace
from decimal import Decimal

import pytest

from kalshi_bot.execution.models import ExecutionPlan, OrderIntent, OrderSide
from kalshi_bot.execution.planner import create_execution_plan
from kalshi_bot.risk.models import RiskDecision, RiskDecisionReason
from kalshi_bot.strategy.models import (
    QuoteDecision,
    QuoteDecisionReason,
    QuoteProposal,
)


@pytest.fixture
def quote_decision() -> QuoteDecision:
    return QuoteDecision(
        ticker="TEST-MARKET",
        yes_bid=QuoteProposal(
            price=Decimal("0.4200"),
            quantity=Decimal("2.00"),
        ),
        yes_ask=QuoteProposal(
            price=Decimal("0.4400"),
            quantity=Decimal("2.00"),
        ),
        reason=QuoteDecisionReason.TWO_SIDED_BOOK,
    )


@pytest.fixture
def approved_risk_decision() -> RiskDecision:
    return RiskDecision(
        ticker="TEST-MARKET",
        reason=RiskDecisionReason.APPROVED,
    )


def test_creates_two_order_intents_for_approved_quote(
    quote_decision: QuoteDecision,
    approved_risk_decision: RiskDecision,
) -> None:
    execution_plan = create_execution_plan(
        quote_decision,
        approved_risk_decision,
    )

    assert execution_plan == ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(
            OrderIntent(
                ticker="TEST-MARKET",
                side=OrderSide.BUY,
                price=Decimal("0.4200"),
                quantity=Decimal("2.00"),
            ),
            OrderIntent(
                ticker="TEST-MARKET",
                side=OrderSide.SELL,
                price=Decimal("0.4400"),
                quantity=Decimal("2.00"),
            ),
        ),
    )
    assert execution_plan.has_order_intents is True


def test_creates_empty_plan_for_rejected_quote(
    quote_decision: QuoteDecision,
) -> None:
    rejected_risk_decision = RiskDecision(
        ticker="TEST-MARKET",
        reason=RiskDecisionReason.QUOTE_SIZE_EXCEEDS_LIMIT,
    )

    execution_plan = create_execution_plan(
        quote_decision,
        rejected_risk_decision,
    )

    assert execution_plan == ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(),
    )
    assert execution_plan.has_order_intents is False


def test_rejects_mismatched_decision_tickers(
    quote_decision: QuoteDecision,
    approved_risk_decision: RiskDecision,
) -> None:
    mismatched_risk_decision = replace(
        approved_risk_decision,
        ticker="OTHER-MARKET",
    )

    with pytest.raises(
        ValueError,
        match="quote and risk decisions must have matching tickers",
    ):
        create_execution_plan(
            quote_decision,
            mismatched_risk_decision,
        )


def test_rejects_approved_incomplete_quote(
    quote_decision: QuoteDecision,
    approved_risk_decision: RiskDecision,
) -> None:
    incomplete_quote_decision = replace(
        quote_decision,
        yes_ask=None,
    )

    with pytest.raises(
        ValueError,
        match="approved quote decision must contain both proposals",
    ):
        create_execution_plan(
            incomplete_quote_decision,
            approved_risk_decision,
        )


def test_execution_plan_is_immutable(
    quote_decision: QuoteDecision,
    approved_risk_decision: RiskDecision,
) -> None:
    execution_plan = create_execution_plan(
        quote_decision,
        approved_risk_decision,
    )

    assert isinstance(execution_plan.order_intents, tuple)

    with pytest.raises(FrozenInstanceError):
        execution_plan.ticker = "OTHER-MARKET"

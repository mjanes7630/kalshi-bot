from dataclasses import replace
from decimal import Decimal

import pytest

from kalshi_bot.risk.checks import evaluate_quote_risk
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


def test_approves_complete_quote_at_size_limit(
    quote_decision: QuoteDecision,
) -> None:
    risk_decision = evaluate_quote_risk(
        quote_decision,
        max_quote_quantity=Decimal("2.00"),
    )

    assert risk_decision == RiskDecision(
        ticker="TEST-MARKET",
        reason=RiskDecisionReason.APPROVED,
    )
    assert risk_decision.approved is True


def test_rejects_quote_above_size_limit(
    quote_decision: QuoteDecision,
) -> None:
    oversized_quote = replace(
        quote_decision,
        yes_ask=QuoteProposal(
            price=Decimal("0.4400"),
            quantity=Decimal("2.01"),
        ),
    )

    risk_decision = evaluate_quote_risk(
        oversized_quote,
        max_quote_quantity=Decimal("2.00"),
    )

    assert risk_decision.reason is RiskDecisionReason.QUOTE_SIZE_EXCEEDS_LIMIT
    assert risk_decision.approved is False


def test_rejects_incomplete_quote(
    quote_decision: QuoteDecision,
) -> None:
    incomplete_quote = replace(
        quote_decision,
        yes_ask=None,
    )

    risk_decision = evaluate_quote_risk(
        incomplete_quote,
        max_quote_quantity=Decimal("2.00"),
    )

    assert risk_decision.reason is RiskDecisionReason.INCOMPLETE_QUOTE
    assert risk_decision.approved is False


def test_rejects_yes_bid_above_size_limit(
    quote_decision: QuoteDecision,
) -> None:
    oversized_quote = replace(
        quote_decision,
        yes_bid=QuoteProposal(
            price=Decimal("0.4200"),
            quantity=Decimal("2.01"),
        ),
    )

    risk_decision = evaluate_quote_risk(
        oversized_quote,
        max_quote_quantity=Decimal("2.00"),
    )

    assert risk_decision.reason is RiskDecisionReason.QUOTE_SIZE_EXCEEDS_LIMIT
    assert risk_decision.approved is False


def test_rejects_quote_missing_yes_bid(
    quote_decision: QuoteDecision,
) -> None:
    incomplete_quote = replace(
        quote_decision,
        yes_bid=None,
    )

    risk_decision = evaluate_quote_risk(
        incomplete_quote,
        max_quote_quantity=Decimal("2.00"),
    )

    assert risk_decision.reason is RiskDecisionReason.INCOMPLETE_QUOTE
    assert risk_decision.approved is False


@pytest.mark.parametrize(
    "invalid_max_quote_quantity",
    [
        Decimal("0.00"),
        Decimal("-0.01"),
    ],
)
def test_rejects_non_positive_max_quote_quantity(
    quote_decision: QuoteDecision,
    invalid_max_quote_quantity: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="max_quote_quantity must be greater than zero",
    ):
        evaluate_quote_risk(
            quote_decision,
            max_quote_quantity=invalid_max_quote_quantity,
        )

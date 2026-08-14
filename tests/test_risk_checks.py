from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from kalshi_bot.risk.checks import (
    calculate_quote_reservation_dollars,
    evaluate_quote_risk,
    has_minimum_available_balance,
    is_market_data_fresh,
    is_market_exposure_within_limit,
    is_market_open,
)
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
        market_status="open",
        observed_at=datetime.now(UTC),
        now=datetime.now(UTC),
        max_observed_age_seconds=30,
        market_exposure_dollars=Decimal("0.00"),
        max_market_exposure_dollars=Decimal("5.00"),
        available_balance_dollars=Decimal("100.00"),
        minimum_available_balance_dollars=Decimal("10.00"),
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
        market_status="open",
        observed_at=datetime.now(UTC),
        now=datetime.now(UTC),
        max_observed_age_seconds=30,
        market_exposure_dollars=Decimal("0.00"),
        max_market_exposure_dollars=Decimal("5.00"),
        available_balance_dollars=Decimal("100.00"),
        minimum_available_balance_dollars=Decimal("10.00"),
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
        market_status="open",
        observed_at=datetime.now(UTC),
        now=datetime.now(UTC),
        max_observed_age_seconds=30,
        market_exposure_dollars=Decimal("0.00"),
        max_market_exposure_dollars=Decimal("5.00"),
        available_balance_dollars=Decimal("100.00"),
        minimum_available_balance_dollars=Decimal("10.00"),
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
        market_status="open",
        observed_at=datetime.now(UTC),
        now=datetime.now(UTC),
        max_observed_age_seconds=30,
        market_exposure_dollars=Decimal("0.00"),
        max_market_exposure_dollars=Decimal("5.00"),
        available_balance_dollars=Decimal("100.00"),
        minimum_available_balance_dollars=Decimal("10.00"),
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
        market_status="open",
        observed_at=datetime.now(UTC),
        now=datetime.now(UTC),
        max_observed_age_seconds=30,
        market_exposure_dollars=Decimal("0.00"),
        max_market_exposure_dollars=Decimal("5.00"),
        available_balance_dollars=Decimal("100.00"),
        minimum_available_balance_dollars=Decimal("10.00"),
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
            market_status="open",
            observed_at=datetime.now(UTC),
            now=datetime.now(UTC),
            max_observed_age_seconds=30,
            market_exposure_dollars=Decimal("0.00"),
            max_market_exposure_dollars=Decimal("5.00"),
            available_balance_dollars=Decimal("100.00"),
            minimum_available_balance_dollars=Decimal("10.00"),
        )


def test_is_market_open_returns_true_for_open_market() -> None:
    assert is_market_open("open") is True


def test_is_market_open_returns_false_for_non_open_market() -> None:
    assert is_market_open("closed") is False
    assert is_market_open("paused") is False
    assert is_market_open("settled") is False


def test_is_market_open_returns_false_for_unrecognized_status() -> None:
    assert is_market_open("") is False
    assert is_market_open("OPEN") is False
    assert is_market_open("unknown") is False


def test_rejects_quote_for_non_open_market(
    quote_decision: QuoteDecision,
) -> None:
    risk_decision = evaluate_quote_risk(
        quote_decision,
        max_quote_quantity=Decimal("2.00"),
        market_status="closed",
        observed_at=datetime.now(UTC),
        now=datetime.now(UTC),
        max_observed_age_seconds=30,
        market_exposure_dollars=Decimal("0.00"),
        max_market_exposure_dollars=Decimal("5.00"),
        available_balance_dollars=Decimal("100.00"),
        minimum_available_balance_dollars=Decimal("10.00"),
    )

    assert risk_decision == RiskDecision(
        ticker="TEST-MARKET",
        reason=RiskDecisionReason.MARKET_NOT_OPEN,
    )
    assert risk_decision.approved is False


def test_is_market_data_fresh_returns_true_at_maximum_age() -> None:
    observed_at = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    now = observed_at + timedelta(seconds=30)

    assert (
        is_market_data_fresh(
            observed_at,
            now=now,
            max_age_seconds=30,
        )
        is True
    )


def test_is_market_data_fresh_returns_false_after_maximum_age() -> None:
    observed_at = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    now = observed_at + timedelta(seconds=31)

    assert (
        is_market_data_fresh(
            observed_at,
            now=now,
            max_age_seconds=30,
        )
        is False
    )


@pytest.mark.parametrize(
    "max_age_seconds",
    [
        0,
        -1,
    ],
)
def test_is_market_data_fresh_rejects_non_positive_max_age_seconds(
    max_age_seconds: int,
) -> None:
    observed_at = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)

    with pytest.raises(
        ValueError,
        match="max_age_seconds must be greater than zero",
    ):
        is_market_data_fresh(
            observed_at,
            now=observed_at,
            max_age_seconds=max_age_seconds,
        )


def test_rejects_quote_when_market_data_is_stale(
    quote_decision: QuoteDecision,
) -> None:
    observed_at = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    now = observed_at + timedelta(seconds=31)

    risk_decision = evaluate_quote_risk(
        quote_decision,
        max_quote_quantity=Decimal("2.00"),
        market_status="open",
        observed_at=observed_at,
        now=now,
        max_observed_age_seconds=30,
        market_exposure_dollars=Decimal("0.00"),
        max_market_exposure_dollars=Decimal("5.00"),
        available_balance_dollars=Decimal("100.00"),
        minimum_available_balance_dollars=Decimal("10.00"),
    )

    assert risk_decision == RiskDecision(
        ticker="TEST-MARKET",
        reason=RiskDecisionReason.STALE_MARKET_DATA,
    )
    assert risk_decision.approved is False


def test_is_market_exposure_within_limit_returns_true_at_limit() -> None:
    assert (
        is_market_exposure_within_limit(
            Decimal("5.00"),
            max_market_exposure_dollars=Decimal("5.00"),
        )
        is True
    )


def test_is_market_exposure_within_limit_returns_false_above_limit() -> None:
    assert (
        is_market_exposure_within_limit(
            Decimal("5.01"),
            max_market_exposure_dollars=Decimal("5.00"),
        )
        is False
    )


@pytest.mark.parametrize(
    "max_market_exposure_dollars",
    [
        Decimal("0.00"),
        Decimal("-0.01"),
    ],
)
def test_is_market_exposure_within_limit_rejects_non_positive_limit(
    max_market_exposure_dollars: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="max_market_exposure_dollars must be greater than zero",
    ):
        is_market_exposure_within_limit(
            Decimal("0.00"),
            max_market_exposure_dollars=max_market_exposure_dollars,
        )


def test_rejects_quote_when_market_exposure_exceeds_limit(
    quote_decision: QuoteDecision,
) -> None:
    observed_at = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)

    risk_decision = evaluate_quote_risk(
        quote_decision,
        max_quote_quantity=Decimal("2.00"),
        market_status="open",
        observed_at=observed_at,
        now=observed_at,
        max_observed_age_seconds=30,
        market_exposure_dollars=Decimal("5.01"),
        max_market_exposure_dollars=Decimal("5.00"),
        available_balance_dollars=Decimal("100.00"),
        minimum_available_balance_dollars=Decimal("10.00"),
    )

    assert risk_decision == RiskDecision(
        ticker="TEST-MARKET",
        reason=RiskDecisionReason.MARKET_EXPOSURE_EXCEEDS_LIMIT,
    )
    assert risk_decision.approved is False


def test_has_minimum_available_balance_returns_true_at_floor() -> None:
    assert (
        has_minimum_available_balance(
            Decimal("10.00"),
            minimum_available_balance_dollars=Decimal("10.00"),
        )
        is True
    )


def test_has_minimum_available_balance_returns_false_below_floor() -> None:
    assert (
        has_minimum_available_balance(
            Decimal("9.99"),
            minimum_available_balance_dollars=Decimal("10.00"),
        )
        is False
    )


@pytest.mark.parametrize(
    "minimum_available_balance_dollars",
    [
        Decimal("0.00"),
        Decimal("-0.01"),
    ],
)
def test_has_minimum_available_balance_rejects_non_positive_floor(
    minimum_available_balance_dollars: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="minimum_available_balance_dollars must be greater than zero",
    ):
        has_minimum_available_balance(
            Decimal("10.00"),
            minimum_available_balance_dollars=(minimum_available_balance_dollars),
        )


def test_rejects_quote_when_available_balance_is_below_floor(
    quote_decision: QuoteDecision,
) -> None:
    observed_at = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)

    risk_decision = evaluate_quote_risk(
        quote_decision,
        max_quote_quantity=Decimal("2.00"),
        market_status="open",
        observed_at=observed_at,
        now=observed_at,
        max_observed_age_seconds=30,
        market_exposure_dollars=Decimal("0.00"),
        max_market_exposure_dollars=Decimal("5.00"),
        available_balance_dollars=Decimal("9.99"),
        minimum_available_balance_dollars=Decimal("10.00"),
    )

    assert risk_decision == RiskDecision(
        ticker="TEST-MARKET",
        reason=RiskDecisionReason.AVAILABLE_BALANCE_BELOW_FLOOR,
    )
    assert risk_decision.approved is False


def test_calculate_quote_reservation_dollars_for_two_sided_quote(
    quote_decision: QuoteDecision,
) -> None:
    assert calculate_quote_reservation_dollars(quote_decision) == Decimal("1.9600")


def test_calculate_quote_reservation_dollars_requires_complete_quote(
    quote_decision: QuoteDecision,
) -> None:
    incomplete_quote = replace(
        quote_decision,
        yes_ask=None,
    )

    with pytest.raises(
        ValueError,
        match="A complete quote is required to calculate reservation.",
    ):
        calculate_quote_reservation_dollars(incomplete_quote)


def test_rejects_quote_when_projected_market_exposure_exceeds_limit(
    quote_decision: QuoteDecision,
) -> None:
    observed_at = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)

    risk_decision = evaluate_quote_risk(
        quote_decision,
        max_quote_quantity=Decimal("2.00"),
        market_status="open",
        observed_at=observed_at,
        now=observed_at,
        max_observed_age_seconds=30,
        market_exposure_dollars=Decimal("4.00"),
        max_market_exposure_dollars=Decimal("5.00"),
        available_balance_dollars=Decimal("100.00"),
        minimum_available_balance_dollars=Decimal("10.00"),
    )

    assert risk_decision == RiskDecision(
        ticker="TEST-MARKET",
        reason=RiskDecisionReason.MARKET_EXPOSURE_EXCEEDS_LIMIT,
    )
    assert risk_decision.approved is False


def test_rejects_quote_when_projected_available_balance_is_below_floor(
    quote_decision: QuoteDecision,
) -> None:
    observed_at = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)

    risk_decision = evaluate_quote_risk(
        quote_decision,
        max_quote_quantity=Decimal("2.00"),
        market_status="open",
        observed_at=observed_at,
        now=observed_at,
        max_observed_age_seconds=30,
        market_exposure_dollars=Decimal("0.00"),
        max_market_exposure_dollars=Decimal("5.00"),
        available_balance_dollars=Decimal("11.95"),
        minimum_available_balance_dollars=Decimal("10.00"),
    )

    assert risk_decision == RiskDecision(
        ticker="TEST-MARKET",
        reason=RiskDecisionReason.AVAILABLE_BALANCE_BELOW_FLOOR,
    )
    assert risk_decision.approved is False

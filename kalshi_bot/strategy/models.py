from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class QuoteDecisionReason(StrEnum):
    TWO_SIDED_BOOK = "two_sided_book"
    INCOMPLETE_BOOK = "incomplete_book"
    CROSSED_BOOK = "crossed_book"
    WIDE_SPREAD = "wide_spread"


@dataclass(frozen=True)
class QuoteProposal:
    price: Decimal
    quantity: Decimal


@dataclass(frozen=True)
class QuoteDecision:
    ticker: str
    yes_bid: QuoteProposal | None
    yes_ask: QuoteProposal | None
    reason: QuoteDecisionReason

    @property
    def should_quote(self) -> bool:
        return self.yes_bid is not None and self.yes_ask is not None

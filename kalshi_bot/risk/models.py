from dataclasses import dataclass
from enum import Enum


class RiskDecisionReason(Enum):
    APPROVED = "approved"
    INCOMPLETE_QUOTE = "incomplete_quote"
    QUOTE_SIZE_EXCEEDS_LIMIT = "quote_size_exceeds_limit"
    MARKET_NOT_OPEN = "market_not_open"
    STALE_MARKET_DATA = "stale_market_data"
    MARKET_EXPOSURE_EXCEEDS_LIMIT = "market_exposure_exceeds_limit"
    AVAILABLE_BALANCE_BELOW_FLOOR = "available_balance_below_floor"


@dataclass(frozen=True)
class RiskDecision:
    ticker: str
    reason: RiskDecisionReason

    @property
    def approved(self) -> bool:
        return self.reason is RiskDecisionReason.APPROVED

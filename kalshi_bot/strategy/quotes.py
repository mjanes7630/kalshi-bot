from decimal import Decimal

from kalshi_bot.marketdata.models import MarketSnapshot
from kalshi_bot.strategy.models import QuoteDecision, QuoteDecisionReason, QuoteProposal


def decide_quotes(
    snapshot: MarketSnapshot,
    *,
    quote_quantity: Decimal,
    max_yes_spread_dollars: Decimal = Decimal("0.05"),
) -> QuoteDecision:
    if max_yes_spread_dollars < 0:
        raise ValueError("max_yes_spread_dollars cannot be negative.")

    best_yes_bid = snapshot.best_yes_bid
    best_yes_ask = snapshot.best_yes_ask

    if best_yes_bid is None or best_yes_ask is None:
        return QuoteDecision(
            ticker=snapshot.ticker,
            yes_bid=None,
            yes_ask=None,
            reason=QuoteDecisionReason.INCOMPLETE_BOOK,
        )

    if best_yes_bid.price >= best_yes_ask.price:
        return QuoteDecision(
            ticker=snapshot.ticker,
            yes_bid=None,
            yes_ask=None,
            reason=QuoteDecisionReason.CROSSED_BOOK,
        )

    if best_yes_ask.price - best_yes_bid.price > max_yes_spread_dollars:
        return QuoteDecision(
            ticker=snapshot.ticker,
            yes_bid=None,
            yes_ask=None,
            reason=QuoteDecisionReason.WIDE_SPREAD,
        )

    return QuoteDecision(
        ticker=snapshot.ticker,
        yes_bid=QuoteProposal(
            price=best_yes_bid.price,
            quantity=quote_quantity,
        ),
        yes_ask=QuoteProposal(
            price=best_yes_ask.price,
            quantity=quote_quantity,
        ),
        reason=QuoteDecisionReason.TWO_SIDED_BOOK,
    )

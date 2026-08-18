import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import httpx
import structlog

from kalshi_bot.api.auth import load_private_key
from kalshi_bot.api.client import KALSHI_API_BASE_URL, KalshiClient
from kalshi_bot.config import Settings
from kalshi_bot.execution.cancellation import retrieve_all_resting_orders
from kalshi_bot.execution.inventory import (
    can_flatten_inventory,
    create_flattening_order_intent,
    decide_inventory_action,
)
from kalshi_bot.execution.lifecycle import reconcile_execution_plan
from kalshi_bot.execution.models import ExecutionPlan
from kalshi_bot.execution.planner import create_execution_plan
from kalshi_bot.execution.recovery import recover_interrupted_lifecycle
from kalshi_bot.execution.state import (
    LifecycleState,
    clear_lifecycle_state,
    save_lifecycle_state,
)
from kalshi_bot.logging_config import configure_logging
from kalshi_bot.marketdata.builder import build_market_snapshot
from kalshi_bot.models.market import Market
from kalshi_bot.risk.checks import evaluate_quote_risk
from kalshi_bot.strategy.quotes import decide_quotes

logger = structlog.get_logger(__name__)


def classify_trade(price: Decimal, midpoint: Decimal) -> str:
    if price > midpoint:
        return "Above Midpoint"
    elif price < midpoint:
        return "Below Midpoint"
    else:
        return "At Midpoint"


def display_trade_prices(prices: list[Decimal], midpoint: Decimal) -> None:
    for price in prices:
        classification = classify_trade(price, midpoint)

        logger.info(
            "trade_price_classified",
            price=price,
            classification=classification,
        )


async def retrieve_demo_api_data(
    settings: Settings,
    *,
    client_order_id_prefix: str | None = None,
) -> None:
    if settings.api_key_id is None:
        raise ValueError("KALSHI_BOT_API_KEY_ID is required.")

    if settings.private_key_path is None:
        raise ValueError("KALSHI_BOT_PRIVATE_KEY_PATH is required.")

    if settings.demo_market_ticker is None:
        raise ValueError("KALSHI_BOT_DEMO_MARKET_TICKER is required.")

    if settings.demo_quote_quantity is None:
        raise ValueError("KALSHI_BOT_DEMO_QUOTE_QUANTITY is required.")

    private_key = load_private_key(settings.private_key_path)

    async with httpx.AsyncClient(
        base_url=KALSHI_API_BASE_URL,
        timeout=10.0,
    ) as http_client:
        client = KalshiClient(
            http_client,
            api_key_id=settings.api_key_id,
            private_key=private_key,
        )

        market_response = await client.get_market(
            settings.demo_market_ticker,
        )

        market = market_response.market

        orderbook_response = await client.get_market_orderbook(
            ticker=market.ticker,
            depth=5,
        )

        trades_response = await client.get_trades(
            ticker=market.ticker,
            limit=5,
        )

        snapshot = build_market_snapshot(
            market=market,
            orderbook_response=orderbook_response,
            trades_response=trades_response,
            observed_at=datetime.now(UTC),
        )

        quote_quantity = settings.demo_quote_quantity
        max_quote_quantity = settings.demo_quote_quantity

        quote_decision = decide_quotes(
            snapshot,
            quote_quantity=quote_quantity,
        )

        positions = await client.get_positions(ticker=market.ticker, limit=10)

        market_position = next(
            (
                position
                for position in positions.market_positions
                if position.ticker == market.ticker
            ),
            None,
        )

        market_exposure_dollars = (
            market_position.market_exposure_dollars
            if market_position is not None
            else Decimal("0.00")
        )

        balance = await client.get_balance()

        now = datetime.now(UTC)
        risk_decision = evaluate_quote_risk(
            quote_decision,
            max_quote_quantity=max_quote_quantity,
            market_status=snapshot.status,
            observed_at=snapshot.observed_at,
            now=now,
            max_observed_age_seconds=settings.demo_max_observed_age_seconds,
            market_exposure_dollars=market_exposure_dollars,
            max_market_exposure_dollars=settings.demo_max_market_exposure_dollars,
            available_balance_dollars=balance.balance_dollars,
            minimum_available_balance_dollars=settings.demo_min_available_balance_dollars,
        )

        execution_plan = create_execution_plan(
            quote_decision,
            risk_decision,
        )

        position = (
            market_position.position_fp
            if market_position is not None
            else Decimal("0.00")
        )
        inventory_action = decide_inventory_action(position)

        if inventory_action is not None and can_flatten_inventory(
            market_status=snapshot.status,
            observed_at=snapshot.observed_at,
            now=now,
            max_observed_age_seconds=settings.demo_max_observed_age_seconds,
        ):
            flattening_order_intent = create_flattening_order_intent(
                ticker=market.ticker,
                inventory_action=inventory_action,
                snapshot=snapshot,
            )
            execution_plan = ExecutionPlan(
                ticker=market.ticker,
                order_intents=(flattening_order_intent,),
            )

        reconciliation_decision = await reconcile_execution_plan(
            execution_plan,
            client=client,
            order_submission_enabled=settings.order_submission_enabled,
            order_cancellation_enabled=settings.order_cancellation_enabled,
            client_order_id_prefix=client_order_id_prefix,
        )

    best_yes_bid = snapshot.best_yes_bid
    best_yes_ask = snapshot.best_yes_ask
    yes_spread = snapshot.yes_spread
    yes_midpoint = snapshot.yes_midpoint

    logger.info(
        "demo_api_data_retrieved",
        ticker=snapshot.ticker,
        title=snapshot.title,
        last_price=str(snapshot.last_price),
        best_yes_bid=(str(best_yes_bid.price) if best_yes_bid is not None else None),
        best_yes_ask=(str(best_yes_ask.price) if best_yes_ask is not None else None),
        yes_spread=(str(yes_spread) if yes_spread is not None else None),
        yes_midpoint=(str(yes_midpoint) if yes_midpoint is not None else None),
        yes_bid_level_count=len(snapshot.yes_bids),
        yes_ask_level_count=len(snapshot.yes_asks),
        recent_trade_count=len(snapshot.recent_trades),
        observed_at=snapshot.observed_at.isoformat(),
        balance_dollars=str(balance.balance_dollars),
        market_position_count=len(positions.market_positions),
        event_position_count=len(positions.event_positions),
    )

    yes_bid_proposal = quote_decision.yes_bid
    yes_ask_proposal = quote_decision.yes_ask

    logger.info(
        "strategy_quotes_decided",
        ticker=quote_decision.ticker,
        should_quote=quote_decision.should_quote,
        reason=quote_decision.reason.value,
        yes_bid_price=(
            str(yes_bid_proposal.price) if yes_bid_proposal is not None else None
        ),
        yes_bid_quantity=(
            str(yes_bid_proposal.quantity) if yes_bid_proposal is not None else None
        ),
        yes_ask_price=(
            str(yes_ask_proposal.price) if yes_ask_proposal is not None else None
        ),
        yes_ask_quantity=(
            str(yes_ask_proposal.quantity) if yes_ask_proposal is not None else None
        ),
    )

    logger.info(
        "quote_risk_evaluated",
        ticker=risk_decision.ticker,
        approved=risk_decision.approved,
        reason=risk_decision.reason.value,
        market_status=snapshot.status.value,
        max_quote_quantity=str(max_quote_quantity),
    )

    logger.info(
        "dry_run_execution_planned",
        ticker=execution_plan.ticker,
        has_order_intents=execution_plan.has_order_intents,
        order_intent_count=len(execution_plan.order_intents),
        order_intents=[
            {
                "side": order_intent.side.value,
                "price": str(order_intent.price),
                "quantity": str(order_intent.quantity),
            }
            for order_intent in execution_plan.order_intents
        ],
    )

    logger.info(
        "execution_plan_reconciled",
        ticker=execution_plan.ticker,
        order_submission_enabled=settings.order_submission_enabled,
        order_cancellation_enabled=settings.order_cancellation_enabled,
        planned_order_count=len(execution_plan.order_intents),
        orders_to_cancel=len(reconciliation_decision.order_ids_to_cancel),
        orders_to_submit=len(reconciliation_decision.order_intents_to_submit),
    )

    logger.info(
        "demo_api_data_cycle_completed",
        ticker=execution_plan.ticker,
        should_quote=quote_decision.should_quote,
        quote_reason=quote_decision.reason.value,
        risk_approved=risk_decision.approved,
        risk_reason=risk_decision.reason.value,
        planned_order_count=len(execution_plan.order_intents),
        orders_to_cancel=len(reconciliation_decision.order_ids_to_cancel),
        orders_to_submit=len(reconciliation_decision.order_intents_to_submit),
        inventory_action_side=(
            inventory_action.side.value if inventory_action is not None else None
        ),
        inventory_action_quantity=(
            str(inventory_action.quantity) if inventory_action is not None else None
        ),
    )


async def cancel_demo_lifecycle_orders(
    settings: Settings,
    *,
    client_order_id_prefix: str,
) -> None:
    if not settings.order_cancellation_enabled:
        return

    if settings.demo_market_ticker is None:
        return

    if settings.api_key_id is None:
        raise ValueError("KALSHI_BOT_API_KEY_ID is required.")

    if settings.private_key_path is None:
        raise ValueError("KALSHI_BOT_PRIVATE_KEY_PATH is required.")

    private_key = load_private_key(settings.private_key_path)

    async with httpx.AsyncClient(
        base_url=KALSHI_API_BASE_URL,
        timeout=10.0,
    ) as http_client:
        client = KalshiClient(
            http_client,
            api_key_id=settings.api_key_id,
            private_key=private_key,
        )

        resting_orders = await retrieve_all_resting_orders(
            client=client,
            ticker=settings.demo_market_ticker,
        )

        for order in resting_orders:
            if order.client_order_id is not None and order.client_order_id.startswith(
                client_order_id_prefix
            ):
                await client.cancel_order(order.order_id)


async def run_demo_lifecycle(settings: Settings) -> None:
    await recover_demo_lifecycle(settings)

    if settings.demo_market_ticker is None:
        raise ValueError("KALSHI_BOT_DEMO_MARKET_TICKER is required.")

    client_order_id_prefix = f"kbot-{uuid4().hex[:16]}-"
    lifecycle_state = LifecycleState(
        client_order_id_prefix=client_order_id_prefix,
        ticker=settings.demo_market_ticker,
    )
    save_lifecycle_state(lifecycle_state, state_path=settings.demo_lifecycle_state_path)

    try:
        for cycle_number in range(settings.demo_max_cycles):
            await retrieve_demo_api_data(
                settings,
                client_order_id_prefix=client_order_id_prefix,
            )

            is_final_cycle = cycle_number == settings.demo_max_cycles - 1

            if not is_final_cycle:
                await asyncio.sleep(
                    float(settings.demo_poll_interval_seconds),
                )
    except BaseException as lifecycle_error:
        try:
            await cancel_demo_lifecycle_orders(
                settings,
                client_order_id_prefix=client_order_id_prefix,
            )
        except BaseException as cleanup_error:  # noqa: BLE001
            raise BaseExceptionGroup(
                "Lifecycle cycle and cleanup both failed.",
                [lifecycle_error, cleanup_error],
            ) from None

        clear_lifecycle_state(settings.demo_lifecycle_state_path)
        raise

    else:
        await cancel_demo_lifecycle_orders(
            settings,
            client_order_id_prefix=client_order_id_prefix,
        )
        clear_lifecycle_state(settings.demo_lifecycle_state_path)


async def recover_demo_lifecycle(settings: Settings) -> None:
    if not settings.order_cancellation_enabled:
        return

    if not settings.demo_lifecycle_state_path.exists():
        return

    if settings.api_key_id is None:
        raise ValueError("KALSHI_BOT_API_KEY_ID is required.")

    if settings.private_key_path is None:
        raise ValueError("KALSHI_BOT_PRIVATE_KEY_PATH is required.")

    private_key = load_private_key(settings.private_key_path)

    async with httpx.AsyncClient(
        base_url=KALSHI_API_BASE_URL,
        timeout=10.0,
    ) as http_client:
        client = KalshiClient(
            http_client,
            api_key_id=settings.api_key_id,
            private_key=private_key,
        )

        await recover_interrupted_lifecycle(
            client=client,
            state_path=settings.demo_lifecycle_state_path,
            order_cancellation_enabled=settings.order_cancellation_enabled,
        )


def main() -> None:
    settings = Settings()
    configure_logging(settings)

    logger.info(
        "application_started",
        environment=settings.environment,
        log_level=settings.log_level,
    )

    try:
        market = Market(
            ticker="FEDRATE-2026-SEP",
            title="Federal Funds Rate",
            best_bid=Decimal("0.42"),
            best_ask=Decimal("0.44"),
            recent_trade_prices=[
                Decimal("0.41"),
                Decimal("0.42"),
                Decimal("0.43"),
                Decimal("0.42"),
                Decimal("0.45"),
            ],
        )
    except (TypeError, ValueError) as error:
        logger.error(
            "market_creation_failed",
            error=str(error),
            error_type=type(error).__name__,
        )
        return

    spread = market.calculate_spread()
    midpoint = market.calculate_midpoint()
    average_price = market.calculate_average_trade_price()

    logger.info(
        "market_analyzed",
        ticker=market.ticker,
        title=market.title,
        best_bid=market.best_bid,
        best_ask=market.best_ask,
        spread=spread,
        midpoint=midpoint,
        average_price=round(average_price, 2),
    )

    display_trade_prices(market.recent_trade_prices, midpoint)

    try:
        asyncio.run(run_demo_lifecycle(settings))
    except (OSError, ValueError, TypeError, httpx.HTTPError, ExceptionGroup) as error:
        if isinstance(error, httpx.HTTPStatusError):
            api_error_code = None
            api_error_message = None

            try:
                response_data = error.response.json()
            except ValueError:
                pass
            else:
                response_error = (
                    response_data.get("error")
                    if isinstance(response_data, dict)
                    else None
                )

                if isinstance(response_error, dict):
                    error_code = response_error.get("code")
                    error_message = response_error.get("message")

                    if isinstance(error_code, str):
                        api_error_code = error_code

                    if isinstance(error_message, str):
                        api_error_message = error_message

            logger.error(
                "demo_api_data_retrieval_failed",
                error=str(error),
                error_type=type(error).__name__,
                http_status_code=error.response.status_code,
                api_error_code=api_error_code,
                api_error_message=api_error_message,
            )
        else:
            logger.error(
                "demo_api_data_retrieval_failed",
                error=str(error),
                error_type=type(error).__name__,
            )


if __name__ == "__main__":
    main()

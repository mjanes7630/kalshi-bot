import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from http import HTTPStatus
from unittest.mock import ANY, AsyncMock, MagicMock, Mock, patch

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from kalshi_bot.api.client import KalshiClient
from kalshi_bot.api.models import KalshiMarketStatus
from kalshi_bot.config import Settings
from kalshi_bot.execution.models import (
    ExecutionPlan,
    OrderIntent,
    OrderSide,
    TimeInForce,
)
from kalshi_bot.execution.reconciliation import ReconciliationDecision
from kalshi_bot.main import (
    cancel_demo_lifecycle_orders,
    retrieve_demo_api_data,
    run_demo_lifecycle,
)


@pytest.fixture
def lifecycle_settings(tmp_path) -> Mock:
    private_key_path = tmp_path / "test-private-key.pem"
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    settings = Mock(spec=Settings)
    settings.api_key_id = "test-key-id"
    settings.private_key_path = private_key_path
    settings.demo_market_ticker = "TEST-MARKET"
    settings.demo_lifecycle_state_path = tmp_path / "lifecycle-state.json"
    settings.demo_max_cycles = 1
    settings.demo_poll_interval_seconds = Decimal(0)
    settings.order_submission_enabled = False
    settings.order_cancellation_enabled = False

    return settings


def test_retrieve_demo_api_data_uses_configured_market_and_quantity() -> None:
    settings = Mock(spec=Settings)
    settings.api_key_id = "test-key-id"
    settings.private_key_path = Mock()
    settings.order_submission_enabled = False
    settings.order_cancellation_enabled = False
    settings.demo_market_ticker = "TEST-MARKET"
    settings.demo_quote_quantity = Decimal("2.00")
    settings.demo_max_observed_age_seconds = 30
    settings.demo_max_market_exposure_dollars = Decimal("5.00")
    settings.demo_min_available_balance_dollars = Decimal("10.00")

    market = Mock()
    market.ticker = "TEST-MARKET"

    market_response = Mock()
    market_response.market = market

    execution_plan = Mock(spec=ExecutionPlan)
    execution_plan.ticker = "TEST-MARKET"
    execution_plan.has_order_intents = False
    execution_plan.order_intents = ()

    decision = ReconciliationDecision(
        order_ids_to_cancel=(),
        order_intents_to_submit=(),
    )

    snapshot = MagicMock()
    snapshot.status = KalshiMarketStatus.ACTIVE

    market_position = Mock()
    market_position.ticker = "TEST-MARKET"
    market_position.market_exposure_dollars = Decimal("1.25")
    market_position.position_fp = Decimal(0)

    positions_response = Mock()
    positions_response.market_positions = [market_position]
    positions_response.event_positions = []

    balance_response = Mock()
    balance_response.balance_dollars = Decimal("100.00")

    client = AsyncMock(spec=KalshiClient)
    client.get_market.return_value = market_response
    client.get_market_orderbook.return_value = Mock()
    client.get_trades.return_value = Mock()
    client.get_positions.return_value = positions_response
    client.get_balance.return_value = balance_response

    decide_quotes_mock = Mock()
    decide_quotes_mock.return_value.should_quote = True
    decide_quotes_mock.return_value.reason.value = "quoted"

    evaluate_quote_risk_mock = Mock()
    evaluate_quote_risk_mock.return_value.approved = True
    evaluate_quote_risk_mock.return_value.reason.value = "approved"

    with (
        patch(
            "kalshi_bot.main.build_market_snapshot",
            return_value=snapshot,
        ),
        patch(
            "kalshi_bot.main.decide_quotes",
            decide_quotes_mock,
        ),
        patch(
            "kalshi_bot.main.evaluate_quote_risk",
            evaluate_quote_risk_mock,
        ),
        patch(
            "kalshi_bot.main.create_execution_plan",
            return_value=execution_plan,
        ),
        patch(
            "kalshi_bot.main.reconcile_execution_plan",
            new=AsyncMock(return_value=decision),
        ) as reconcile_mock,
        patch("kalshi_bot.main.logger.info") as logger_info,
    ):
        asyncio.run(retrieve_demo_api_data(settings, client=client))

    client.get_balance.assert_awaited_once_with()
    client.get_market.assert_awaited_once_with("TEST-MARKET")
    client.get_positions.assert_awaited_once_with(
        ticker="TEST-MARKET",
        limit=10,
    )
    client.get_markets.assert_not_awaited()
    decide_quotes_mock.assert_called_once_with(
        snapshot,
        quote_quantity=Decimal("2.00"),
    )

    evaluate_quote_risk_mock.assert_called_once_with(
        decide_quotes_mock.return_value,
        max_quote_quantity=Decimal("2.00"),
        market_status=snapshot.status,
        observed_at=snapshot.observed_at,
        now=ANY,
        max_observed_age_seconds=30,
        market_exposure_dollars=Decimal("1.25"),
        max_market_exposure_dollars=Decimal("5.00"),
        available_balance_dollars=Decimal("100.00"),
        minimum_available_balance_dollars=Decimal("10.00"),
    )

    reconcile_mock.assert_awaited_once_with(
        execution_plan,
        client=client,
        order_submission_enabled=False,
        order_cancellation_enabled=False,
        client_order_id_prefix=None,
    )

    logger_info.assert_any_call(
        "demo_api_data_cycle_completed",
        ticker="TEST-MARKET",
        should_quote=True,
        quote_reason="quoted",
        risk_approved=True,
        risk_reason="approved",
        planned_order_count=0,
        orders_to_cancel=0,
        orders_to_submit=0,
        inventory_action_side=None,
        inventory_action_quantity=None,
    )

    logger_info.assert_any_call(
        "quote_risk_evaluated",
        ticker=ANY,
        approved=True,
        reason="approved",
        max_quote_quantity="2.00",
        market_status="active",
    )


def test_retrieve_demo_api_data_requires_demo_market_ticker() -> None:
    settings = Mock(spec=Settings)
    settings.demo_market_ticker = None
    client = AsyncMock(spec=KalshiClient)

    with pytest.raises(
        ValueError,
        match="KALSHI_BOT_DEMO_MARKET_TICKER is required.",
    ):
        asyncio.run(retrieve_demo_api_data(settings, client=client))


def test_retrieve_demo_api_data_requires_demo_quote_quantity() -> None:
    settings = Mock(spec=Settings)
    settings.demo_market_ticker = "TEST-MARKET"
    settings.demo_quote_quantity = None
    client = AsyncMock(spec=KalshiClient)

    with pytest.raises(
        ValueError,
        match="KALSHI_BOT_DEMO_QUOTE_QUANTITY is required.",
    ):
        asyncio.run(retrieve_demo_api_data(settings, client=client))


def test_run_demo_lifecycle_runs_configured_number_of_cycles(
    lifecycle_settings,
) -> None:
    settings = lifecycle_settings
    settings.demo_max_cycles = 3
    settings.demo_poll_interval_seconds = Decimal("2.50")

    with (
        patch(
            "kalshi_bot.main.retrieve_demo_api_data",
            new=AsyncMock(),
        ) as retrieve_mock,
        patch(
            "kalshi_bot.main.asyncio.sleep",
            new=AsyncMock(),
        ) as sleep_mock,
    ):
        asyncio.run(run_demo_lifecycle(settings))

    assert retrieve_mock.await_count == 3
    assert sleep_mock.await_args_list == [
        ((2.5,),),
        ((2.5,),),
    ]


def test_run_demo_lifecycle_does_not_sleep_after_final_cycle(
    lifecycle_settings,
) -> None:
    settings = lifecycle_settings
    settings.demo_poll_interval_seconds = Decimal("2.50")

    with (
        patch(
            "kalshi_bot.main.retrieve_demo_api_data",
            new=AsyncMock(),
        ),
        patch(
            "kalshi_bot.main.asyncio.sleep",
            new=AsyncMock(),
        ) as sleep_mock,
    ):
        asyncio.run(run_demo_lifecycle(settings))

    sleep_mock.assert_not_awaited()


def test_run_demo_lifecycle_reuses_one_session_prefix_for_every_cycle(
    lifecycle_settings,
) -> None:
    settings = lifecycle_settings
    settings.demo_max_cycles = 3

    with patch(
        "kalshi_bot.main.retrieve_demo_api_data",
        new=AsyncMock(),
    ) as retrieve_mock:
        asyncio.run(run_demo_lifecycle(settings))

    prefixes = [
        call.kwargs["client_order_id_prefix"] for call in retrieve_mock.await_args_list
    ]

    assert len(prefixes) == 3
    assert prefixes[0].startswith("kbot-")
    assert prefixes[0].endswith("-")
    assert len(set(prefixes)) == 1


def test_run_demo_lifecycle_cleans_up_session_orders_after_final_cycle(
    lifecycle_settings,
) -> None:
    settings = lifecycle_settings

    with (
        patch(
            "kalshi_bot.main.retrieve_demo_api_data",
            new=AsyncMock(),
        ) as retrieve_mock,
        patch(
            "kalshi_bot.main.cancel_demo_lifecycle_orders",
            new=AsyncMock(),
        ) as cancel_mock,
    ):
        asyncio.run(run_demo_lifecycle(settings))

    client_order_id_prefix = retrieve_mock.await_args.kwargs["client_order_id_prefix"]

    cancel_mock.assert_awaited_once_with(
        settings,
        client=ANY,
        client_order_id_prefix=client_order_id_prefix,
    )


def test_run_demo_lifecycle_cleans_up_session_orders_when_cycle_fails(
    lifecycle_settings,
) -> None:
    settings = lifecycle_settings

    cycle_error = RuntimeError("Lifecycle cycle failed.")

    with (
        patch(
            "kalshi_bot.main.retrieve_demo_api_data",
            new=AsyncMock(side_effect=cycle_error),
        ) as retrieve_mock,
        patch(
            "kalshi_bot.main.cancel_demo_lifecycle_orders",
            new=AsyncMock(),
        ) as cancel_mock,
        pytest.raises(RuntimeError, match="Lifecycle cycle failed."),
    ):
        asyncio.run(run_demo_lifecycle(settings))

    client_order_id_prefix = retrieve_mock.await_args.kwargs["client_order_id_prefix"]

    cancel_mock.assert_awaited_once_with(
        settings,
        client=ANY,
        client_order_id_prefix=client_order_id_prefix,
    )


def test_cancel_demo_lifecycle_orders_cancels_only_owned_orders() -> None:
    settings = Mock(spec=Settings)
    settings.api_key_id = "test-key-id"
    settings.private_key_path = Mock()
    settings.demo_market_ticker = "TEST-MARKET"
    settings.order_cancellation_enabled = True

    owned_order = Mock()
    owned_order.order_id = "owned-order-123"
    owned_order.client_order_id = "kbot-session-1234-order-id"

    unowned_order = Mock()
    unowned_order.order_id = "manual-order-456"
    unowned_order.client_order_id = "manual-order-id"

    client = AsyncMock(spec=KalshiClient)

    with patch(
        "kalshi_bot.main.retrieve_all_resting_orders",
        new=AsyncMock(return_value=(owned_order, unowned_order)),
    ) as retrieve_orders_mock:
        asyncio.run(
            cancel_demo_lifecycle_orders(
                settings,
                client=client,
                client_order_id_prefix="kbot-session-1234-",
            )
        )

    retrieve_orders_mock.assert_awaited_once_with(
        client=client,
        ticker="TEST-MARKET",
    )
    client.cancel_order.assert_awaited_once_with("owned-order-123")


def test_retrieve_demo_api_data_reconciles_inventory_flattening_order() -> None:
    settings = Mock(spec=Settings)
    settings.api_key_id = "test-key-id"
    settings.private_key_path = Mock()
    settings.order_submission_enabled = True
    settings.order_cancellation_enabled = True
    settings.demo_market_ticker = "TEST-MARKET"
    settings.demo_quote_quantity = Decimal("2.00")
    settings.demo_max_observed_age_seconds = 30
    settings.demo_max_market_exposure_dollars = Decimal("5.00")
    settings.demo_min_available_balance_dollars = Decimal("10.00")

    market = Mock()
    market.ticker = "TEST-MARKET"

    market_response = Mock()
    market_response.market = market

    snapshot = MagicMock()
    snapshot.ticker = "TEST-MARKET"
    snapshot.status = KalshiMarketStatus.ACTIVE
    snapshot.observed_at = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

    market_position = Mock()
    market_position.ticker = "TEST-MARKET"
    market_position.position_fp = Decimal("2.00")
    market_position.market_exposure_dollars = Decimal("1.25")

    positions_response = Mock()
    positions_response.market_positions = [market_position]
    positions_response.event_positions = []

    balance_response = Mock()
    balance_response.balance_dollars = Decimal("100.00")

    flattening_intent = OrderIntent(
        ticker="TEST-MARKET",
        side=OrderSide.SELL,
        price=Decimal("0.4200"),
        quantity=Decimal("2.00"),
        post_only=False,
        time_in_force=TimeInForce.IMMEDIATE_OR_CANCEL,
    )
    flattening_plan = ExecutionPlan(
        ticker="TEST-MARKET",
        order_intents=(flattening_intent,),
    )

    reconciliation_decision = ReconciliationDecision(
        order_ids_to_cancel=(),
        order_intents_to_submit=(),
    )

    client = AsyncMock(spec=KalshiClient)
    client.get_market.return_value = market_response
    client.get_market_orderbook.return_value = Mock()
    client.get_trades.return_value = Mock()
    client.get_positions.return_value = positions_response
    client.get_balance.return_value = balance_response

    with (
        patch(
            "kalshi_bot.main.build_market_snapshot",
            return_value=snapshot,
        ),
        patch("kalshi_bot.main.decide_quotes"),
        patch("kalshi_bot.main.evaluate_quote_risk"),
        patch("kalshi_bot.main.create_execution_plan"),
        patch(
            "kalshi_bot.main.create_flattening_order_intent",
            return_value=flattening_intent,
        ) as create_flattening_intent_mock,
        patch(
            "kalshi_bot.main.reconcile_execution_plan",
            new=AsyncMock(return_value=reconciliation_decision),
        ) as reconcile_mock,
        patch(
            "kalshi_bot.main.can_flatten_inventory",
            return_value=True,
        ) as can_flatten_inventory_mock,
        patch("kalshi_bot.main.logger.info") as logger_info,
    ):
        asyncio.run(retrieve_demo_api_data(settings, client=client))

    create_flattening_intent_mock.assert_called_once()
    reconcile_mock.assert_awaited_once_with(
        flattening_plan,
        client=client,
        order_submission_enabled=True,
        order_cancellation_enabled=True,
        client_order_id_prefix=None,
    )
    can_flatten_inventory_mock.assert_called_once_with(
        market_status=KalshiMarketStatus.ACTIVE,
        observed_at=snapshot.observed_at,
        now=ANY,
        max_observed_age_seconds=30,
    )

    logger_info.assert_any_call(
        "demo_api_data_cycle_completed",
        ticker="TEST-MARKET",
        should_quote=ANY,
        quote_reason=ANY,
        risk_approved=ANY,
        risk_reason=ANY,
        planned_order_count=1,
        orders_to_cancel=0,
        orders_to_submit=0,
        inventory_action_side="sell",
        inventory_action_quantity="2.00",
    )


def test_run_demo_lifecycle_cleans_up_session_orders_when_read_retry_is_exhausted(
    lifecycle_settings,
) -> None:
    settings = lifecycle_settings

    request = httpx.Request(
        "GET",
        "https://example.test/trade-api/v2/markets/TEST-MARKET",
    )
    response = httpx.Response(
        HTTPStatus.TOO_MANY_REQUESTS,
        request=request,
    )
    retry_error = httpx.HTTPStatusError(
        "Client error '429 Too Many Requests'",
        request=request,
        response=response,
    )

    with (
        patch(
            "kalshi_bot.main.retrieve_demo_api_data",
            new=AsyncMock(side_effect=retry_error),
        ) as retrieve_mock,
        patch(
            "kalshi_bot.main.cancel_demo_lifecycle_orders",
            new=AsyncMock(),
        ) as cancel_mock,
        pytest.raises(httpx.HTTPStatusError, match="429 Too Many Requests"),
    ):
        asyncio.run(run_demo_lifecycle(settings))

    client_order_id_prefix = retrieve_mock.await_args.kwargs["client_order_id_prefix"]

    cancel_mock.assert_awaited_once_with(
        settings,
        client=ANY,
        client_order_id_prefix=client_order_id_prefix,
    )


def test_run_demo_lifecycle_preserves_read_failure_when_session_cleanup_fails(
    lifecycle_settings,
) -> None:
    settings = lifecycle_settings

    request = httpx.Request(
        "GET",
        "https://example.test/trade-api/v2/markets/TEST-MARKET",
    )
    response = httpx.Response(
        HTTPStatus.TOO_MANY_REQUESTS,
        request=request,
    )
    retry_error = httpx.HTTPStatusError(
        "Client error '429 Too Many Requests'",
        request=request,
        response=response,
    )
    cleanup_error = RuntimeError("Session cleanup failed.")

    with (
        patch(
            "kalshi_bot.main.retrieve_demo_api_data",
            new=AsyncMock(side_effect=retry_error),
        ),
        patch(
            "kalshi_bot.main.cancel_demo_lifecycle_orders",
            new=AsyncMock(side_effect=cleanup_error),
        ),
        pytest.raises(ExceptionGroup) as error,
    ):
        asyncio.run(run_demo_lifecycle(settings))

    assert error.value.message == "Lifecycle cycle and cleanup both failed."
    assert error.value.exceptions == (retry_error, cleanup_error)


def test_run_demo_lifecycle_raises_cleanup_failure_after_successful_cycles(
    lifecycle_settings,
) -> None:
    settings = lifecycle_settings

    cleanup_error = RuntimeError("Session cleanup failed.")

    with (
        patch(
            "kalshi_bot.main.retrieve_demo_api_data",
            new=AsyncMock(),
        ),
        patch(
            "kalshi_bot.main.cancel_demo_lifecycle_orders",
            new=AsyncMock(side_effect=cleanup_error),
        ),
        pytest.raises(RuntimeError, match="Session cleanup failed."),
    ):
        asyncio.run(run_demo_lifecycle(settings))


def test_run_demo_lifecycle_cleans_up_session_orders_when_cancelled(
    lifecycle_settings,
) -> None:
    settings = lifecycle_settings

    cancellation_error = asyncio.CancelledError()

    with (
        patch(
            "kalshi_bot.main.retrieve_demo_api_data",
            new=AsyncMock(side_effect=cancellation_error),
        ) as retrieve_mock,
        patch(
            "kalshi_bot.main.cancel_demo_lifecycle_orders",
            new=AsyncMock(),
        ) as cancel_mock,
        pytest.raises(asyncio.CancelledError),
    ):
        asyncio.run(run_demo_lifecycle(settings))

    client_order_id_prefix = retrieve_mock.await_args.kwargs["client_order_id_prefix"]

    cancel_mock.assert_awaited_once_with(
        settings,
        client=ANY,
        client_order_id_prefix=client_order_id_prefix,
    )


def test_run_demo_lifecycle_preserves_cancellation_when_session_cleanup_fails(
    lifecycle_settings,
) -> None:
    settings = lifecycle_settings

    cancellation_error = asyncio.CancelledError()
    cleanup_error = RuntimeError("Session cleanup failed.")

    with (
        patch(
            "kalshi_bot.main.retrieve_demo_api_data",
            new=AsyncMock(side_effect=cancellation_error),
        ),
        patch(
            "kalshi_bot.main.cancel_demo_lifecycle_orders",
            new=AsyncMock(side_effect=cleanup_error),
        ),
        pytest.raises(BaseExceptionGroup) as error,
    ):
        asyncio.run(run_demo_lifecycle(settings))

    assert error.value.message == "Lifecycle cycle and cleanup both failed."
    assert error.value.exceptions == (cancellation_error, cleanup_error)


def test_run_demo_lifecycle_persists_session_state_before_first_cycle(
    lifecycle_settings,
) -> None:
    settings = lifecycle_settings
    state_path = settings.demo_lifecycle_state_path

    async def run_test() -> None:
        with (
            patch(
                "kalshi_bot.main.save_lifecycle_state",
            ) as save_lifecycle_state,
            patch(
                "kalshi_bot.main.retrieve_demo_api_data",
                new_callable=AsyncMock,
            ) as retrieve_demo_api_data,
            patch(
                "kalshi_bot.main.cancel_demo_lifecycle_orders",
                new_callable=AsyncMock,
            ),
            patch(
                "kalshi_bot.main.clear_lifecycle_state",
            ),
        ):
            await run_demo_lifecycle(settings)

        save_lifecycle_state.assert_called_once()
        lifecycle_state = save_lifecycle_state.call_args.args[0]

        assert lifecycle_state.ticker == "TEST-MARKET"
        assert lifecycle_state.client_order_id_prefix.startswith("kbot-")
        assert save_lifecycle_state.call_args.kwargs["state_path"] == state_path
        retrieve_demo_api_data.assert_awaited_once_with(
            settings,
            client=ANY,
            client_order_id_prefix=lifecycle_state.client_order_id_prefix,
        )

    asyncio.run(run_test())


def test_run_demo_lifecycle_clears_state_after_successful_cleanup(
    lifecycle_settings,
) -> None:
    settings = lifecycle_settings

    async def run_test() -> None:
        with (
            patch(
                "kalshi_bot.main.retrieve_demo_api_data",
                new_callable=AsyncMock,
            ),
            patch(
                "kalshi_bot.main.cancel_demo_lifecycle_orders",
                new_callable=AsyncMock,
            ),
            patch(
                "kalshi_bot.main.clear_lifecycle_state",
            ) as clear_lifecycle_state,
        ):
            await run_demo_lifecycle(settings)

        clear_lifecycle_state.assert_called_once_with(
            settings.demo_lifecycle_state_path,
        )

    asyncio.run(run_test())


def test_run_demo_lifecycle_clears_state_after_failed_cycle_cleanup_succeeds(
    lifecycle_settings,
) -> None:
    settings = lifecycle_settings
    settings.order_cancellation_enabled = True
    lifecycle_error = RuntimeError("Cycle failed.")

    async def run_test() -> None:
        with (
            patch(
                "kalshi_bot.main.retrieve_demo_api_data",
                new=AsyncMock(side_effect=lifecycle_error),
            ),
            patch(
                "kalshi_bot.main.cancel_demo_lifecycle_orders",
                new_callable=AsyncMock,
            ) as cancel_demo_lifecycle_orders,
            patch(
                "kalshi_bot.main.clear_lifecycle_state",
            ) as clear_lifecycle_state,
            pytest.raises(RuntimeError, match="Cycle failed."),
        ):
            await run_demo_lifecycle(settings)

        cancel_demo_lifecycle_orders.assert_awaited_once()
        clear_lifecycle_state.assert_called_once_with(
            settings.demo_lifecycle_state_path,
        )

    asyncio.run(run_test())


def test_run_demo_lifecycle_attempts_restart_recovery_before_new_cycle(
    lifecycle_settings,
) -> None:
    settings = lifecycle_settings
    settings.order_cancellation_enabled = True

    async def run_test() -> None:
        with (
            patch(
                "kalshi_bot.main.recover_demo_lifecycle",
                new_callable=AsyncMock,
            ) as recover_demo_lifecycle,
            patch(
                "kalshi_bot.main.save_lifecycle_state",
            ),
            patch(
                "kalshi_bot.main.retrieve_demo_api_data",
                new_callable=AsyncMock,
            ),
            patch(
                "kalshi_bot.main.cancel_demo_lifecycle_orders",
                new_callable=AsyncMock,
            ),
            patch(
                "kalshi_bot.main.clear_lifecycle_state",
            ),
        ):
            await run_demo_lifecycle(settings)

        recover_demo_lifecycle.assert_awaited_once_with(
            settings,
            client=ANY,
        )

    asyncio.run(run_test())


def test_run_demo_lifecycle_reuses_one_authenticated_client(
    lifecycle_settings,
) -> None:
    settings = lifecycle_settings

    http_client = AsyncMock()
    http_client.__aenter__.return_value = http_client
    client = AsyncMock(spec=KalshiClient)

    async def run_test() -> None:
        with (
            patch("kalshi_bot.api.session.load_private_key") as load_private_key,
            patch(
                "kalshi_bot.api.session.httpx.AsyncClient",
                return_value=http_client,
            ),
            patch(
                "kalshi_bot.api.session.KalshiClient",
                return_value=client,
            ) as kalshi_client,
            patch(
                "kalshi_bot.main.recover_demo_lifecycle",
                new_callable=AsyncMock,
            ) as recover_demo_lifecycle,
            patch(
                "kalshi_bot.main.retrieve_demo_api_data",
                new_callable=AsyncMock,
            ) as retrieve_demo_api_data,
            patch(
                "kalshi_bot.main.cancel_demo_lifecycle_orders",
                new_callable=AsyncMock,
            ) as cancel_demo_lifecycle_orders,
            patch("kalshi_bot.main.save_lifecycle_state"),
            patch("kalshi_bot.main.clear_lifecycle_state"),
        ):
            await run_demo_lifecycle(settings)

        load_private_key.assert_called_once_with(settings.private_key_path)
        kalshi_client.assert_called_once_with(
            http_client,
            api_key_id="test-key-id",
            private_key=load_private_key.return_value,
        )
        recover_demo_lifecycle.assert_awaited_once_with(
            settings,
            client=client,
        )

        client_order_id_prefix = (
            retrieve_demo_api_data.await_args.kwargs["client_order_id_prefix"]
        )
        retrieve_demo_api_data.assert_awaited_once_with(
            settings,
            client=client,
            client_order_id_prefix=client_order_id_prefix,
        )
        cancel_demo_lifecycle_orders.assert_awaited_once_with(
            settings,
            client=client,
            client_order_id_prefix=client_order_id_prefix,
        )

    asyncio.run(run_test())
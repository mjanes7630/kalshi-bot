import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from kalshi_bot.api.client import KalshiClient
from kalshi_bot.config import Settings
from kalshi_bot.execution.models import ExecutionPlan
from kalshi_bot.execution.reconciliation import ReconciliationDecision
from kalshi_bot.main import (
    cancel_demo_lifecycle_orders,
    retrieve_demo_api_data,
    run_demo_lifecycle,
)


def test_retrieve_demo_api_data_uses_configured_market_and_quantity() -> None:
    settings = Mock(spec=Settings)
    settings.api_key_id = "test-key-id"
    settings.private_key_path = Mock()
    settings.order_submission_enabled = False
    settings.order_cancellation_enabled = False
    settings.demo_market_ticker = "TEST-MARKET"
    settings.demo_quote_quantity = Decimal("2.00")

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

    http_client = AsyncMock()
    http_client.__aenter__.return_value = http_client

    client = AsyncMock(spec=KalshiClient)
    client.get_market.return_value = market_response
    client.get_market_orderbook.return_value = Mock()
    client.get_trades.return_value = Mock()

    with (
        patch("kalshi_bot.main.load_private_key"),
        patch("kalshi_bot.main.httpx.AsyncClient", return_value=http_client),
        patch("kalshi_bot.main.KalshiClient", return_value=client),
        patch(
            "kalshi_bot.main.build_market_snapshot",
            return_value=snapshot,
        ),
        patch("kalshi_bot.main.decide_quotes") as decide_quotes_mock,
        patch("kalshi_bot.main.evaluate_quote_risk"),
        patch(
            "kalshi_bot.main.create_execution_plan",
            return_value=execution_plan,
        ),
        patch(
            "kalshi_bot.main.reconcile_execution_plan",
            new=AsyncMock(return_value=decision),
        ) as reconcile_mock,
    ):
        asyncio.run(retrieve_demo_api_data(settings))

    client.get_market.assert_awaited_once_with("TEST-MARKET")
    client.get_markets.assert_not_awaited()
    decide_quotes_mock.assert_called_once_with(
        snapshot,
        quote_quantity=Decimal("2.00"),
    )
    reconcile_mock.assert_awaited_once_with(
        execution_plan,
        client=client,
        order_submission_enabled=False,
        order_cancellation_enabled=False,
        client_order_id_prefix=None,
    )


def test_retrieve_demo_api_data_requires_demo_market_ticker() -> None:
    settings = Mock(spec=Settings)
    settings.api_key_id = "test-key-id"
    settings.private_key_path = Mock()
    settings.demo_market_ticker = None

    with pytest.raises(
        ValueError,
        match="KALSHI_BOT_DEMO_MARKET_TICKER is required.",
    ):
        asyncio.run(retrieve_demo_api_data(settings))


def test_retrieve_demo_api_data_requires_demo_quote_quantity() -> None:
    settings = Mock(spec=Settings)
    settings.api_key_id = "test-key-id"
    settings.private_key_path = Mock()
    settings.demo_market_ticker = "TEST-MARKET"
    settings.demo_quote_quantity = None

    with pytest.raises(
        ValueError,
        match="KALSHI_BOT_DEMO_QUOTE_QUANTITY is required.",
    ):
        asyncio.run(retrieve_demo_api_data(settings))


def test_run_demo_lifecycle_runs_configured_number_of_cycles() -> None:
    settings = Mock(spec=Settings)
    settings.demo_max_cycles = 3
    settings.demo_poll_interval_seconds = Decimal("2.50")
    settings.order_cancellation_enabled = False

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


def test_run_demo_lifecycle_does_not_sleep_after_final_cycle() -> None:
    settings = Mock(spec=Settings)
    settings.demo_max_cycles = 1
    settings.demo_poll_interval_seconds = Decimal("2.50")
    settings.order_cancellation_enabled = False

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


def test_run_demo_lifecycle_reuses_one_session_prefix_for_every_cycle() -> None:
    settings = Mock(spec=Settings)
    settings.demo_max_cycles = 3
    settings.demo_poll_interval_seconds = Decimal(0)
    settings.order_cancellation_enabled = False

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


def test_run_demo_lifecycle_cleans_up_session_orders_after_final_cycle() -> None:
    settings = Mock(spec=Settings)
    settings.demo_max_cycles = 1
    settings.demo_poll_interval_seconds = Decimal(0)

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
        client_order_id_prefix=client_order_id_prefix,
    )


def test_run_demo_lifecycle_cleans_up_session_orders_when_cycle_fails() -> None:
    settings = Mock(spec=Settings)
    settings.demo_max_cycles = 1
    settings.demo_poll_interval_seconds = Decimal(0)

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

    http_client = AsyncMock()
    http_client.__aenter__.return_value = http_client

    client = AsyncMock(spec=KalshiClient)

    with (
        patch("kalshi_bot.main.load_private_key"),
        patch("kalshi_bot.main.httpx.AsyncClient", return_value=http_client),
        patch("kalshi_bot.main.KalshiClient", return_value=client),
        patch(
            "kalshi_bot.main.retrieve_all_resting_orders",
            new=AsyncMock(return_value=(owned_order, unowned_order)),
        ) as retrieve_orders_mock,
    ):
        asyncio.run(
            cancel_demo_lifecycle_orders(
                settings,
                client_order_id_prefix="kbot-session-1234-",
            )
        )

    retrieve_orders_mock.assert_awaited_once_with(
        client=client,
        ticker="TEST-MARKET",
    )
    client.cancel_order.assert_awaited_once_with("owned-order-123")

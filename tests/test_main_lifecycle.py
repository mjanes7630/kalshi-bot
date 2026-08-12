import asyncio
from unittest.mock import AsyncMock, Mock, patch

from kalshi_bot.api.client import KalshiClient
from kalshi_bot.config import Settings
from kalshi_bot.execution.models import ExecutionPlan
from kalshi_bot.execution.reconciliation import ReconciliationDecision
from kalshi_bot.main import retrieve_demo_api_data


def test_retrieve_demo_api_data_reconciles_execution_plan() -> None:
    settings = Mock(spec=Settings)
    settings.api_key_id = "test-key-id"
    settings.private_key_path = Mock()
    settings.order_submission_enabled = False
    settings.order_cancellation_enabled = False

    market = Mock()
    market.ticker = "TEST-MARKET"

    markets_response = Mock()
    markets_response.markets = [market]

    execution_plan = Mock(spec=ExecutionPlan)
    execution_plan.ticker = "TEST-MARKET"
    execution_plan.has_order_intents = False
    execution_plan.order_intents = ()

    decision = ReconciliationDecision(
        order_ids_to_cancel=(),
        order_intents_to_submit=(),
    )

    http_client = AsyncMock()
    http_client.__aenter__.return_value = http_client

    client = AsyncMock(spec=KalshiClient)
    client.get_markets.return_value = markets_response
    client.get_market_orderbook.return_value = Mock()
    client.get_trades.return_value = Mock()

    with (
        patch("kalshi_bot.main.load_private_key"),
        patch("kalshi_bot.main.httpx.AsyncClient", return_value=http_client),
        patch("kalshi_bot.main.KalshiClient", return_value=client),
        patch("kalshi_bot.main.build_market_snapshot"),
        patch("kalshi_bot.main.decide_quotes"),
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

    reconcile_mock.assert_awaited_once_with(
        execution_plan,
        client=client,
        order_submission_enabled=False,
        order_cancellation_enabled=False,
    )

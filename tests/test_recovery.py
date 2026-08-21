import asyncio
import json
from decimal import Decimal
from unittest.mock import AsyncMock, call

import pytest

from kalshi_bot.api.client import KalshiClient
from kalshi_bot.api.models import (
    GetOrdersResponse,
    KalshiContractSide,
    KalshiOrder,
    KalshiOrderSide,
)
from kalshi_bot.execution.recovery import recover_interrupted_lifecycle
from kalshi_bot.execution.state import (
    LifecycleState,
    load_lifecycle_state,
    save_lifecycle_state,
)


def test_recover_interrupted_lifecycle_cancels_only_prior_session_orders(
    tmp_path,
) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    save_lifecycle_state(
        LifecycleState(
            client_order_id_prefix="kbot-prior-session-",
            ticker="TEST-MARKET",
        ),
        state_path=state_path,
    )

    owned_order = KalshiOrder(
        order_id="owned-order-id",
        client_order_id="kbot-prior-session-order-1",
        ticker="TEST-MARKET",
        side=KalshiContractSide.YES,
        book_side=KalshiOrderSide.BID,
        yes_price_dollars=Decimal("0.4200"),
        remaining_count_fp=Decimal("1.00"),
        initial_count_fp=Decimal("1.00"),
        fill_count_fp=Decimal("0.00"),
    )
    unrelated_order = KalshiOrder(
        order_id="unrelated-order-id",
        client_order_id="another-bot-order-1",
        ticker="TEST-MARKET",
        side=KalshiContractSide.YES,
        book_side=KalshiOrderSide.BID,
        yes_price_dollars=Decimal("0.4200"),
        remaining_count_fp=Decimal("1.00"),
        initial_count_fp=Decimal("1.00"),
        fill_count_fp=Decimal("0.00"),
    )

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.get_orders.return_value = GetOrdersResponse(
            orders=[owned_order, unrelated_order],
            cursor="",
        )

        await recover_interrupted_lifecycle(
            client=client,
            state_path=state_path,
            order_cancellation_enabled=True,
        )

        client.cancel_order.assert_awaited_once_with("owned-order-id")

    asyncio.run(run_test())

    assert not state_path.exists()


def test_recover_interrupted_lifecycle_keeps_state_when_cancellation_fails(
    tmp_path,
) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    lifecycle_state = LifecycleState(
        client_order_id_prefix="kbot-prior-session-",
        ticker="TEST-MARKET",
    )
    save_lifecycle_state(
        lifecycle_state,
        state_path=state_path,
    )

    owned_order = KalshiOrder(
        order_id="owned-order-id",
        client_order_id="kbot-prior-session-order-1",
        ticker="TEST-MARKET",
        side=KalshiContractSide.YES,
        book_side=KalshiOrderSide.BID,
        yes_price_dollars=Decimal("0.4200"),
        fill_count_fp=Decimal("0.00"),
        remaining_count_fp=Decimal("1.00"),
        initial_count_fp=Decimal("1.00"),
    )

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.get_orders.return_value = GetOrdersResponse(
            orders=[owned_order],
            cursor="",
        )
        client.cancel_order.side_effect = RuntimeError("Cancellation failed.")

        with pytest.raises(ExceptionGroup) as errors:
            await recover_interrupted_lifecycle(
                client=client,
                state_path=state_path,
                order_cancellation_enabled=True,
            )

        assert len(errors.value.exceptions) == 1
        assert str(errors.value.exceptions[0]) == "Cancellation failed."
        client.cancel_order.assert_awaited_once_with("owned-order-id")

    asyncio.run(run_test())

    assert state_path.exists()
    assert load_lifecycle_state(state_path) == lifecycle_state


def test_recover_interrupted_lifecycle_does_nothing_without_saved_state(
    tmp_path,
) -> None:
    state_path = tmp_path / "lifecycle-state.json"

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)

        await recover_interrupted_lifecycle(
            client=client,
            state_path=state_path,
            order_cancellation_enabled=True,
        )

        client.get_orders.assert_not_awaited()
        client.cancel_order.assert_not_awaited()

    asyncio.run(run_test())


def test_recover_interrupted_lifecycle_preserves_state_when_cancellation_disabled(
    tmp_path,
) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    lifecycle_state = LifecycleState(
        client_order_id_prefix="kbot-prior-session-",
        ticker="TEST-MARKET",
    )
    save_lifecycle_state(
        lifecycle_state,
        state_path=state_path,
    )

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)

        await recover_interrupted_lifecycle(
            client=client,
            state_path=state_path,
            order_cancellation_enabled=False,
        )

        client.get_orders.assert_not_awaited()
        client.cancel_order.assert_not_awaited()

    asyncio.run(run_test())

    assert load_lifecycle_state(state_path) == lifecycle_state


def test_recover_interrupted_lifecycle_attempts_all_owned_cancellations_before_raising(
    tmp_path,
) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    lifecycle_state = LifecycleState(
        client_order_id_prefix="kbot-prior-session-",
        ticker="TEST-MARKET",
    )
    save_lifecycle_state(
        lifecycle_state,
        state_path=state_path,
    )

    first_owned_order = KalshiOrder(
        order_id="first-owned-order-id",
        client_order_id="kbot-prior-session-order-1",
        ticker="TEST-MARKET",
        side=KalshiContractSide.YES,
        book_side=KalshiOrderSide.BID,
        yes_price_dollars=Decimal("0.4200"),
        fill_count_fp=Decimal("0.00"),
        remaining_count_fp=Decimal("1.00"),
        initial_count_fp=Decimal("1.00"),
    )
    second_owned_order = KalshiOrder(
        order_id="second-owned-order-id",
        client_order_id="kbot-prior-session-order-2",
        ticker="TEST-MARKET",
        side=KalshiContractSide.YES,
        book_side=KalshiOrderSide.BID,
        yes_price_dollars=Decimal("0.4200"),
        fill_count_fp=Decimal("0.00"),
        remaining_count_fp=Decimal("1.00"),
        initial_count_fp=Decimal("1.00"),
    )

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.get_orders.return_value = GetOrdersResponse(
            orders=[first_owned_order, second_owned_order],
            cursor="",
        )
        client.cancel_order.side_effect = [
            RuntimeError("First cancellation failed."),
            None,
        ]

        with pytest.raises(ExceptionGroup) as error:
            await recover_interrupted_lifecycle(
                client=client,
                state_path=state_path,
                order_cancellation_enabled=True,
            )

        assert len(error.value.exceptions) == 1
        assert str(error.value.exceptions[0]) == "First cancellation failed."
        assert client.cancel_order.await_args_list == [
            call("first-owned-order-id"),
            call("second-owned-order-id"),
        ]

    asyncio.run(run_test())

    assert load_lifecycle_state(state_path) == lifecycle_state


def test_recover_interrupted_lifecycle_preserves_corrupted_state(
    tmp_path,
) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    corrupted_state = "{ this is not valid JSON"
    state_path.write_text(
        corrupted_state,
        encoding="utf-8",
    )

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)

        with pytest.raises(json.JSONDecodeError):
            await recover_interrupted_lifecycle(
                client=client,
                state_path=state_path,
                order_cancellation_enabled=True,
            )

        client.get_orders.assert_not_awaited()
        client.cancel_order.assert_not_awaited()

    asyncio.run(run_test())

    assert state_path.read_text(encoding="utf-8") == corrupted_state


def test_recover_interrupted_lifecycle_cancels_saved_order_ids_without_listing_orders(
    tmp_path,
) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    save_lifecycle_state(
        LifecycleState(
            client_order_id_prefix="kbot-prior-session-",
            ticker="TEST-MARKET",
            submitted_order_ids=(
                "saved-order-123",
                "saved-order-456",
            ),
        ),
        state_path=state_path,
    )

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.get_orders.return_value = GetOrdersResponse(
            orders=[],
            cursor="",
        )

        await recover_interrupted_lifecycle(
            client=client,
            state_path=state_path,
            order_cancellation_enabled=True,
        )

        client.get_orders.assert_not_awaited()
        assert client.cancel_order.await_args_list == [
            call("saved-order-123"),
            call("saved-order-456"),
        ]

    asyncio.run(run_test())

    assert not state_path.exists()


def test_recover_interrupted_lifecycle_removes_each_successfully_cancelled_id(
    tmp_path,
) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    lifecycle_state = LifecycleState(
        client_order_id_prefix="kbot-prior-session-",
        ticker="TEST-MARKET",
        submitted_order_ids=(
            "first-saved-order-id",
            "second-saved-order-id",
        ),
    )
    save_lifecycle_state(
        lifecycle_state,
        state_path=state_path,
    )

    async def run_test() -> None:
        client = AsyncMock(spec=KalshiClient)
        client.cancel_order.side_effect = [
            None,
            RuntimeError("Second cancellation failed."),
        ]

        with pytest.raises(ExceptionGroup) as errors:
            await recover_interrupted_lifecycle(
                client=client,
                state_path=state_path,
                order_cancellation_enabled=True,
            )

        assert str(errors.value.exceptions[0]) == "Second cancellation failed."
        client.get_orders.assert_not_awaited()
        assert client.cancel_order.await_args_list == [
            call("first-saved-order-id"),
            call("second-saved-order-id"),
        ]

    asyncio.run(run_test())

    assert load_lifecycle_state(state_path) == LifecycleState(
        client_order_id_prefix="kbot-prior-session-",
        ticker="TEST-MARKET",
        submitted_order_ids=("second-saved-order-id",),
    )

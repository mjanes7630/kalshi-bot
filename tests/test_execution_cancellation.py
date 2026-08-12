import asyncio
from unittest.mock import AsyncMock, Mock, call

import pytest

from kalshi_bot.api.client import KalshiClient
from kalshi_bot.api.models import CancelOrderResponse, GetOrdersResponse, KalshiOrder
from kalshi_bot.execution.cancellation import (
    cancel_all_resting_orders,
    retrieve_all_resting_orders,
)


def test_retrieve_all_resting_orders_follows_pagination() -> None:
    first_order = Mock(spec=KalshiOrder)
    first_order.order_id = "first-order-123"

    second_order = Mock(spec=KalshiOrder)
    second_order.order_id = "second-order-456"

    first_page = Mock(spec=GetOrdersResponse)
    first_page.orders = [first_order]
    first_page.cursor = "next-page"

    final_page = Mock(spec=GetOrdersResponse)
    final_page.orders = [second_order]
    final_page.cursor = ""

    client = AsyncMock(spec=KalshiClient)
    client.get_orders.side_effect = [
        first_page,
        final_page,
    ]

    result = asyncio.run(
        retrieve_all_resting_orders(client=client, ticker="TEST-MARKET")
    )

    assert result == (
        first_order,
        second_order,
    )
    assert client.get_orders.await_args_list == [
        call(
            status="resting",
            ticker="TEST-MARKET",
            limit=1000,
            cursor=None,
        ),
        call(
            status="resting",
            ticker="TEST-MARKET",
            limit=1000,
            cursor="next-page",
        ),
    ]
    client.cancel_order.assert_not_awaited()


def test_cancel_all_resting_orders_cancels_each_retrieved_order() -> None:
    first_order = Mock(spec=KalshiOrder)
    first_order.order_id = "first-order-123"

    second_order = Mock(spec=KalshiOrder)
    second_order.order_id = "second-order-456"

    page = Mock(spec=GetOrdersResponse)
    page.orders = [
        first_order,
        second_order,
    ]
    page.cursor = ""

    first_response = Mock(spec=CancelOrderResponse)
    second_response = Mock(spec=CancelOrderResponse)

    client = AsyncMock(spec=KalshiClient)
    client.get_orders.return_value = page
    client.cancel_order.side_effect = [
        first_response,
        second_response,
    ]

    result = asyncio.run(
        cancel_all_resting_orders(
            client=client,
            order_cancellation_enabled=True,
            ticker="TEST-MARKET",
        )
    )

    assert result == (
        first_response,
        second_response,
    )
    client.get_orders.assert_awaited_once_with(
        status="resting",
        ticker="TEST-MARKET",
        limit=1000,
        cursor=None,
    )
    assert client.cancel_order.await_args_list == [
        call("first-order-123"),
        call("second-order-456"),
    ]


def test_cancel_all_resting_orders_attempts_every_cancellation_when_some_fail() -> None:
    first_order = Mock(spec=KalshiOrder)
    first_order.order_id = "first-order-123"

    second_order = Mock(spec=KalshiOrder)
    second_order.order_id = "second-order-456"

    third_order = Mock(spec=KalshiOrder)
    third_order.order_id = "third-order-789"

    page = Mock(spec=GetOrdersResponse)
    page.orders = [
        first_order,
        second_order,
        third_order,
    ]
    page.cursor = ""

    successful_response = Mock(spec=CancelOrderResponse)
    first_error = RuntimeError("First cancellation failed.")
    third_error = RuntimeError("Third cancellation failed.")

    client = AsyncMock(spec=KalshiClient)
    client.get_orders.return_value = page
    client.cancel_order.side_effect = [
        first_error,
        successful_response,
        third_error,
    ]

    with pytest.raises(
        ExceptionGroup,
        match="One or more resting order cancellations failed.",
    ) as exception_info:
        asyncio.run(
            cancel_all_resting_orders(
                client=client,
                order_cancellation_enabled=True,
                ticker="TEST-MARKET",
            )
        )

    assert exception_info.value.exceptions == (
        first_error,
        third_error,
    )
    assert client.cancel_order.await_args_list == [
        call("first-order-123"),
        call("second-order-456"),
        call("third-order-789"),
    ]


def test_retrieve_all_resting_orders_rejects_repeated_cursor() -> None:
    first_page = Mock(spec=GetOrdersResponse)
    first_page.orders = []
    first_page.cursor = "repeated-page"

    repeated_page = Mock(spec=GetOrdersResponse)
    repeated_page.orders = []
    repeated_page.cursor = "repeated-page"

    client = AsyncMock(spec=KalshiClient)
    client.get_orders.side_effect = [
        first_page,
        repeated_page,
    ]

    with pytest.raises(
        RuntimeError,
        match="Order pagination returned a repeated cursor.",
    ):
        asyncio.run(retrieve_all_resting_orders(client=client, ticker="TEST-MARKET"))

    assert client.get_orders.await_args_list == [
        call(
            status="resting",
            ticker="TEST-MARKET",
            limit=1000,
            cursor=None,
        ),
        call(
            status="resting",
            ticker="TEST-MARKET",
            limit=1000,
            cursor="repeated-page",
        ),
    ]
    client.cancel_order.assert_not_awaited()


def test_cancel_all_resting_orders_does_not_call_api_when_disabled() -> None:
    client = AsyncMock(spec=KalshiClient)

    result = asyncio.run(
        cancel_all_resting_orders(
            client=client,
            order_cancellation_enabled=False,
            ticker="TEST-MARKET",
        )
    )

    assert result == ()
    client.get_orders.assert_not_awaited()
    client.cancel_order.assert_not_awaited()


def test_retrieve_all_resting_orders_filters_by_ticker() -> None:
    resting_order = Mock(spec=KalshiOrder)
    client = AsyncMock(spec=KalshiClient)
    client.get_orders.return_value = Mock(
        orders=[resting_order],
        cursor="",
    )

    orders = asyncio.run(
        retrieve_all_resting_orders(
            client=client,
            ticker="TEST-MARKET",
        )
    )

    assert orders == (resting_order,)
    client.get_orders.assert_awaited_once_with(
        status="resting",
        ticker="TEST-MARKET",
        limit=1000,
        cursor=None,
    )

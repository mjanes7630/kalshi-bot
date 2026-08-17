from http import HTTPStatus
from unittest.mock import AsyncMock, Mock, patch

import httpx

from kalshi_bot.config import Settings
from kalshi_bot.main import main


def test_main_logs_lifecycle_cancellation_exception_group() -> None:
    settings = Mock(spec=Settings)
    settings.environment = "development"
    settings.log_level = "INFO"

    lifecycle_error = ExceptionGroup(
        "One or more lifecycle order cancellations failed.",
        [RuntimeError("Cancellation failed.")],
    )

    with (
        patch("kalshi_bot.main.Settings", return_value=settings),
        patch("kalshi_bot.main.configure_logging"),
        patch(
            "kalshi_bot.main.run_demo_lifecycle",
            new=AsyncMock(side_effect=lifecycle_error),
        ),
        patch("kalshi_bot.main.logger") as logger,
    ):
        main()

    logger.error.assert_called_once_with(
        "demo_api_data_retrieval_failed",
        error="One or more lifecycle order cancellations failed. (1 sub-exception)",
        error_type="ExceptionGroup",
    )


def test_main_logs_http_status_error_from_exhausted_read_retry() -> None:
    settings = Mock(spec=Settings)
    settings.environment = "development"
    settings.log_level = "INFO"

    request = httpx.Request(
        "GET",
        "https://example.test/trade-api/v2/markets",
    )
    response = httpx.Response(
        HTTPStatus.TOO_MANY_REQUESTS,
        request=request,
    )
    error = httpx.HTTPStatusError(
        "Client error '429 Too Many Requests'",
        request=request,
        response=response,
    )

    with (
        patch("kalshi_bot.main.Settings", return_value=settings),
        patch("kalshi_bot.main.configure_logging"),
        patch(
            "kalshi_bot.main.run_demo_lifecycle",
            new=AsyncMock(side_effect=error),
        ),
        patch("kalshi_bot.main.logger.error") as logger_error,
    ):
        main()

    logger_error.assert_called_once_with(
        "demo_api_data_retrieval_failed",
        error=str(error),
        error_type="HTTPStatusError",
        http_status_code=HTTPStatus.TOO_MANY_REQUESTS,
        api_error_code=None,
        api_error_message=None,
    )


def test_main_logs_safe_http_status_error_details() -> None:
    settings = Mock(spec=Settings)
    settings.environment = "development"
    settings.log_level = "INFO"

    request = httpx.Request(
        "POST",
        "https://external-api.demo.kalshi.co/trade-api/v2/portfolio/events/orders",
    )
    response = httpx.Response(
        HTTPStatus.FORBIDDEN,
        request=request,
        json={
            "error": {
                "code": "order_submission_forbidden",
                "message": "Order submission is not permitted.",
            }
        },
    )
    lifecycle_error = httpx.HTTPStatusError(
        "Client error '403 Forbidden'",
        request=request,
        response=response,
    )

    with (
        patch("kalshi_bot.main.Settings", return_value=settings),
        patch("kalshi_bot.main.configure_logging"),
        patch(
            "kalshi_bot.main.run_demo_lifecycle",
            new=AsyncMock(side_effect=lifecycle_error),
        ),
        patch("kalshi_bot.main.logger") as logger,
    ):
        main()

    logger.error.assert_called_once_with(
        "demo_api_data_retrieval_failed",
        error=str(lifecycle_error),
        error_type="HTTPStatusError",
        http_status_code=HTTPStatus.FORBIDDEN,
        api_error_code="order_submission_forbidden",
        api_error_message="Order submission is not permitted.",
    )

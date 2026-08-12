from unittest.mock import AsyncMock, Mock, patch

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
            "kalshi_bot.main.retrieve_demo_api_data",
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

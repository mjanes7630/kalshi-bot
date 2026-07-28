import json

import pytest
import structlog

from kalshi_bot.config import Settings
from kalshi_bot.logging_config import configure_logging


def test_development_logging_uses_console_renderer(
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = Settings(
        environment="development",
        log_level="INFO",
    )
    configure_logging(settings)

    logger = structlog.get_logger("test_logger")
    logger.info(
        "logging_test",
        price=42,
    )

    captured = capsys.readouterr()

    assert "logging_test" in captured.out
    assert "price=42" in captured.out
    assert "[test_logger]" in captured.out
    assert captured.err == ""


def test_production_logging_uses_json_renderer(
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = Settings(
        environment="production",
        log_level="INFO",
    )
    configure_logging(settings)

    logger = structlog.get_logger("test_logger")
    logger.info(
        "logging_test",
        price=42,
    )

    captured = capsys.readouterr()
    log_data = json.loads(captured.out)

    assert log_data["event"] == "logging_test"
    assert log_data["price"] == 42
    assert log_data["logger"] == "test_logger"
    assert log_data["level"] == "info"
    assert "timestamp" in log_data
    assert captured.err == ""


def test_logging_respects_configured_level(capsys: pytest.CaptureFixture[str]) -> None:
    settings = Settings(
        environment="development",
        log_level="WARNING",
    )
    configure_logging(settings)

    logger = structlog.get_logger("test_logger")
    logger.info("hidden_event")
    logger.warning("visable_event")

    captured = capsys.readouterr()

    assert "hidden_event" not in captured.out
    assert "visable_event" in captured.out

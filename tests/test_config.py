from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from kalshi_bot.config import Settings


def test_settings_use_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KALSHI_BOT_ENVIRONMENT", raising=False)
    monkeypatch.delenv("KALSHI_BOT_LOG_LEVEL", raising=False)

    settings = Settings()

    assert settings.environment == "development"
    assert settings.log_level == "INFO"


def test_settings_load_dotenv_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "KALSHI_BOT_ENVIRONMENT=production\nKALSHI_BOT_LOG_LEVEL=WARNING\n",
        encoding="utf_8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KALSHI_BOT_ENVIRONMENT", raising=False)
    monkeypatch.delenv("KALSHI_BOT_LOG_LEVEL", raising=False)

    settings = Settings()

    assert settings.environment == "production"
    assert settings.log_level == "WARNING"


def test_settings_reject_invalid_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "KALSHI_BOT_ENVIRONMENT=staging\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KALSHI_BOT_ENVIRONMENT", raising=False)

    with pytest.raises(ValidationError):
        Settings()


def test_settings_loads_kalshi_credentials_from_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    private_key_path = tmp_path / "kalshi-private-key.pem"

    monkeypatch.setenv("KALSHI_BOT_API_KEY_ID", "test-key-id")
    monkeypatch.setenv(
        "KALSHI_BOT_PRIVATE_KEY_PATH",
        str(private_key_path),
    )

    settings = Settings(_env_file=None)

    assert settings.api_key_id == "test-key-id"
    assert settings.private_key_path == private_key_path


def test_order_submission_is_disabled_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "KALSHI_BOT_ORDER_SUBMISSION_ENABLED",
        raising=False,
    )

    settings = Settings(_env_file=None)

    assert settings.order_submission_enabled is False


def test_order_submission_can_be_explicitly_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "KALSHI_BOT_ORDER_SUBMISSION_ENABLED",
        "true",
    )

    settings = Settings(_env_file=None)

    assert settings.order_submission_enabled is True


def test_order_cancellation_is_disabled_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "KALSHI_BOT_ORDER_CANCELLATION_ENABLED",
        raising=False,
    )

    settings = Settings(_env_file=None)

    assert settings.order_cancellation_enabled is False


def test_order_cancellation_can_be_enabled_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "KALSHI_BOT_ORDER_CANCELLATION_ENABLED",
        "true",
    )

    settings = Settings(_env_file=None)

    assert settings.order_cancellation_enabled is True


def test_demo_lifecycle_uses_bounded_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KALSHI_BOT_DEMO_MAX_CYCLES", raising=False)
    monkeypatch.delenv(
        "KALSHI_BOT_DEMO_POLL_INTERVAL_SECONDS",
        raising=False,
    )
    monkeypatch.delenv(
        "KALSHI_BOT_DEMO_MAX_OBSERVED_AGE_SECONDS",
        raising=False,
    )
    monkeypatch.delenv(
        "KALSHI_BOT_DEMO_MAX_MARKET_EXPOSURE_DOLLARS",
        raising=False,
    )
    monkeypatch.delenv(
        "KALSHI_BOT_DEMO_MIN_AVAILABLE_BALANCE_DOLLARS",
        raising=False,
    )
    monkeypatch.delenv(
        "KALSHI_BOT_DEMO_MAX_YES_SPREAD_DOLLARS",
        raising=False,
    )

    settings = Settings(_env_file=None)

    assert settings.demo_max_cycles == 1
    assert settings.demo_poll_interval_seconds == Decimal(0)
    assert settings.demo_max_observed_age_seconds == 30
    assert settings.demo_max_market_exposure_dollars == Decimal("5.00")
    assert settings.demo_min_available_balance_dollars == Decimal("10.00")
    assert settings.demo_max_yes_spread_dollars == Decimal("0.05")


def test_demo_lifecycle_rejects_non_positive_max_cycles() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            demo_max_cycles=0,
        )


def test_demo_lifecycle_rejects_negative_poll_interval() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            demo_poll_interval_seconds=Decimal("-0.01"),
        )


def test_demo_lifecycle_settings_load_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KALSHI_BOT_DEMO_MARKET_TICKER", "TEST-MARKET")
    monkeypatch.setenv("KALSHI_BOT_DEMO_QUOTE_QUANTITY", "1.50")
    monkeypatch.setenv("KALSHI_BOT_DEMO_MAX_CYCLES", "3")
    monkeypatch.setenv(
        "KALSHI_BOT_DEMO_POLL_INTERVAL_SECONDS",
        "2.50",
    )
    monkeypatch.setenv(
        "KALSHI_BOT_DEMO_MAX_YES_SPREAD_DOLLARS",
        "0.03",
    )

    settings = Settings(_env_file=None)

    assert settings.demo_market_ticker == "TEST-MARKET"
    assert settings.demo_quote_quantity == Decimal("1.50")
    assert settings.demo_max_cycles == 3
    assert settings.demo_poll_interval_seconds == Decimal("2.50")
    assert settings.demo_max_yes_spread_dollars == Decimal("0.03")


def test_demo_lifecycle_rejects_non_positive_quote_quantity() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            demo_quote_quantity=Decimal(0),
        )


def test_demo_market_scan_uses_bounded_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "KALSHI_BOT_DEMO_MARKET_SCAN_MAX_RESULTS",
        raising=False,
    )
    monkeypatch.delenv(
        "KALSHI_BOT_DEMO_MARKET_SCAN_MAX_PAGES",
        raising=False,
    )
    monkeypatch.delenv(
        "KALSHI_BOT_DEMO_MARKET_SCAN_PAGE_DELAY_SECONDS",
        raising=False,
    )
    monkeypatch.delenv(
        "KALSHI_BOT_DEMO_MARKET_SCAN_MAX_ORDERBOOK_CHECKS",
        raising=False,
    )

    settings = Settings(_env_file=None)

    assert settings.demo_market_scan_max_results == 10
    assert settings.demo_market_scan_max_pages == 10
    assert settings.demo_market_scan_page_delay_seconds == Decimal("0.25")
    assert settings.demo_market_scan_max_orderbook_checks == 10


def test_demo_market_scan_settings_load_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "KALSHI_BOT_DEMO_MARKET_SCAN_MAX_RESULTS",
        "5",
    )
    monkeypatch.setenv(
        "KALSHI_BOT_DEMO_MARKET_SCAN_MAX_PAGES",
        "3",
    )
    monkeypatch.setenv(
        "KALSHI_BOT_DEMO_MARKET_SCAN_PAGE_DELAY_SECONDS",
        "0.50",
    )
    monkeypatch.setenv(
        "KALSHI_BOT_DEMO_MARKET_SCAN_MAX_ORDERBOOK_CHECKS",
        "4",
    )

    settings = Settings(_env_file=None)

    assert settings.demo_market_scan_max_results == 5
    assert settings.demo_market_scan_max_pages == 3
    assert settings.demo_market_scan_page_delay_seconds == Decimal("0.50")
    assert settings.demo_market_scan_max_orderbook_checks == 4


@pytest.mark.parametrize(
    ("setting_name", "setting_value"),
    [
        ("demo_market_scan_max_results", 0),
        ("demo_market_scan_max_pages", 0),
        ("demo_market_scan_page_delay_seconds", Decimal("-0.01")),
        ("demo_market_scan_max_orderbook_checks", 0),
    ],
)
def test_demo_market_scan_rejects_invalid_limits(
    setting_name: str,
    setting_value: int | Decimal,
) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            **{setting_name: setting_value},
        )


def test_demo_lifecycle_rejects_non_positive_max_yes_spread() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            demo_max_yes_spread_dollars=Decimal(0),
        )


def test_demo_market_scan_excluded_categories_load_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "KALSHI_BOT_DEMO_MARKET_SCAN_EXCLUDED_CATEGORIES",
        raising=False,
    )

    default_settings = Settings(_env_file=None)

    monkeypatch.setenv(
        "KALSHI_BOT_DEMO_MARKET_SCAN_EXCLUDED_CATEGORIES",
        "Weather, Economics",
    )

    configured_settings = Settings(_env_file=None)

    assert default_settings.demo_market_scan_excluded_categories == (
        "sports,elections,entertainment"
    )
    assert configured_settings.demo_market_scan_excluded_categories == (
        "weather,economics"
    )


@pytest.mark.parametrize(
    "excluded_categories",
    [
        "",
        " , , ",
    ],
)
def test_demo_market_scan_rejects_empty_excluded_categories(
    excluded_categories: str,
) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            demo_market_scan_excluded_categories=excluded_categories,
        )

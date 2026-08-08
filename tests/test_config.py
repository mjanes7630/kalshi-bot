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

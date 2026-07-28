from pathlib import Path

import pytest
from pydantic import ValidationError

from kalshi_bot.config import Settings


def test_settings_use_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KALSHI_BOT_ENVIROMENT", raising=False)
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

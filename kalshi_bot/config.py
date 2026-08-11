from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="KALSHI_BOT_",
        extra="ignore",
    )

    environment: Literal["development", "production"] = "development"
    log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"

    api_key_id: str | None = None
    private_key_path: Path | None = None
    order_submission_enabled: bool = False
    order_cancellation_enabled: bool = False
    demo_order_ticker: str | None = None
    demo_order_count: Decimal | None = None
    demo_order_price: Decimal | None = None

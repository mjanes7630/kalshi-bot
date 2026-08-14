from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field
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
    demo_max_cycles: int = Field(default=1, gt=0)
    demo_poll_interval_seconds: Decimal = Field(default=Decimal(0), ge=0)
    demo_market_ticker: str | None = None
    demo_quote_quantity: Decimal | None = Field(default=None, gt=0)
    demo_max_observed_age_seconds: int = Field(default=30, gt=0)
    demo_max_market_exposure_dollars: Decimal = Field(default=Decimal("5.00"), gt=0)
    demo_min_available_balance_dollars: Decimal = Field(default=Decimal("10.00"), gt=0)

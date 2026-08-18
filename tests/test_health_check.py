import asyncio
from unittest.mock import Mock

import pytest

from kalshi_bot.config import Settings
from kalshi_bot.health_check import run_demo_market_health_check


def test_run_demo_market_health_check_requires_market_ticker() -> None:
    settings = Mock(spec=Settings)
    settings.demo_market_ticker = None

    with pytest.raises(
        ValueError,
        match="KALSHI_BOT_DEMO_MARKET_TICKER is required.",
    ):
        asyncio.run(run_demo_market_health_check(settings))
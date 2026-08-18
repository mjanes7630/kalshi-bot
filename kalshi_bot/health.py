import structlog
import httpx

from dataclasses import dataclass

from kalshi_bot.api.client import KalshiClient
from kalshi_bot.api.models import KalshiMarketStatus

logger = structlog.get_logger()


@dataclass(frozen=True)
class MarketHealth:
    ticker: str
    market_status: KalshiMarketStatus
    is_healthy: bool


async def check_market_health(
    *,
    client: KalshiClient,
    ticker: str,
) -> MarketHealth:
    market_response = await client.get_market(ticker)
    market = market_response.market

    return MarketHealth(
        ticker=ticker,
        market_status=market.status,
        is_healthy=market.status is KalshiMarketStatus.ACTIVE,
    )


async def run_market_health_check(
    *,
    client: KalshiClient,
    ticker: str,
) -> None:
    try:
        market_health = await check_market_health(
            client=client,
            ticker=ticker,
        )
    except httpx.HTTPError as error:
        logger.error(
            "market_health_check_failed",
            ticker=ticker,
            error=str(error),
            error_type=type(error).__name__,
        )
        raise

    log_health_result = (
        logger.info
        if market_health.is_healthy
        else logger.warning
    )
    log_health_result(
        "market_health_check_completed",
        ticker=ticker,
        market_status=market_health.market_status.value,
        is_healthy=market_health.is_healthy,
    )

    return market_health
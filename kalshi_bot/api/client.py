import httpx

from kalshi_bot.api.models import GetMarketsResponse

KALSHI_API_BASE_URL = "https://external-api.kalshi.com/trade-api/v2/"


class KalshiClient:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http_client = http_client

    async def get_markets(
        self,
        *,
        limit: int = 100,
        cursor: str | None = None,
    ) -> GetMarketsResponse:
        params: dict[str, int | str] = {"limit": limit}

        if cursor is not None:
            params["cursor"] = cursor

        response = await self._http_client.get(
            "markets",
            params=params,
        )
        response.raise_for_status()

        return GetMarketsResponse.model_validate(response.json())

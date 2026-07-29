from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class KalshiMarket(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticker: str
    title: str
    yes_bid_dollars: Decimal
    yes_ask_dollars: Decimal
    no_bid_dollars: Decimal
    no_ask_dollars: Decimal
    last_price_dollars: Decimal


class GetMarketsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    markets: list[KalshiMarket]
    cursor: str

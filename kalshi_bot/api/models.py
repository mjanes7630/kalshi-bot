from datetime import datetime
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


type OrderbookLevel = tuple[Decimal, Decimal]


class KalshiOrderbook(BaseModel):
    model_config = ConfigDict(extra="ignore")

    yes_dollars: list[OrderbookLevel]
    no_dollars: list[OrderbookLevel]


class GetMarketOrderbookResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    orderbook_fp: KalshiOrderbook


class KalshiTrade(BaseModel):
    model_config = ConfigDict(extra="ignore")

    trade_id: str
    ticker: str
    count_fp: Decimal
    yes_price_dollars: Decimal
    no_price_dollars: Decimal
    created_time: datetime
    is_block_trade: bool


class GetTradesResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    trades: list[KalshiTrade]
    cursor: str


class KalshiMarketPosition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticker: str
    total_traded_dollars: Decimal
    position_fp: Decimal
    market_exposure_dollars: Decimal
    realized_pnl_dollars: Decimal
    fees_paid_dollars: Decimal
    last_updated_ts: datetime


class KalshiEventPosition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_ticker: str
    total_cost_dollars: Decimal
    total_cost_shares_fp: Decimal
    event_exposure_dollars: Decimal
    realized_pnl_dollars: Decimal
    fees_paid_dollars: Decimal


class GetPositionsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    market_positions: list[KalshiMarketPosition]
    event_positions: list[KalshiEventPosition]
    cursor: str


class GetBalanceResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    balance: int
    balance_dollars: Decimal
    portfolio_value: int
    updated_ts: int

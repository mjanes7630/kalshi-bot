from datetime import datetime
from decimal import Decimal
from enum import StrEnum

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


class KalshiOrderSide(StrEnum):
    BID = "bid"
    ASK = "ask"


class KalshiTimeInForce(StrEnum):
    FILL_OR_KILL = "fill_or_kill"
    GOOD_TILL_CANCELED = "good_till_canceled"
    IMMEDIATE_OR_CANCEL = "immediate_or_cancel"


class KalshiSelfTradePreventionType(StrEnum):
    TAKER_AT_CROSS = "taker_at_cross"
    MAKER = "maker"


class CreateOrderRequest(BaseModel):
    ticker: str
    client_order_id: str
    side: KalshiOrderSide
    count: Decimal
    price: Decimal
    time_in_force: KalshiTimeInForce = KalshiTimeInForce.GOOD_TILL_CANCELED
    self_trade_prevention_type: KalshiSelfTradePreventionType = (
        KalshiSelfTradePreventionType.TAKER_AT_CROSS
    )
    post_only: bool = True
    cancel_order_on_pause: bool = True


class CreateOrderResponse(BaseModel):
    order_id: str
    client_order_id: str
    fill_count: Decimal
    remaining_count: Decimal
    ts_ms: int
    average_fill_price: Decimal | None = None
    average_fee_paid: Decimal | None = None


class CancelOrderResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    order_id: str
    client_order_id: str
    reduced_by: Decimal
    ts_ms: int

"""Broker abstraction layer — all broker implementations must inherit from BaseBroker."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchResult:
    symbol: str
    name: str
    sec_type: str
    exchange: str
    broker_ref: str
    currency: str = "USD"


@dataclass
class Position:
    symbol: str
    quantity: float
    market_value: float
    avg_cost: float
    unrealized_pnl: float
    currency: str = "USD"
    broker_ref: str = ""


@dataclass
class Quote:
    symbol: str
    last_price: float
    bid: float = 0.0
    ask: float = 0.0
    volume: int = 0
    timestamp: str = ""


@dataclass
class OrderRequest:
    symbol: str
    side: str
    quantity: int
    order_type: str = "LMT"
    price: Optional[float] = None
    sec_type: str = "STK"
    tif: str = "DAY"
    exchange: Optional[str] = None
    broker_ref: Optional[str] = None


@dataclass
class OrderResult:
    order_id: str
    status: str
    filled_qty: int = 0
    avg_price: float = 0.0
    raw: dict = field(default_factory=dict)


@dataclass
class AccountSummary:
    account_id: str
    net_value: float
    buying_power: float
    cash: float
    currency: str = "USD"
    raw: dict = field(default_factory=dict)


class BaseBroker(ABC):
    """Abstract base class for all broker implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def supported_markets(self) -> list[str]:
        ...

    @abstractmethod
    def auth_status(self) -> dict:
        ...

    @abstractmethod
    def list_accounts(self) -> list[dict]:
        ...

    @abstractmethod
    def portfolio_summary(self, account_id: str) -> AccountSummary:
        ...

    @abstractmethod
    def positions(self, account_id: str) -> list[Position]:
        ...

    @abstractmethod
    def search_symbol(self, query: str) -> list[SearchResult]:
        ...

    @abstractmethod
    def get_quote(self, symbols: list[str]) -> list[Quote]:
        ...

    @abstractmethod
    def order_status(self, account_id: str) -> list[dict]:
        ...

    @abstractmethod
    def place_order(self, account_id: str, order: OrderRequest) -> OrderResult:
        ...

    @abstractmethod
    def cancel_order(self, account_id: str, order_id: str) -> dict:
        ...

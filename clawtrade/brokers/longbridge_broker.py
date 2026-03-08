"""Longbridge broker — supports US, HK, and China A-shares via Stock Connect.
Ultra-low latency (~10ms). No gateway container needed.
Docs: https://open.longbridge.com/en/docs
"""
from brokers.base import (
    BaseBroker, OrderRequest, OrderResult, Position,
    Quote, SearchResult, AccountSummary,
)
from config import LONGBRIDGE_APP_KEY, LONGBRIDGE_APP_SECRET, LONGBRIDGE_ACCESS_TOKEN

_MARKET_SUFFIX = {"US": ".US", "HK": ".HK", "CN": ".SH", "SH": ".SH", "SZ": ".SZ"}


def _ensure_suffix(symbol: str) -> str:
    """Longbridge symbols use SYMBOL.MARKET format (e.g. AAPL.US, 700.HK)."""
    if "." in symbol:
        return symbol
    return f"{symbol}.US"


class LongbridgeBroker(BaseBroker):
    def __init__(self):
        from longport.openapi import Config, QuoteContext, TradeContext

        self._config = Config(
            app_key=LONGBRIDGE_APP_KEY,
            app_secret=LONGBRIDGE_APP_SECRET,
            access_token=LONGBRIDGE_ACCESS_TOKEN,
        )
        self._quote_ctx = QuoteContext(self._config)
        self._trade_ctx = TradeContext(self._config)

    @property
    def name(self) -> str:
        return "Longbridge"

    @property
    def supported_markets(self) -> list[str]:
        return ["US", "HK", "CN"]

    # ---- Read operations ----

    def auth_status(self) -> dict:
        try:
            balances = self._trade_ctx.account_balance()
            return {"authenticated": True, "accounts": len(balances)}
        except Exception as e:
            return {"authenticated": False, "error": str(e)}

    def list_accounts(self) -> list[dict]:
        balances = self._trade_ctx.account_balance()
        return [
            {"id": str(i), "currency": b.currency,
             "net_assets": str(b.net_assets)}
            for i, b in enumerate(balances)
        ]

    def portfolio_summary(self, account_id: str) -> AccountSummary:
        balances = self._trade_ctx.account_balance()
        if not balances:
            return AccountSummary(account_id=account_id, net_value=0,
                                 buying_power=0, cash=0)
        b = balances[0]
        return AccountSummary(
            account_id=account_id,
            net_value=float(b.net_assets),
            buying_power=float(b.max_finance_amount),
            cash=float(b.total_cash),
            currency=b.currency,
            raw={"net_assets": str(b.net_assets),
                 "total_cash": str(b.total_cash)},
        )

    def positions(self, account_id: str) -> list[Position]:
        resp = self._trade_ctx.stock_positions()
        results = []
        for channel in resp.channels:
            for p in channel.positions:
                results.append(Position(
                    symbol=p.symbol,
                    quantity=float(p.quantity),
                    market_value=float(getattr(p, "market_value", 0)),
                    avg_cost=float(p.cost_price),
                    unrealized_pnl=float(getattr(p, "unrealized_pnl", 0)),
                    currency=p.currency,
                    broker_ref=p.symbol,
                ))
        return results

    def search_symbol(self, query: str) -> list[SearchResult]:
        results = []
        for suffix, market in [(".US", "US"), (".HK", "HK")]:
            symbol = f"{query.upper()}{suffix}"
            try:
                quotes = self._quote_ctx.quote([symbol])
                if quotes:
                    q = quotes[0]
                    results.append(SearchResult(
                        symbol=symbol,
                        name=getattr(q, "symbol_name", ""),
                        sec_type="STK",
                        exchange=market,
                        broker_ref=symbol,
                        currency="USD" if market == "US" else "HKD",
                    ))
            except Exception:
                continue
        return results

    def get_quote(self, symbols: list[str]) -> list[Quote]:
        qualified = [_ensure_suffix(s) for s in symbols]
        data = self._quote_ctx.quote(qualified)
        return [
            Quote(
                symbol=q.symbol,
                last_price=float(q.last_done),
                bid=float(getattr(q, "bid", 0)),
                ask=float(getattr(q, "ask", 0)),
                volume=int(q.volume),
                timestamp=str(getattr(q, "timestamp", "")),
            )
            for q in data
        ]

    def order_status(self, account_id: str) -> list[dict]:
        try:
            orders = self._trade_ctx.today_orders()
        except Exception:
            orders = []
        return [
            {
                "order_id": o.order_id,
                "symbol": o.symbol,
                "side": str(o.side),
                "quantity": str(o.quantity),
                "status": str(o.status),
                "price": str(getattr(o, "price", "")),
            }
            for o in orders
        ]

    # ---- Write operations ----

    def place_order(self, account_id: str, order: OrderRequest) -> OrderResult:
        from longport.openapi import OrderSide, OrderType, TimeInForceType

        side = OrderSide.Buy if order.side.upper() == "BUY" else OrderSide.Sell
        order_type = OrderType.MO if order.order_type == "MKT" else OrderType.LO

        symbol = _ensure_suffix(order.symbol)
        price = order.price if order.price else 0

        resp = self._trade_ctx.submit_order(
            symbol=symbol,
            order_type=order_type,
            side=side,
            submitted_quantity=order.quantity,
            submitted_price=price,
            time_in_force=TimeInForceType.Day,
        )
        return OrderResult(
            order_id=resp.order_id,
            status="submitted",
            raw={"order_id": resp.order_id},
        )

    def cancel_order(self, account_id: str, order_id: str) -> dict:
        self._trade_ctx.cancel_order(order_id)
        return {"status": "cancelled", "order_id": order_id}

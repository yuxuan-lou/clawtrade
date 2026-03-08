"""Alpaca broker — pure REST API, no gateway container needed.
Supports US equities. Free paper trading available.
Docs: https://docs.alpaca.markets/
"""
import requests
from brokers.base import (
    BaseBroker, OrderRequest, OrderResult, Position,
    Quote, SearchResult, AccountSummary,
)
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL, ALPACA_DATA_URL


class AlpacaBroker(BaseBroker):
    def __init__(self):
        self._base = ALPACA_BASE_URL
        self._data = ALPACA_DATA_URL
        self._headers = {
            "APCA-API-KEY-ID": ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
        }
        self._timeout = 15

    @property
    def name(self) -> str:
        return "Alpaca"

    @property
    def supported_markets(self) -> list[str]:
        return ["US"]

    def _get(self, path: str, params: dict = None, base: str = None):
        r = requests.get(f"{base or self._base}{path}", params=params,
                         headers=self._headers, timeout=self._timeout)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict = None):
        r = requests.post(f"{self._base}{path}", json=data,
                          headers=self._headers, timeout=self._timeout)
        r.raise_for_status()
        return r.json()

    def _delete(self, path: str):
        r = requests.delete(f"{self._base}{path}", headers=self._headers,
                            timeout=self._timeout)
        r.raise_for_status()
        return r.json() if r.content else {}

    # ---- Read operations ----

    def auth_status(self) -> dict:
        try:
            acct = self._get("/v2/account")
            return {
                "authenticated": acct.get("status") == "ACTIVE",
                "status": acct.get("status", "UNKNOWN"),
                "account_id": acct.get("id", ""),
            }
        except requests.RequestException as e:
            return {"authenticated": False, "error": str(e)}

    def list_accounts(self) -> list[dict]:
        acct = self._get("/v2/account")
        return [{"id": acct["id"],
                 "account_number": acct.get("account_number", "")}]

    def portfolio_summary(self, account_id: str) -> AccountSummary:
        d = self._get("/v2/account")
        return AccountSummary(
            account_id=d.get("id", account_id),
            net_value=float(d.get("equity", 0)),
            buying_power=float(d.get("buying_power", 0)),
            cash=float(d.get("cash", 0)),
            currency="USD",
            raw=d,
        )

    def positions(self, account_id: str) -> list[Position]:
        data = self._get("/v2/positions")
        return [
            Position(
                symbol=p["symbol"],
                quantity=float(p.get("qty", 0)),
                market_value=float(p.get("market_value", 0)),
                avg_cost=float(p.get("avg_entry_price", 0)),
                unrealized_pnl=float(p.get("unrealized_pl", 0)),
                currency="USD",
                broker_ref=p.get("asset_id", ""),
            )
            for p in data
        ]

    def search_symbol(self, query: str) -> list[SearchResult]:
        try:
            d = self._get(f"/v2/assets/{query.upper()}")
            return [SearchResult(
                symbol=d["symbol"], name=d.get("name", ""),
                sec_type="STK", exchange=d.get("exchange", ""),
                broker_ref=d["symbol"], currency="USD",
            )]
        except requests.HTTPError:
            data = self._get("/v2/assets", params={
                "status": "active", "asset_class": "us_equity",
            })
            hits = [a for a in data
                    if query.upper() in a.get("symbol", "").upper()
                    or query.lower() in a.get("name", "").lower()][:20]
            return [
                SearchResult(
                    symbol=a["symbol"], name=a.get("name", ""),
                    sec_type="STK", exchange=a.get("exchange", ""),
                    broker_ref=a["symbol"], currency="USD",
                )
                for a in hits
            ]

    def get_quote(self, symbols: list[str]) -> list[Quote]:
        quotes = []
        for sym in symbols:
            try:
                snap = self._get(f"/v2/stocks/{sym}/snapshot",
                                 base=self._data)
                trade = snap.get("latestTrade", snap.get("latest_trade", {}))
                qt = snap.get("latestQuote", snap.get("latest_quote", {}))
                quotes.append(Quote(
                    symbol=sym,
                    last_price=float(trade.get("p", 0)),
                    bid=float(qt.get("bp", 0)),
                    ask=float(qt.get("ap", 0)),
                    volume=int(snap.get("dailyBar", snap.get("daily_bar", {}))
                               .get("v", 0)),
                ))
            except Exception:
                quotes.append(Quote(symbol=sym, last_price=0))
        return quotes

    def order_status(self, account_id: str) -> list[dict]:
        return self._get("/v2/orders", params={"status": "open"})

    # ---- Write operations ----

    def place_order(self, account_id: str, order: OrderRequest) -> OrderResult:
        body = {
            "symbol": order.symbol.upper(),
            "qty": str(order.quantity),
            "side": order.side.lower(),
            "type": "market" if order.order_type == "MKT" else "limit",
            "time_in_force": order.tif.lower() if order.tif else "day",
        }
        if order.order_type != "MKT" and order.price is not None:
            body["limit_price"] = str(order.price)

        result = self._post("/v2/orders", data=body)
        return OrderResult(
            order_id=result.get("id", ""),
            status=result.get("status", "new"),
            raw=result,
        )

    def cancel_order(self, account_id: str, order_id: str) -> dict:
        self._delete(f"/v2/orders/{order_id}")
        return {"status": "cancelled", "order_id": order_id}

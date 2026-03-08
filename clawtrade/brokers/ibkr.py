"""IBKR broker — connects to Client Portal Gateway running in a sibling container."""
import requests
import urllib3
from brokers.base import (
    BaseBroker, OrderRequest, OrderResult, Position,
    Quote, SearchResult, AccountSummary,
)
from config import IBKR_GATEWAY_URL, IBKR_VERIFY_SSL

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class IBKRBroker(BaseBroker):
    def __init__(self):
        self._base = IBKR_GATEWAY_URL
        self._verify = IBKR_VERIFY_SSL
        self._timeout = 15

    @property
    def name(self) -> str:
        return "Interactive Brokers"

    @property
    def supported_markets(self) -> list[str]:
        return ["US", "HK", "EU", "APAC"]

    def _get(self, path: str, params: dict = None):
        r = requests.get(f"{self._base}{path}", params=params,
                         verify=self._verify, timeout=self._timeout)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict = None):
        r = requests.post(f"{self._base}{path}", json=data,
                          verify=self._verify, timeout=self._timeout)
        r.raise_for_status()
        return r.json()

    # ---- Read operations ----

    def auth_status(self) -> dict:
        return self._get("/v1/api/iserver/auth/status")

    def list_accounts(self) -> list[dict]:
        result = self._get("/v1/api/portfolio/accounts")
        return result if isinstance(result, list) else [result]

    def portfolio_summary(self, account_id: str) -> AccountSummary:
        data = self._get(f"/v1/api/portfolio/{account_id}/summary")
        return AccountSummary(
            account_id=account_id,
            net_value=data.get("netLiquidation", {}).get("amount", 0),
            buying_power=data.get("buyingPower", {}).get("amount", 0),
            cash=data.get("totalCashValue", {}).get("amount", 0),
            currency=data.get("netLiquidation", {}).get("currency", "USD"),
            raw=data,
        )

    def positions(self, account_id: str) -> list[Position]:
        data = self._get(f"/v1/api/portfolio/{account_id}/positions/0")
        if not isinstance(data, list):
            return []
        return [
            Position(
                symbol=p.get("contractDesc", p.get("ticker", "")),
                quantity=p.get("position", 0),
                market_value=p.get("mktValue", 0),
                avg_cost=p.get("avgCost", 0),
                unrealized_pnl=p.get("unrealizedPnl", 0),
                currency=p.get("currency", "USD"),
                broker_ref=str(p.get("conid", "")),
            )
            for p in data
        ]

    def search_symbol(self, query: str) -> list[SearchResult]:
        data = self._get("/v1/api/iserver/secdef/search",
                         params={"symbol": query})
        if not isinstance(data, list):
            return []
        results = []
        for item in data:
            sections = item.get("sections", [])
            exchange = sections[0].get("exchange", "") if sections else ""
            results.append(SearchResult(
                symbol=item.get("symbol", ""),
                name=item.get("companyName", item.get("description", "")),
                sec_type=item.get("secType", "STK"),
                exchange=exchange,
                broker_ref=str(item.get("conid", "")),
                currency=item.get("currency", "USD"),
            ))
        return results

    def get_quote(self, symbols: list[str]) -> list[Quote]:
        conids = ",".join(symbols)
        data = self._get("/v1/api/iserver/marketdata/snapshot",
                         params={"conids": conids, "fields": "31,84,86"})
        if not isinstance(data, list):
            return []
        return [
            Quote(
                symbol=str(item.get("conid", "")),
                last_price=float(item.get("31", 0) or 0),
                bid=float(item.get("84", 0) or 0),
                ask=float(item.get("86", 0) or 0),
            )
            for item in data
        ]

    def order_status(self, account_id: str) -> list[dict]:
        data = self._get(f"/v1/api/iserver/account/{account_id}/orders")
        if isinstance(data, list):
            return data
        return [data] if data else []

    # ---- Write operations ----

    def place_order(self, account_id: str, order: OrderRequest) -> OrderResult:
        conid = order.broker_ref
        if not conid:
            results = self.search_symbol(order.symbol)
            if not results:
                raise ValueError(f"Symbol '{order.symbol}' not found on IBKR")
            conid = results[0].broker_ref

        order_data = {
            "conid": int(conid),
            "side": order.side.upper(),
            "quantity": order.quantity,
            "orderType": order.order_type,
            "tif": order.tif,
        }
        if order.price is not None:
            order_data["price"] = order.price

        result = self._post(
            f"/v1/api/iserver/account/{account_id}/orders",
            data={"orders": [order_data]},
        )

        order_id = ""
        status = "submitted"
        if isinstance(result, list) and result:
            order_id = str(result[0].get("order_id", ""))
            status = result[0].get("order_status", "submitted")
        elif isinstance(result, dict):
            order_id = str(result.get("order_id", ""))
            status = result.get("order_status", "submitted")

        return OrderResult(order_id=order_id, status=status,
                           raw=result if isinstance(result, dict) else {"items": result})

    def cancel_order(self, account_id: str, order_id: str) -> dict:
        r = requests.delete(
            f"{self._base}/v1/api/iserver/account/{account_id}/order/{order_id}",
            verify=self._verify, timeout=self._timeout,
        )
        r.raise_for_status()
        return r.json()

    def tickle(self) -> dict:
        return self._post("/v1/api/tickle")

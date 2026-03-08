"""Tiger Brokers — supports US, HK, China A-shares (Stock Connect), and SG.
Docs: https://quant.itigerup.com/openapi/en/python/overview/introduction.html
"""
from brokers.base import (
    BaseBroker, OrderRequest, OrderResult, Position,
    Quote, SearchResult, AccountSummary,
)
from config import TIGER_ID, TIGER_ACCOUNT, TIGER_PRIVATE_KEY


class TigerBrokerClient(BaseBroker):
    def __init__(self):
        from tigeropen.common.consts import Language
        from tigeropen.tiger_open_config import TigerOpenClientConfig
        from tigeropen.trade.trade_client import TradeClient
        from tigeropen.quote.quote_client import QuoteClient

        cfg = TigerOpenClientConfig(sandbox_debug=False)
        cfg.tiger_id = TIGER_ID
        cfg.account = TIGER_ACCOUNT
        cfg.private_key = TIGER_PRIVATE_KEY
        cfg.language = Language.en_US

        self._trade = TradeClient(cfg)
        self._quote = QuoteClient(cfg)
        self._account = TIGER_ACCOUNT

    @property
    def name(self) -> str:
        return "Tiger Brokers"

    @property
    def supported_markets(self) -> list[str]:
        return ["US", "HK", "CN", "SG"]

    # ---- Read operations ----

    def auth_status(self) -> dict:
        try:
            self._trade.get_assets()
            return {"authenticated": True, "account": self._account}
        except Exception as e:
            return {"authenticated": False, "error": str(e)}

    def list_accounts(self) -> list[dict]:
        try:
            managed = self._trade.get_managed_accounts()
            accounts = managed if managed else [self._account]
        except Exception:
            accounts = [self._account]
        return [{"id": acc, "account": acc} for acc in accounts]

    def portfolio_summary(self, account_id: str) -> AccountSummary:
        assets = self._trade.get_assets()
        if not assets:
            return AccountSummary(account_id=account_id, net_value=0,
                                 buying_power=0, cash=0)
        a = assets[0] if isinstance(assets, list) else assets
        return AccountSummary(
            account_id=account_id,
            net_value=float(getattr(a, "net_liquidation", 0) or 0),
            buying_power=float(getattr(a, "buying_power", 0) or 0),
            cash=float(getattr(a, "cash", 0) or 0),
            currency=getattr(a, "currency", "USD"),
            raw={"segment": getattr(a, "segment", "")},
        )

    def positions(self, account_id: str) -> list[Position]:
        data = self._trade.get_positions(account=account_id)
        if not data:
            return []
        return [
            Position(
                symbol=p.contract.symbol,
                quantity=float(p.quantity),
                market_value=float(getattr(p, "market_value", 0) or 0),
                avg_cost=float(getattr(p, "average_cost", 0) or 0),
                unrealized_pnl=float(getattr(p, "unrealized_pnl", 0) or 0),
                currency=getattr(p.contract, "currency", "USD"),
                broker_ref=p.contract.symbol,
            )
            for p in data
        ]

    def search_symbol(self, query: str) -> list[SearchResult]:
        results = []
        try:
            briefs = self._quote.get_stock_briefs([query.upper()])
            for b in (briefs or []):
                results.append(SearchResult(
                    symbol=b.symbol,
                    name=getattr(b, "name", ""),
                    sec_type="STK",
                    exchange=getattr(b, "market", "US"),
                    broker_ref=b.symbol,
                ))
        except Exception:
            pass

        if not results:
            from tigeropen.common.consts import Market
            for market, label in [(Market.US, "US"), (Market.HK, "HK"),
                                  (Market.CN, "CN")]:
                try:
                    syms = self._quote.get_symbols(market=market) or []
                    hits = [s for s in syms
                            if query.upper() in s.upper()][:5]
                    for s in hits:
                        results.append(SearchResult(
                            symbol=s, name="", sec_type="STK",
                            exchange=label, broker_ref=s,
                        ))
                except Exception:
                    continue
        return results

    def get_quote(self, symbols: list[str]) -> list[Quote]:
        briefs = self._quote.get_stock_briefs(symbols) or []
        return [
            Quote(
                symbol=b.symbol,
                last_price=float(getattr(b, "latest_price", 0) or 0),
                bid=float(getattr(b, "bid_price", 0) or 0),
                ask=float(getattr(b, "ask_price", 0) or 0),
                volume=int(getattr(b, "volume", 0) or 0),
            )
            for b in briefs
        ]

    def order_status(self, account_id: str) -> list[dict]:
        orders = self._trade.get_orders(account=account_id) or []
        return [
            {
                "order_id": str(o.order_id),
                "symbol": o.contract.symbol,
                "side": o.action,
                "quantity": str(o.quantity),
                "status": o.status,
                "price": str(getattr(o, "limit_price", "")),
            }
            for o in orders
        ]

    # ---- Write operations ----

    def place_order(self, account_id: str, order: OrderRequest) -> OrderResult:
        from tigeropen.common.util.order_utils import market_order, limit_order

        action = "BUY" if order.side.upper() == "BUY" else "SELL"

        if order.order_type == "MKT":
            tiger_order = market_order(
                account=account_id,
                symbol=order.symbol.upper(),
                action=action,
                quantity=order.quantity,
            )
        else:
            tiger_order = limit_order(
                account=account_id,
                symbol=order.symbol.upper(),
                action=action,
                quantity=order.quantity,
                limit_price=order.price or 0,
            )

        self._trade.place_order(tiger_order)
        oid = str(getattr(tiger_order, "order_id", "")
                  or getattr(tiger_order, "id", ""))
        return OrderResult(
            order_id=oid,
            status="submitted",
            raw={"order_id": oid},
        )

    def cancel_order(self, account_id: str, order_id: str) -> dict:
        self._trade.cancel_order(order_id=int(order_id))
        return {"status": "cancelled", "order_id": order_id}

"""
ClawTrade main service.
Provides guardrail-protected REST API for AI agent consumption.
Broker-agnostic: works with IBKR, Alpaca, Longbridge, and Tiger Brokers.
"""
import sys
from dataclasses import asdict
from functools import wraps

from flask import Flask, request, jsonify

import config
from brokers import create_broker
from brokers.base import OrderRequest
import guardrails
import confirmation
import audit

app = Flask(__name__)

CLAWTRADE_SECRET = config.CLAWTRADE_SECRET

_broker = None


def get_broker():
    global _broker
    if _broker is None:
        _broker = create_broker(config.BROKER_TYPE)
    return _broker


# ---- Auth middleware ----
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = (request.headers.get("X-ClawTrade-Token", "")
                 or request.headers.get("X-Bridge-Token", ""))
        if not CLAWTRADE_SECRET or token != CLAWTRADE_SECRET:
            audit.log_action("unauthorized_access", {
                "path": request.path,
                "method": request.method,
            }, {}, blocked=True, reason="Invalid API key")
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# ============================================================
# Read-only endpoints
# ============================================================

@app.route("/api/status", methods=["GET"])
@require_auth
def get_status():
    try:
        result = get_broker().auth_status()
        result["broker"] = get_broker().name
        audit.log_action("auth_status", {}, result)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/accounts", methods=["GET"])
@require_auth
def get_accounts():
    try:
        result = get_broker().list_accounts()
        audit.log_action("list_accounts", {}, {"count": len(result)})
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/portfolio/<account_id>", methods=["GET"])
@require_auth
def get_portfolio(account_id):
    try:
        result = get_broker().portfolio_summary(account_id)
        audit.log_action("portfolio_summary",
                         {"account_id": account_id}, {"ok": True})
        return jsonify(asdict(result))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/positions/<account_id>", methods=["GET"])
@require_auth
def get_positions(account_id):
    try:
        result = get_broker().positions(account_id)
        audit.log_action("positions",
                         {"account_id": account_id},
                         {"count": len(result)})
        return jsonify([asdict(p) for p in result])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/search", methods=["GET"])
@require_auth
def search():
    symbol = request.args.get("symbol", "")
    if not symbol:
        return jsonify({"error": "Missing 'symbol' parameter"}), 400
    try:
        result = get_broker().search_symbol(symbol)
        audit.log_action("search_symbol", {"symbol": symbol},
                         {"count": len(result)})
        return jsonify([asdict(r) for r in result])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/quote", methods=["GET"])
@require_auth
def quote():
    symbols = request.args.get("symbols", request.args.get("conids", ""))
    if not symbols:
        return jsonify({"error": "Missing 'symbols' parameter"}), 400
    try:
        symbol_list = [s.strip() for s in symbols.split(",")]
        result = get_broker().get_quote(symbol_list)
        audit.log_action("market_data", {"symbols": symbols}, {"ok": True})
        return jsonify([asdict(q) for q in result])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/orders/<account_id>", methods=["GET"])
@require_auth
def get_orders(account_id):
    try:
        result = get_broker().order_status(account_id)
        audit.log_action("order_status",
                         {"account_id": account_id}, {"ok": True})
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# Write endpoints (guardrail-protected)
# ============================================================

@app.route("/api/order/<account_id>", methods=["POST"])
@require_auth
def place_order(account_id):
    """
    Place order — goes through full guardrail checks.
    Request body:
    {
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": 10,
        "order_type": "LMT",
        "price": 150.00,
        "sec_type": "STK",
        "estimated_price": 150.00,
        "tif": "DAY",
        "broker_ref": ""       (optional, broker-specific ID)
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    params = {
        "account_id": account_id,
        "order": {
            "symbol": data.get("symbol", ""),
            "side": data.get("side", "").upper(),
            "quantity": data.get("quantity", 0),
            "orderType": data.get("order_type", "LMT"),
            "price": data.get("price"),
            "secType": data.get("sec_type", "STK"),
            "tif": data.get("tif", "DAY"),
        },
        "estimated_price": data.get("estimated_price", 0),
    }

    # ---- Guardrail checks ----
    try:
        check = guardrails.run_all_checks("place_order", params)
    except guardrails.GuardrailViolation as e:
        audit.log_action("place_order", params, {},
                         blocked=True, reason=str(e))
        return jsonify({
            "blocked": True,
            "rule": e.rule,
            "detail": e.detail,
        }), 403

    # ---- Needs human confirmation? ----
    if check["needs_confirm"]:
        confirm_params = {"account_id": account_id, "order_data": data}
        item = confirmation.create_confirmation(
            "place_order", confirm_params,
            f"Order value ${check['order_value']:,.2f} "
            f"exceeds confirmation threshold "
            f"${config.CONFIRM_THRESHOLD_USD:,}"
        )
        audit.log_action("place_order", params,
                         {"awaiting_confirmation": item["id"]},
                         reason="Awaiting human confirmation")
        return jsonify({
            "status": "awaiting_confirmation",
            "confirm_id": item["id"],
            "detail": item["detail"],
            "message": (
                f"Reply 'confirm {item['id']}' to execute this order, "
                f"or 'reject {item['id']}' to cancel"
            ),
        }), 202

    # ---- Execute directly ----
    order_req = OrderRequest(
        symbol=data.get("symbol", ""),
        side=data.get("side", "").upper(),
        quantity=data.get("quantity", 0),
        order_type=data.get("order_type", "LMT"),
        price=data.get("price"),
        sec_type=data.get("sec_type", "STK"),
        tif=data.get("tif", "DAY"),
        broker_ref=data.get("broker_ref", ""),
    )
    try:
        result = get_broker().place_order(account_id, order_req)
        audit.log_action("place_order", params, asdict(result))
        return jsonify({
            "status": "executed",
            "result": {"order_id": result.order_id, "status": result.status},
        })
    except Exception as e:
        audit.log_action("place_order", params,
                         {"error": str(e)}, blocked=True,
                         reason="Execution failed")
        return jsonify({"error": str(e)}), 500


@app.route("/api/confirm/<confirm_id>", methods=["POST"])
@require_auth
def confirm_order(confirm_id):
    body = request.get_json() or {}
    action_type = body.get("action", "confirm")

    if action_type == "reject":
        item = confirmation.reject(confirm_id)
        if "error" in item:
            return jsonify(item), 404
        audit.log_action("reject_confirmation",
                         {"confirm_id": confirm_id}, item)
        return jsonify({"status": "rejected", "detail": "Operation cancelled"})

    item = confirmation.confirm(confirm_id)
    if "error" in item:
        return jsonify(item), 404

    saved = item["params"]
    data = saved["order_data"]
    account_id = saved["account_id"]

    order_req = OrderRequest(
        symbol=data.get("symbol", ""),
        side=data.get("side", "").upper(),
        quantity=data.get("quantity", 0),
        order_type=data.get("order_type", "LMT"),
        price=data.get("price"),
        sec_type=data.get("sec_type", "STK"),
        tif=data.get("tif", "DAY"),
        broker_ref=data.get("broker_ref", ""),
    )
    try:
        result = get_broker().place_order(account_id, order_req)
        audit.log_action("place_order_confirmed",
                         saved, asdict(result))
        return jsonify({
            "status": "executed",
            "result": {"order_id": result.order_id, "status": result.status},
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cancel_order/<account_id>/<order_id>",
           methods=["DELETE"])
@require_auth
def cancel_order(account_id, order_id):
    try:
        result = get_broker().cancel_order(account_id, order_id)
        audit.log_action("cancel_order",
                         {"account_id": account_id,
                          "order_id": order_id}, result)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# Admin endpoints
# ============================================================

@app.route("/api/pending", methods=["GET"])
@require_auth
def get_pending():
    confirmation.cleanup_expired()
    return jsonify(confirmation.get_pending())


@app.route("/api/guardrails", methods=["GET"])
@require_auth
def get_guardrails():
    """View current guardrail configuration (read-only)."""
    return jsonify({
        "broker": get_broker().name,
        "supported_markets": get_broker().supported_markets,
        "max_order_value_usd": config.MAX_ORDER_VALUE_USD,
        "max_order_quantity": config.MAX_ORDER_QUANTITY,
        "max_daily_trades": config.MAX_DAILY_TRADES,
        "confirm_threshold_usd": config.CONFIRM_THRESHOLD_USD,
        "allowed_sec_types": config.ALLOWED_SEC_TYPES,
        "forbidden_ops": config.FORBIDDEN_OPS,
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "clawtrade",
        "broker": config.BROKER_TYPE,
    })


# ---- Startup ----
if __name__ == "__main__":
    if not CLAWTRADE_SECRET:
        print("Error: CLAWTRADE_SECRET is not set")
        sys.exit(1)

    broker = get_broker()
    print(f"ClawTrade listening on {config.CLAWTRADE_HOST}:{config.CLAWTRADE_PORT}")
    print(f"Broker: {broker.name} | Markets: {broker.supported_markets}")
    print(f"Guardrails: max_order=${config.MAX_ORDER_VALUE_USD:,} | "
          f"confirm_threshold=${config.CONFIRM_THRESHOLD_USD:,} | "
          f"daily_limit={config.MAX_DAILY_TRADES}")

    app.run(
        host=config.CLAWTRADE_HOST,
        port=config.CLAWTRADE_PORT,
        debug=False,
    )

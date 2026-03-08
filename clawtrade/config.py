"""
ClawTrade security configuration.
All guardrail parameters are defined here and cannot be modified by AI agents.
"""
import os

# ============================================================
# Broker selection
# ============================================================
BROKER_TYPE = os.environ.get("BROKER_TYPE", "ibkr")

# ============================================================
# IBKR settings (requires ibkr-gateway container)
# ============================================================
IBKR_GATEWAY_URL = os.environ.get("IBKR_GATEWAY_URL", "https://ibkr-gateway:5000")
IBKR_VERIFY_SSL = False

# ============================================================
# Alpaca settings (pure REST, no gateway needed)
# ============================================================
ALPACA_API_KEY = os.environ.get("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL = os.environ.get(
    "ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
ALPACA_DATA_URL = os.environ.get(
    "ALPACA_DATA_URL", "https://data.alpaca.markets")

# ============================================================
# Longbridge settings (US, HK, China A-shares via Stock Connect)
# ============================================================
LONGBRIDGE_APP_KEY = os.environ.get("LONGBRIDGE_APP_KEY", "")
LONGBRIDGE_APP_SECRET = os.environ.get("LONGBRIDGE_APP_SECRET", "")
LONGBRIDGE_ACCESS_TOKEN = os.environ.get("LONGBRIDGE_ACCESS_TOKEN", "")

# ============================================================
# Tiger Brokers settings (US, HK, China A-shares, SG)
# ============================================================
TIGER_ID = os.environ.get("TIGER_ID", "")
TIGER_ACCOUNT = os.environ.get("TIGER_ACCOUNT", "")
TIGER_PRIVATE_KEY = os.environ.get("TIGER_PRIVATE_KEY", "")

# ============================================================
# ClawTrade service
# ============================================================
CLAWTRADE_HOST = "0.0.0.0"
CLAWTRADE_PORT = 5100

# ============================================================
# Trading guardrails — hardcoded, not modifiable by AI
# ============================================================

ALLOWED_READ_OPS = [
    "auth_status",
    "list_accounts",
    "portfolio_summary",
    "positions",
    "market_data",
    "search_symbol",
    "order_status",
]

ALLOWED_WRITE_OPS = [
    "place_order",
    "cancel_order",
]

FORBIDDEN_OPS = [
    "close_all_positions",
    "cancel_all_orders",
    "transfer_funds",
    "modify_account",
]

MAX_ORDER_VALUE_USD = 5000
MAX_ORDER_QUANTITY = 100
MAX_DAILY_TRADES = 20
MAX_CONCENTRATION_PCT = 25
CONFIRM_THRESHOLD_USD = 1000
CONFIRM_TIMEOUT_SEC = 300
ALLOWED_SEC_TYPES = ["STK"]

AUDIT_LOG_PATH = "/app/logs/clawtrade_audit.jsonl"

"""
ClawTrade security configuration.
All guardrail parameters are defined here and cannot be modified by AI agents.
"""
import os


def _read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def _get_secret(name: str, default: str = "") -> str:
    file_path = os.environ.get(f"{name}_FILE", "").strip()
    if file_path:
        value = _read_file(file_path)
        if value:
            return value
    return os.environ.get(name, default)

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
ALPACA_API_KEY = _get_secret("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = _get_secret("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL = os.environ.get(
    "ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
ALPACA_DATA_URL = os.environ.get(
    "ALPACA_DATA_URL", "https://data.alpaca.markets")

# ============================================================
# Longbridge settings (US, HK, China A-shares via Stock Connect)
# ============================================================
LONGBRIDGE_APP_KEY = _get_secret("LONGBRIDGE_APP_KEY", "")
LONGBRIDGE_APP_SECRET = _get_secret("LONGBRIDGE_APP_SECRET", "")
LONGBRIDGE_ACCESS_TOKEN = _get_secret("LONGBRIDGE_ACCESS_TOKEN", "")

# ============================================================
# Tiger Brokers settings (US, HK, China A-shares, SG)
# ============================================================
TIGER_ID = _get_secret("TIGER_ID", "")
TIGER_ACCOUNT = os.environ.get("TIGER_ACCOUNT", "")
TIGER_PRIVATE_KEY = _get_secret("TIGER_PRIVATE_KEY", "")

# ============================================================
# ClawTrade service
# ============================================================
CLAWTRADE_HOST = "0.0.0.0"
CLAWTRADE_PORT = 5100
CLAWTRADE_SECRET = _get_secret("CLAWTRADE_SECRET", "")

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

"""
Security guardrails — checks every write operation before execution.
All rules are hardcoded in this file, running inside a Docker container.
The AI agent on the host cannot read or modify these rules.
"""
import json
import os
from datetime import date
from config import (
    MAX_ORDER_VALUE_USD, MAX_ORDER_QUANTITY, MAX_DAILY_TRADES,
    CONFIRM_THRESHOLD_USD, ALLOWED_SEC_TYPES, FORBIDDEN_OPS,
    AUDIT_LOG_PATH,
)


class GuardrailViolation(Exception):
    def __init__(self, rule: str, detail: str):
        self.rule = rule
        self.detail = detail
        super().__init__(f"[{rule}] {detail}")


def check_forbidden(action: str):
    if action in FORBIDDEN_OPS:
        raise GuardrailViolation(
            "FORBIDDEN_OP",
            f"Operation '{action}' is permanently forbidden. "
            f"Please execute it manually through your broker client."
        )


def check_order_value(quantity: int, estimated_price: float):
    value = quantity * estimated_price
    if value > MAX_ORDER_VALUE_USD:
        raise GuardrailViolation(
            "MAX_ORDER_VALUE",
            f"Order value ${value:,.2f} exceeds the limit of "
            f"${MAX_ORDER_VALUE_USD:,}"
        )
    return value


def check_order_quantity(quantity: int):
    if quantity > MAX_ORDER_QUANTITY:
        raise GuardrailViolation(
            "MAX_ORDER_QUANTITY",
            f"Order quantity {quantity} exceeds the limit of "
            f"{MAX_ORDER_QUANTITY}"
        )


def check_daily_trade_count():
    today = date.today().isoformat()
    count = 0
    if os.path.exists(AUDIT_LOG_PATH):
        with open(AUDIT_LOG_PATH, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                if (entry.get("action") == "place_order"
                        and not entry.get("blocked")
                        and entry["timestamp"].startswith(today)):
                    count += 1
    if count >= MAX_DAILY_TRADES:
        raise GuardrailViolation(
            "MAX_DAILY_TRADES",
            f"Already executed {count} trades today, "
            f"reaching the limit of {MAX_DAILY_TRADES}"
        )
    return count


def check_sec_type(sec_type: str):
    if sec_type not in ALLOWED_SEC_TYPES:
        raise GuardrailViolation(
            "DISALLOWED_SEC_TYPE",
            f"Security type '{sec_type}' is not in the allowed list: "
            f"{ALLOWED_SEC_TYPES}"
        )


def needs_confirmation(order_value: float) -> bool:
    return order_value >= CONFIRM_THRESHOLD_USD


def run_all_checks(action: str, params: dict) -> dict:
    """Run all guardrail checks."""
    check_forbidden(action)

    if action == "place_order":
        order = params.get("order", {})
        quantity = order.get("quantity", 0)
        est_price = params.get("estimated_price", 0)
        sec_type = order.get("secType", "STK")

        check_sec_type(sec_type)
        check_order_quantity(quantity)
        order_value = check_order_value(quantity, est_price)
        check_daily_trade_count()

        return {
            "passed": True,
            "needs_confirm": needs_confirmation(order_value),
            "order_value": order_value,
            "detail": "All guardrail checks passed",
        }

    return {"passed": True, "needs_confirm": False, "detail": "OK"}

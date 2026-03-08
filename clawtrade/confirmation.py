"""Human confirmation queue — pauses operations above the threshold until
the user confirms via chat."""
import uuid
import threading
from datetime import datetime, timezone
from config import CONFIRM_TIMEOUT_SEC

_pending = {}
_lock = threading.Lock()


def create_confirmation(action: str, params: dict, detail: str) -> dict:
    confirm_id = str(uuid.uuid4())[:8]
    item = {
        "id": confirm_id,
        "action": action,
        "params": params,
        "detail": detail,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }
    with _lock:
        _pending[confirm_id] = item
    return item


def confirm(confirm_id: str) -> dict:
    with _lock:
        if confirm_id not in _pending:
            return {"error": f"Confirmation ID '{confirm_id}' does not exist or has expired"}
        item = _pending[confirm_id]
        if item["status"] != "pending":
            return {"error": f"This operation has already been {item['status']}"}
        item["status"] = "confirmed"
        return item


def reject(confirm_id: str) -> dict:
    with _lock:
        if confirm_id not in _pending:
            return {"error": f"Confirmation ID '{confirm_id}' does not exist"}
        item = _pending[confirm_id]
        item["status"] = "rejected"
        return item


def get_pending() -> list:
    with _lock:
        return [v for v in _pending.values() if v["status"] == "pending"]


def cleanup_expired():
    now = datetime.now(timezone.utc)
    with _lock:
        for v in _pending.values():
            created = datetime.fromisoformat(v["created_at"])
            if ((now - created).total_seconds() > CONFIRM_TIMEOUT_SEC
                    and v["status"] == "pending"):
                v["status"] = "expired"

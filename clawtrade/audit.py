"""Audit log — records every operation; cannot be modified externally."""
import json
import os
from datetime import datetime, timezone


def log_action(action: str, params: dict, result: dict,
               blocked: bool = False, reason: str = ""):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "params": _sanitize(params),
        "result": _sanitize(result),
        "blocked": blocked,
        "reason": reason,
    }

    from config import AUDIT_LOG_PATH
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)

    with open(AUDIT_LOG_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def _sanitize(obj, max_depth=3):
    """Truncate overly long fields to prevent log bloat."""
    if max_depth <= 0:
        return "..."
    if isinstance(obj, dict):
        return {k: _sanitize(v, max_depth - 1) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v, max_depth - 1) for v in obj[:20]]
    if isinstance(obj, str) and len(obj) > 500:
        return obj[:500] + "...(truncated)"
    return obj

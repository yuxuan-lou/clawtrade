"""IBKR Gateway keepalive — pings every 5 minutes."""
import time
import requests
import urllib3
urllib3.disable_warnings()

while True:
    try:
        requests.post("https://localhost:5000/v1/api/tickle",
                       verify=False, timeout=10)
        status = requests.get(
            "https://localhost:5000/v1/api/iserver/auth/status",
            verify=False, timeout=10,
        ).json()
        auth = status.get("authenticated", False)
        if not auth:
            print("[keepalive] ⚠️  Session expired — re-authentication needed")
        else:
            print("[keepalive] ✓ Session active")
    except Exception as e:
        print(f"[keepalive] Error: {e}")
    time.sleep(300)

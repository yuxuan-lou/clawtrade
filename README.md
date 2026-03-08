# ClawTrade

> Secure multi-broker trading middleware for AI agents
>
> [中文文档](README.zh-CN.md)

---

## What is ClawTrade?

ClawTrade is a standalone security middleware that allows AI agents (such as [OpenClaw](https://openclaw.ai)) to safely operate your brokerage account. It is an **independent microservice** that exposes trading functionality through a controlled HTTP API and enforces hardcoded safety guardrails on every operation.

A lightweight OpenClaw Skill file is included to bridge OpenClaw with ClawTrade.

### Why Not Just an OpenClaw Trade Skill?

A regular OpenClaw Skill runs **inside the same process** as the AI agent — meaning the agent has full access to your broker credentials, can modify safety rules on the fly, and can execute any operation without restriction. If the agent hallucinates or is prompt-injected, nothing stands in the way.

ClawTrade takes a fundamentally different approach:

| | OpenClaw Skill (direct) | ClawTrade |
|---|---|---|
| Credential access | Agent can read API keys from env/memory | Credentials live only inside a Docker container the agent cannot access |
| Safety rules | Agent can modify or ignore them | Hardcoded in a separate process; changes require a container rebuild |
| Operation scope | Unrestricted — agent can call any broker API | Allowlist-only; forbidden operations (close-all, transfer funds) are permanently blocked |
| Large trades | Execute immediately | Paused for human confirmation above threshold |
| Audit trail | Optional, agent-controlled | Mandatory, tamper-resistant (container-internal log) |
| Broker support | One Skill per broker | Single API across IBKR, Alpaca, Longbridge, Tiger |

**In short:** ClawTrade treats your AI agent as an untrusted client. It gives the agent enough capability to be useful, while making it structurally impossible to cause catastrophic damage — even if the agent is compromised.

### Supported Brokers

| Broker | Markets | Auth Method | Gateway Required |
|--------|---------|-------------|-----------------|
| **Interactive Brokers** | US, HK, EU, APAC | Username/Password + 2FA | Yes (Java container) |
| **Alpaca** | US | API Key/Secret | No |
| **Longbridge** | US, HK, China A-shares | App Key/Secret + Token | No |
| **Tiger Brokers** | US, HK, China A-shares, SG | Tiger ID + RSA Key | No |

### Core Security Principles

- **Your AI agent never touches the broker directly** — all operations are filtered through ClawTrade
- **Guardrails are hardcoded** — the AI cannot modify value limits, rate limits, or other rules
- **ClawTrade runs inside a Docker container** — even if your AI agent runs as root, it cannot read broker credentials or modify configuration inside the container
- **Large operations require human confirmation** — trades above the threshold are paused until you confirm in chat

### Architecture

```
You (WhatsApp / Telegram / WebChat)
        │
        ▼
┌───────────────────────────┐
│  OpenClaw Gateway         │  Runs on the host
│  + ClawTrade Skill        │
└────────────┬──────────────┘
             │  HTTP → localhost:5100
             ▼
┌──────────────────────────────────────────────────┐
│  Docker                                          │
│  ┌──────────────────────┐  ┌───────────────────┐ │
│  │  ClawTrade           │  │  IBKR Gateway     │ │
│  │  (Python/Flask)      │←→│  (IBKR only)      │ │
│  │  Port 5100           │  │  Port 5000        │ │
│  │                      │  │  (container only) │ │
│  │  • Broker adapter    │  └───────────────────┘ │
│  │  • Guardrails        │                        │
│  │  • Confirmation      │  Alpaca / Longbridge   │
│  │    queue             │  / Tiger: direct API   │
│  │  • Audit log         │  (no gateway needed)   │
│  └──────────────────────┘                        │
└──────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/yuxuan-lou/clawtrade.git
cd clawtrade
```

### 2. Run the installer

```bash
./install.sh
```

If ClawTrade is already running and you only want to configure OpenClaw Skill:

```bash
./install.sh --openclaw-only
```

The script will:
1. Ask you to **choose a broker** (IBKR, Alpaca, Longbridge, or Tiger)
2. Collect broker-specific credentials
3. Generate a ClawTrade API key
4. Build Docker images and start services
5. (Optional) Auto-install the OpenClaw Skill and update `~/.openclaw/openclaw.json`

> **IBKR users:** You must confirm the push notification on your IBKR Key mobile app within 2 minutes on first launch.

### 3. Verify deployment

```bash
# Health check (no key required)
curl http://localhost:5100/api/health
# Expected: {"status":"ok","service":"clawtrade","broker":"ibkr"}

# Auth check (key required)
CT_SECRET=$(grep CLAWTRADE_SECRET .env | cut -d= -f2)
curl -H "X-ClawTrade-Token: $CT_SECRET" http://localhost:5100/api/status
```

### 4. Configure OpenClaw Skill

`install.sh` now prompts to configure OpenClaw automatically. If you choose **Yes**, it will:

- Copy `openclaw-skill/SKILL.md` to `~/.openclaw/skills/clawtrade/SKILL.md`
- Backup your existing `~/.openclaw/openclaw.json` (if present)
- Set `skills.entries.clawtrade.enabled=true`
- Set `skills.entries.clawtrade.env.CLAWTRADE_SECRET` to your generated key
- Inject `CLAWTRADE_SECRET` into gateway runtime environment on restart (compatibility fallback)
- Attempt to restart OpenClaw gateway

Note: For most setups, skill-specific env (`skills.entries.clawtrade.env`) is sufficient. The installer also injects gateway runtime env as a compatibility fallback for environments that still require it.

If you choose **No** (or auto-setup fails), use the manual steps below:

```bash
mkdir -p ~/.openclaw/skills/clawtrade
cp openclaw-skill/SKILL.md ~/.openclaw/skills/clawtrade/
```

Add the entry to `~/.openclaw/openclaw.json`:

```json
{
  "skills": {
    "entries": {
      "clawtrade": {
        "enabled": true,
        "env": {
          "CLAWTRADE_SECRET": "YOUR_KEY_HERE"
        }
      }
    }
  }
}
```

Then restart OpenClaw:

```bash
openclaw gateway restart
```

---

## Default Guardrails (Paper Trading)

| Parameter | Default |
|-----------|---------|
| Max order value | $5,000 |
| Max shares per order | 100 |
| Max daily trades | 20 |
| Human confirmation threshold | $1,000 |
| Allowed security types | STK (stocks) |

To modify guardrails, edit `clawtrade/config.py` and rebuild:

```bash
docker compose up -d --build clawtrade
```

---

## API Reference

All endpoints (except `/api/health`) require the header:

```
X-ClawTrade-Token: YOUR_CLAWTRADE_SECRET
```

### Read Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check (no auth) |
| `/api/status` | GET | Broker connection status |
| `/api/accounts` | GET | List accounts |
| `/api/portfolio/{account_id}` | GET | Portfolio summary |
| `/api/positions/{account_id}` | GET | Current positions |
| `/api/search?symbol=AAPL` | GET | Search for a symbol |
| `/api/quote?symbols=AAPL,MSFT` | GET | Market data snapshot |
| `/api/orders/{account_id}` | GET | Open orders |
| `/api/guardrails` | GET | Current guardrail config |
| `/api/pending` | GET | Pending confirmations |

### Write Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/order/{account_id}` | POST | Place order (guardrail-checked) |
| `/api/confirm/{confirm_id}` | POST | Confirm or reject a pending order |
| `/api/cancel_order/{account_id}/{order_id}` | DELETE | Cancel an order |

### Order Request Body

```json
{
  "symbol": "AAPL",
  "side": "BUY",
  "quantity": 10,
  "order_type": "LMT",
  "price": 150.00,
  "sec_type": "STK",
  "estimated_price": 150.00,
  "tif": "DAY"
}
```

The API is **broker-agnostic** — the same request format works across all supported brokers. ClawTrade handles the translation to each broker's native API.

---

## Daily Operations

```bash
# Start services
docker compose up -d                          # non-IBKR brokers
docker compose --profile ibkr up -d           # IBKR (includes gateway)

# Stop services
docker compose down

# View logs
docker compose logs -f clawtrade

# Re-authenticate IBKR (confirm on mobile)
docker compose exec ibkr-gateway python3 -m ibeam.ibeam_starter --authenticate

# View audit log
docker compose exec clawtrade cat /app/logs/clawtrade_audit.jsonl
```

---

## Switching Brokers

1. Stop services: `docker compose down`
2. Re-run `./install.sh` and select a different broker
3. Update the `CLAWTRADE_SECRET` in `~/.openclaw/openclaw.json` if it changed

---

## Switching to Live Trading

1. Update `.env` with your live broker credentials
2. Lower the guardrails in `clawtrade/config.py`:

```python
MAX_ORDER_VALUE_USD = 1000
MAX_ORDER_QUANTITY = 20
MAX_DAILY_TRADES = 5
CONFIRM_THRESHOLD_USD = 200
```

3. Rebuild: `docker compose up -d --build`
4. Start with small manual trades, monitor the audit log

---

## FAQ

**Q: Will ClawTrade affect my existing OpenClaw configuration?**
No. You only need to add one entry to `openclaw.json` under `skills.entries`. No other configuration changes are needed, and it won't affect your other Skills.

**Q: I have other trading-related Skills installed. What should I do?**
It's recommended to disable other Skills that connect directly to your broker (e.g., an ibkr-trader Skill from ClawHub), to avoid bypassing ClawTrade's safety layer. But this is not mandatory — ClawTrade's security does not depend on it.

**Q: IBKR Gateway authentication expired. What do I do?**
Run `docker compose exec ibkr-gateway python3 -m ibeam.ibeam_starter --authenticate`, then confirm the push notification on your IBKR Key app. The keepalive script extends sessions, but re-authentication is typically needed every ~24 hours.

**Q: How do I view all historical operations?**
Run `docker compose exec clawtrade cat /app/logs/clawtrade_audit.jsonl`. Each line is a JSON object with timestamp, action, parameters, result, and whether it was blocked.

**Q: How do I enable options trading?**
Edit `clawtrade/config.py` and add `"OPT"` to the `ALLOWED_SEC_TYPES` list, then rebuild with `docker compose up -d --build clawtrade`. Consider lowering value limits when enabling options.

**Q: My ClawTrade API key was leaked. What do I do?**
1. `docker compose down`
2. Generate a new key: `openssl rand -hex 32`
3. Update the key in both `.env` and `~/.openclaw/openclaw.json`
4. `docker compose up -d`

**Q: Which brokers support China A-share trading?**
Longbridge and Tiger Brokers both support China A-shares through the Stock Connect mechanism. IBKR also provides access to some Hong Kong and Shanghai-listed securities.

**Q: Can I add a new broker that's not supported yet?**
Yes. Create a new file in `clawtrade/brokers/` that implements the `BaseBroker` interface (see `clawtrade/brokers/base.py`), register it in `clawtrade/brokers/__init__.py`, and add the required configuration to `clawtrade/config.py`. Pull requests are welcome.

---

## Project Structure

```
clawtrade/
├── README.md                   ← You are here
├── README.zh-CN.md             ← 中文文档
├── LICENSE
├── install.sh                  ← Interactive setup (broker selection)
├── docker-compose.yml          ← Container orchestration (profiles)
├── .gitignore
│
├── clawtrade/                  ← Core middleware
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                  ← Flask REST API
│   ├── config.py               ← Guardrails + broker config
│   ├── guardrails.py           ← Safety checks
│   ├── confirmation.py         ← Human confirmation queue
│   ├── audit.py                ← JSONL audit logger
│   └── brokers/                ← Broker abstraction layer
│       ├── base.py             ← BaseBroker interface
│       ├── __init__.py         ← Broker factory
│       ├── ibkr.py             ← Interactive Brokers
│       ├── alpaca_broker.py    ← Alpaca
│       ├── longbridge_broker.py← Longbridge
│       └── tiger_broker.py     ← Tiger Brokers
│
├── gateways/                   ← Broker-specific gateway containers
│   └── ibkr/                   ← IBKR Client Portal Gateway + IBeam
│       ├── Dockerfile
│       ├── start.sh
│       └── keepalive.py
│
└── openclaw-skill/             ← OpenClaw integration
    └── SKILL.md
```

---

## License

MIT

---

## About the Author

Built by [Yuxuan Lou](https://yuxuanlou.info) — visit for more projects and writing.

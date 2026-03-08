---
name: clawtrade
description: >
  Operate your brokerage account through a secure isolation layer (ClawTrade).
  Supports IBKR, Alpaca, Longbridge, and Tiger Brokers.
  Covers US, HK, and China A-share markets.
  Use this Skill when the user mentions stocks, trading, portfolio,
  positions, orders, buy, sell, IBKR, Alpaca, Longbridge, or Tiger.
metadata:
  openclaw:
    requires:
      env: ["CLAWTRADE_SECRET"]
    primaryEnv: "CLAWTRADE_SECRET"
---

# ClawTrade

Operate your brokerage account through a secure middleware. All operations are guardrail-protected.

## Supported Brokers

| Broker | Markets |
|--------|---------|
| Interactive Brokers (IBKR) | US, HK, EU, APAC |
| Alpaca | US |
| Longbridge | US, HK, China A-shares |
| Tiger Brokers | US, HK, China A-shares, SG |

## Security Rules (must follow)

1. All trading operations must go through ClawTrade (localhost:5100) — never access broker APIs directly
2. All requests must include header: `X-ClawTrade-Token: $CLAWTRADE_SECRET`
3. When receiving `awaiting_confirmation`, show details and wait for the user to confirm or reject
4. When receiving `blocked`, explain the reason to the user — do not retry or attempt to bypass
5. Never attempt to modify ClawTrade configuration or Docker containers

## API Reference

Common header (all requests):
```
X-ClawTrade-Token: $CLAWTRADE_SECRET
```

Base URL: `http://localhost:5100`

### Query Operations

| Operation | Method | Path |
|-----------|--------|------|
| Connection status | GET | /api/status |
| List accounts | GET | /api/accounts |
| Portfolio summary | GET | /api/portfolio/{account_id} |
| Current positions | GET | /api/positions/{account_id} |
| Search symbol | GET | /api/search?symbol=AAPL |
| Get quote | GET | /api/quote?symbols=AAPL,MSFT |
| Current orders | GET | /api/orders/{account_id} |
| Guardrail config | GET | /api/guardrails |
| Pending confirmations | GET | /api/pending |

### Place Order (guardrail-protected)

POST /api/order/{account_id}

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

**Before placing an order**:
1. GET /api/search?symbol=XXX to look up the symbol
2. GET /api/quote?symbols=XXX to get the current price for estimated_price

**Response handling**:
- `"status": "executed"` — inform the user the order has been executed
- `"status": "awaiting_confirmation"` — show order details and confirmation ID, wait for user reply
- `"blocked": true` — explain the blocking reason, do not retry

### Confirm / Reject

POST /api/confirm/{confirm_id}

```json
{"action": "confirm"}
```
or
```json
{"action": "reject"}
```

### Cancel Order

DELETE /api/cancel_order/{account_id}/{order_id}

## Interaction Guidelines

1. User asks about portfolio/positions — call the corresponding GET endpoint
2. User asks to trade — search for the symbol, fetch current price, then place order
3. User says "confirm xxx" — call the confirm endpoint
4. User says "reject xxx" — call the reject endpoint
5. Always inform the user clearly about the current status and guardrail limits

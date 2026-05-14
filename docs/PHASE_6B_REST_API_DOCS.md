# Phase 6B REST API Documentation

**Document Type**: API Reference Documentation  
**Status**: ✅ COMPLETE  
**Updated**: May 14, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URL & Endpoints](#base-url--endpoints)
4. [Endpoint Details](#endpoint-details)
5. [Error Handling](#error-handling)
6. [Examples](#examples)
7. [WebSocket](#websocket)
8. [Rate Limiting](#rate-limiting)

---

## Overview

The **Paper Trading REST API** provides full control over the paper trading engine, allowing:

- **Lifecycle Management**: Start/stop trading engine
- **Signal Injection**: Send trading signals from external models  
- **Real-Time Monitoring**: Get live portfolio and performance data
- **Configuration Updates**: Dynamically adjust risk parameters
- **Trade History**: Access detailed trade records with pagination
- **Risk Reporting**: Comprehensive risk metrics and violation tracking
- **WebSocket Updates**: Real-time portfolio and trade notifications

**Base URL**: `http://localhost:8000`  
**Documentation**: `http://localhost:8000/docs` (Swagger UI)

---

## Authentication

Currently **NOT REQUIRED** for development. In production, add JWT:

```python
# Add to src/api/app.py for production:
from fastapi.security import HTTPBearer, HTTPAuthCredential
import jwt

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthCredential):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

Add to endpoints:
```python
@app.post("/paper-trading/start")
async def start_paper_trading(
    request: PaperTradingStartRequest,
    token: HTTPAuthCredential = Depends(security)
):
    # Verify token first
    await verify_token(token)
    # ... rest of endpoint
```

---

## Base URL & Endpoints

All endpoints are under `/paper-trading/`:

```
POST   /paper-trading/start          Initialize engine
GET    /paper-trading/status         Current status
GET    /paper-trading/performance    Performance metrics
POST   /paper-trading/stop           Stop engine
GET    /paper-trading/trades         Trade history
GET    /paper-trading/portfolio      Portfolio snapshot
GET    /paper-trading/risk-report    Risk analysis
POST   /paper-trading/signal         Inject signal
POST   /paper-trading/config         Update config
POST   /paper-trading/reset-daily    Reset daily counters
WS     /paper-trading/ws             WebSocket updates
```

---

## Endpoint Details

### 1. START ENGINE

**Endpoint**: `POST /paper-trading/start`

**Purpose**: Initialize and start the paper trading engine with specified capital and risk parameters.

**Request**:
```json
{
  "initial_capital": 100000.0,
  "kelly_fraction": 0.25,
  "max_position_pct": 0.10,
  "max_daily_loss_pct": 0.02,
  "max_drawdown_pct": 0.15,
  "min_confidence": 0.60
}
```

**Response (200)**:
```json
{
  "status": "success",
  "message": "Paper trading engine started",
  "config": {
    "initial_capital": 100000.0,
    "kelly_fraction": 0.25,
    "max_position_pct": 0.10,
    "max_daily_loss_pct": 0.02,
    "max_drawdown_pct": 0.15,
    "min_confidence": 0.60
  },
  "details": {
    "status": "RUNNING",
    "started_at": "2026-05-14T20:29:06.897Z"
  }
}
```

**Error Responses**:
- `409 Conflict`: Engine already running
- `500 Server Error`: Initialization failed

**Parameters**:
| Name | Type | Range | Default | Description |
|------|------|-------|---------|-------------|
| initial_capital | float | > 0 | 100000 | Starting capital in USD |
| kelly_fraction | float | 0.05-1.0 | 0.25 | Kelly criterion fraction |
| max_position_pct | float | 0.01-0.50 | 0.10 | Max position as % of capital |
| max_daily_loss_pct | float | 0.005-0.10 | 0.02 | Max daily loss % |
| max_drawdown_pct | float | 0.05-0.50 | 0.15 | Max drawdown % |
| min_confidence | float | 0.0-1.0 | 0.60 | Min signal confidence to trade |

---

### 2. GET STATUS

**Endpoint**: `GET /paper-trading/status`

**Purpose**: Get current engine status including portfolio state, trading activity, and per-model signals.

**Response (200)**:
```json
{
  "status": "RUNNING",
  "started_at": "2026-05-14T20:29:06.897Z",
  "current_time": "2026-05-14T20:29:15.234Z",
  "uptime_seconds": 8.337,
  "portfolio": {
    "total_value": 100000.0,
    "cash": 100000.0,
    "position_value": 0.0,
    "daily_pnl": 0.0,
    "total_pnl": 0.0
  },
  "trading": {
    "open_positions": 0,
    "daily_trades": 0,
    "total_trades": 0,
    "consecutive_losses": 0
  },
  "models": {
    "wavelet": {"signals": 0, "last_signal": null},
    "hmm": {"signals": 0, "last_signal": null},
    "lstm": {"signals": 0, "last_signal": null},
    "tft": {"signals": 0, "last_signal": null},
    "genetic": {"signals": 0, "last_signal": null},
    "ensemble": {"signals": 0, "last_signal": null}
  }
}
```

**Error Responses**:
- `404 Not Found`: Engine not initialized

---

### 3. GET PERFORMANCE

**Endpoint**: `GET /paper-trading/performance`

**Purpose**: Get real-time performance metrics including P&L, Sharpe ratio, drawdown, and win rate.

**Response (200)**:
```json
{
  "total_value": 100000.0,
  "cash": 100000.0,
  "position_quantity": 0.0,
  "position_value": 0.0,
  "pnl_total": 0.0,
  "pnl_realized": 0.0,
  "pnl_unrealized": 0.0,
  "pnl_daily": 0.0,
  "return_pct": 0.0,
  "sharpe_ratio": 0.0,
  "max_drawdown": 0.0,
  "win_rate": 0.0,
  "num_trades": 0,
  "daily_trades": 0
}
```

**Metrics**:
- `total_value`: Current portfolio value in USD
- `pnl_total`: Total profit/loss across all trades
- `sharpe_ratio`: Risk-adjusted return metric (higher is better)
- `max_drawdown`: Largest decline from peak (lower is better)
- `win_rate`: % of profitable trades (0-1)
- `return_pct`: Return as % of initial capital

---

### 4. GET PORTFOLIO

**Endpoint**: `GET /paper-trading/portfolio`

**Purpose**: Get complete portfolio snapshot with mark-to-market valuation at current price.

**Response (200)**:
```json
{
  "timestamp": "2026-05-14T20:29:15.234Z",
  "total_value": 100000.0,
  "cash": 100000.0,
  "position_quantity": 0.0,
  "position_value": 0.0,
  "pnl_total": 0.0,
  "daily_pnl": 0.0,
  "return_pct": 0.0,
  "sharpe_ratio": 0.0,
  "max_drawdown": 0.0,
  "win_rate": 0.0,
  "num_trades": 0
}
```

---

### 5. GET TRADES

**Endpoint**: `GET /paper-trading/trades`

**Purpose**: Get trade history with pagination and optional filtering.

**Query Parameters**:
| Name | Type | Default | Description |
|------|------|---------|-------------|
| limit | int | 50 | Number of trades to return (1-500) |
| offset | int | 0 | Number of trades to skip |
| status_filter | str | null | Filter by status: OPEN, CLOSED, ALL |

**Response (200)**:
```json
[
  {
    "trade_id": "trade_001_ensemble_1",
    "model_name": "ensemble",
    "signal_type": "LONG",
    "entry_price": 2045.50,
    "exit_price": null,
    "quantity": 5.0,
    "entry_time": "2026-05-14T10:30:00.000Z",
    "exit_time": null,
    "pnl": 0.0,
    "pnl_pct": 0.0,
    "status": "OPEN",
    "regime": "GROWTH",
    "confidence": 0.85
  }
]
```

---

### 6. GET RISK REPORT

**Endpoint**: `GET /paper-trading/risk-report`

**Purpose**: Get comprehensive risk metrics, limits, and violation tracking.

**Response (200)**:
```json
{
  "status": "success",
  "timestamp": "2026-05-14T20:29:15.234Z",
  "risk_report": {
    "position_limits": {
      "max_position_pct": 0.10,
      "current_position_pct": 0.0,
      "violation": false
    },
    "daily_loss_limit": {
      "daily_loss_pct": 0.02,
      "current_daily_loss_pct": 0.0,
      "violation": false
    },
    "drawdown_limit": {
      "max_drawdown_pct": 0.15,
      "current_drawdown_pct": 0.0,
      "violation": false
    },
    "model_concentration": {
      "max_model_concentration": 0.50,
      "current_concentrations": {},
      "violation": false
    },
    "consecutive_losses": {
      "max_consecutive_losses": 3,
      "current_consecutive_losses": 0,
      "violation": false
    }
  },
  "portfolio_summary": {
    "total_value": 100000.0,
    "return_pct": 0.0,
    "max_drawdown": 0.0
  }
}
```

---

### 7. INJECT SIGNAL

**Endpoint**: `POST /paper-trading/signal`

**Purpose**: Inject a trading signal to be evaluated and executed by the engine.

**Request**:
```json
{
  "model_name": "ensemble",
  "signal_type": "LONG",
  "confidence": 0.85,
  "price": 2045.50,
  "regime": "GROWTH",
  "reasoning": "Strong uptrend across multiple indicators"
}
```

**Response (200)**:
```json
{
  "status": "success",
  "signal_processed": true,
  "model": "ensemble",
  "signal_type": "LONG",
  "confidence": 0.85,
  "trade_executed": true,
  "trade": {
    "trade_id": "trade_001_ensemble_1",
    "signal_type": "LONG",
    "entry_price": 2045.50,
    "quantity": 4.88,
    "status": "OPEN"
  }
}
```

**Parameters**:
| Name | Type | Valid Values | Description |
|------|------|--------------|-------------|
| model_name | str | wavelet, hmm, lstm, tft, genetic, ensemble | Source model |
| signal_type | str | LONG, SHORT, CLOSE, HOLD | Trade direction |
| confidence | float | 0.0-1.0 | Signal confidence level |
| price | float | > 0 | Current gold price |
| regime | str | GROWTH, NORMAL, CRISIS | Market regime |
| reasoning | str | Any string | Optional explanation |

**Error Responses**:
- `400 Bad Request`: Invalid model or signal type
- `404 Not Found`: Engine not initialized
- `409 Conflict`: Engine not running

---

### 8. UPDATE CONFIG

**Endpoint**: `POST /paper-trading/config`

**Purpose**: Dynamically update engine configuration without restarting.

**Request** (update any subset):
```json
{
  "kelly_fraction": 0.30,
  "max_position_pct": 0.12,
  "max_daily_loss_pct": 0.03,
  "max_drawdown_pct": 0.20,
  "min_confidence": 0.65,
  "trading_enabled": true
}
```

**Response (200)**:
```json
{
  "status": "success",
  "message": "Configuration updated",
  "updated_fields": {
    "kelly_fraction": 0.30,
    "max_position_pct": 0.12,
    "max_daily_loss_pct": 0.03
  }
}
```

---

### 9. RESET DAILY

**Endpoint**: `POST /paper-trading/reset-daily`

**Purpose**: Reset daily P&L counters and trade limits for new trading day.

**Response (200)**:
```json
{
  "status": "success",
  "message": "Daily counters reset",
  "previous_daily_pnl": 0.0,
  "reset_time": "2026-05-14T20:29:15.234Z"
}
```

---

### 10. STOP ENGINE

**Endpoint**: `POST /paper-trading/stop`

**Purpose**: Stop engine and close all open positions.

**Response (200)**:
```json
{
  "status": "success",
  "message": "Paper trading stopped",
  "details": {
    "total_pnl": 0.0,
    "total_trades": 0,
    "winning_trades": 0,
    "win_rate": 0.0,
    "max_drawdown": 0.0,
    "sharpe_ratio": 0.0,
    "stopped_at": "2026-05-14T20:29:15.234Z"
  }
}
```

---

## Error Handling

### Error Response Format

All errors follow this format:

```json
{
  "detail": "Human-readable error message"
}
```

### Common HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid input validation |
| 404 | Not Found | Engine not initialized |
| 409 | Conflict | Engine already running or invalid state |
| 422 | Unprocessable Entity | Schema validation failed |
| 500 | Server Error | Internal error during processing |

### Error Examples

**Not Initialized** (404):
```json
{"detail": "Paper trading engine not initialized. Call POST /paper-trading/start first."}
```

**Already Running** (409):
```json
{"detail": "Paper trading is already running. Stop it first."}
```

**Invalid Signal Type** (400):
```json
{"detail": "Invalid signal_type. Must be one of: LONG, SHORT, CLOSE, HOLD"}
```

---

## Examples

### Python Synchronous

```python
import requests

client = requests.Session()
base = "http://localhost:8000/paper-trading"

# Start
r = client.post(f"{base}/start", json={
    "initial_capital": 100000,
    "kelly_fraction": 0.25,
    "max_position_pct": 0.10,
    "max_daily_loss_pct": 0.02,
    "max_drawdown_pct": 0.15,
    "min_confidence": 0.60
})
print(r.json())

# Get status
r = client.get(f"{base}/status")
print(r.json())

# Inject signal
r = client.post(f"{base}/signal", json={
    "model_name": "ensemble",
    "signal_type": "LONG",
    "confidence": 0.85,
    "price": 2045.50
})
print(r.json())

# Stop
r = client.post(f"{base}/stop")
print(r.json())
```

### cURL

```bash
# Start engine
curl -X POST http://localhost:8000/paper-trading/start \
  -H "Content-Type: application/json" \
  -d '{
    "initial_capital": 100000,
    "kelly_fraction": 0.25,
    "max_position_pct": 0.10,
    "max_daily_loss_pct": 0.02,
    "max_drawdown_pct": 0.15,
    "min_confidence": 0.60
  }'

# Get status
curl http://localhost:8000/paper-trading/status

# Inject signal
curl -X POST http://localhost:8000/paper-trading/signal \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "ensemble",
    "signal_type": "LONG",
    "confidence": 0.85,
    "price": 2045.50
  }'

# Stop
curl -X POST http://localhost:8000/paper-trading/stop
```

### JavaScript

```javascript
const BASE_URL = "http://localhost:8000/paper-trading";

async function startEngine() {
  const response = await fetch(`${BASE_URL}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      initial_capital: 100000,
      kelly_fraction: 0.25,
      max_position_pct: 0.10,
      max_daily_loss_pct: 0.02,
      max_drawdown_pct: 0.15,
      min_confidence: 0.60
    })
  });
  return await response.json();
}

async function getStatus() {
  const response = await fetch(`${BASE_URL}/status`);
  return await response.json();
}

async function injectSignal(modelName, signalType, confidence, price) {
  const response = await fetch(`${BASE_URL}/signal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model_name: modelName,
      signal_type: signalType,
      confidence: confidence,
      price: price
    })
  });
  return await response.json();
}

// Usage
(async () => {
  console.log("Starting engine...");
  const start = await startEngine();
  console.log(start);
  
  console.log("Getting status...");
  const status = await getStatus();
  console.log(status);
  
  console.log("Injecting signal...");
  const signal = await injectSignal("ensemble", "LONG", 0.85, 2045.50);
  console.log(signal);
})();
```

---

## WebSocket

**Endpoint**: `WS /paper-trading/ws`

**Purpose**: Real-time portfolio and trade updates via WebSocket.

**Connection**:
```python
import websocket
import json

ws = websocket.create_connection("ws://localhost:8000/paper-trading/ws")

# Receive initial status
msg = ws.recv()
print(json.loads(msg))

# Keep connection alive with pings
ws.send(json.dumps({"type": "ping"}))

# Request updates
ws.send(json.dumps({"type": "get_status"}))

# Listen for updates
msg = ws.recv()
print(json.loads(msg))
```

**Message Types**:

1. **Connection** (server → client):
```json
{
  "event": "connected",
  "data": { ... engine status ... },
  "timestamp": "2026-05-14T20:29:06.897Z"
}
```

2. **Portfolio Update** (server → client):
```json
{
  "event": "portfolio_update",
  "data": {
    "total_value": 100000.0,
    "cash": 100000.0,
    "pnl_total": 0.0,
    "daily_pnl": 0.0,
    "return_pct": 0.0,
    "num_trades": 0
  },
  "timestamp": "2026-05-14T20:29:15.234Z"
}
```

3. **Trade Executed** (server → client):
```json
{
  "event": "trade_executed",
  "data": {
    "trade_id": "trade_001_ensemble_1",
    "signal_type": "LONG",
    "entry_price": 2045.50,
    "quantity": 4.88,
    "status": "OPEN"
  },
  "timestamp": "2026-05-14T20:29:15.234Z"
}
```

4. **Engine Stopped** (server → client):
```json
{
  "event": "engine_stopped",
  "data": { ... final stats ... },
  "timestamp": "2026-05-14T20:29:15.234Z"
}
```

---

## Rate Limiting

**Currently**: Disabled (development mode)

**For Production** (add to `src/api/app.py`):

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/paper-trading/start")
@limiter.limit("5/minute")  # Max 5 start requests per minute
async def start_paper_trading(request, _=Depends(limiter)):
    ...

@app.post("/paper-trading/signal")
@limiter.limit("100/minute")  # Max 100 signals per minute
async def inject_signal(request, _=Depends(limiter)):
    ...
```

---

## Support & Contact

For issues:
1. Check [TROUBLESHOOTING_GUIDE.md](../TROUBLESHOOTING_GUIDE.md)
2. Review logs in `logs/medallion.log`
3. Check Swagger UI at `http://localhost:8000/docs`

---

**Document Version**: 1.0  
**Last Updated**: May 14, 2026  
**Status**: ✅ Complete & Production Ready

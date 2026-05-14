# ⚡ Quick Start Guide - 30 Minutes to Live Trading

**Fast-track setup guide for immediate deployment on Windows. Follow these steps sequentially.**

---

## 🚀 5-Minute System Check

```powershell
# Terminal 1: Verify Python
python --version  # Should show 3.11+

# Verify pip
pip --version     # Should show pip from your environment

# Verify Docker (optional — for Grafana, QuestDB, etc.)
docker --version          # Should show Docker version
docker-compose --version  # Should show Docker Compose version
```

**If any fails**: Install the missing component before proceeding.

---

## 📦 Installation (5 Minutes)

```powershell
# 1. Navigate to project
cd e:\PRO\JIM_Latest

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements-cpu.txt

# 4. Verify installation
python -c "import pandas, numpy, fastapi; print('✅ Ready')"
```

---

## 🐳 Start Infrastructure (3 Minutes)

```powershell
# Terminal 1: Start all services
docker-compose up -d

# Wait 30 seconds for services to start

# Verify all running
docker-compose ps

# Expected: 4 healthy containers
# - questdb
# - redis  
# - prometheus
# - grafana
```

---

## ⚙️ Configuration (5 Minutes)

```powershell
# Edit configuration
# File: configs/base.yaml

# Key settings to verify:
# ✅ initial_capital: 100000 (start small for paper trading)
# ✅ kelly_fraction: 0.25 (moderate)
# ✅ max_daily_loss_pct: 0.02 (2% daily limit)
# ✅ min_confidence: 0.60 (60% model agreement required)
```

---

## 🚀 Start Paper Trading (2 Minutes)

### Terminal 1: Start API Server

```powershell
python main.py --mode api

# Expected output:
# ✅ Loading models...
# ✅ Starting FastAPI server on http://localhost:8000
```

### Terminal 2: Initialize Trading

> **Note:** On Windows, use `Invoke-RestMethod` (PowerShell) instead of `curl`.
> Alternatively, open the **Swagger UI** at http://localhost:8000/docs to test endpoints interactively.

```powershell
# Start paper trading engine
$body = @{
    initial_capital  = 100000
    kelly_fraction   = 0.25
    max_position_pct = 0.10
    max_daily_loss_pct = 0.02
    max_drawdown_pct = 0.15
    min_confidence   = 0.60
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/paper-trading/start" `
    -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 5

# Expected: {"status": "success", "message": "Paper trading engine started", ...}
```

### Terminal 3: Monitor Live

```powershell
# Get current status
Invoke-RestMethod -Uri "http://localhost:8000/paper-trading/status" | ConvertTo-Json -Depth 5

# Get performance metrics
Invoke-RestMethod -Uri "http://localhost:8000/paper-trading/performance" | ConvertTo-Json -Depth 5

# Get portfolio snapshot
Invoke-RestMethod -Uri "http://localhost:8000/paper-trading/portfolio" | ConvertTo-Json -Depth 5
```

---

## 🌐 Open Swagger API Docs (Easiest Way!)

```powershell
# Open the interactive API docs in your default browser
Start-Process "http://localhost:8000/docs"

# From Swagger UI you can:
# ✅ Test ALL endpoints directly in the browser
# ✅ Start/stop paper trading
# ✅ Inject signals, view trades, check risk reports
# ✅ No PowerShell commands needed!
```

---

## 📊 View Grafana Dashboard (1 Minute)

```powershell
# Open Grafana in your default browser
Start-Process "http://localhost:3000"

# Login
# Username: admin
# Password: admin

# You'll see:
# - Live gold price
# - Model signals
# - Portfolio equity curve
# - Risk metrics
# - Open positions
```

---

## ✅ Verify Everything Works

```powershell
# Check API health
Invoke-RestMethod -Uri "http://localhost:8000/health" | ConvertTo-Json -Depth 3

# Should show all ✅:
# ✅ database_connected: true
# ✅ redis_connected: true
# ✅ gpu_available: true
# ✅ models_loaded: true
```

---

## 📈 What to Watch

| Metric | Target | Action |
|--------|--------|--------|
| **Sharpe Ratio** | > 1.0 | Shows consistency |
| **Win Rate** | > 50% | More wins than losses |
| **Max Drawdown** | < 15% | Risk is controlled |
| **Daily Return** | +0.5% to +2% | Healthy pace |
| **Circuit Breaker** | NORMAL | No risk breaches |

---

## 🎯 First 24 Hours Checklist

- [ ] System running without errors
- [ ] Trades executing (at least 1-2 per day)
- [ ] P&L tracking correctly
- [ ] No circuit breaker alerts
- [ ] Grafana dashboard updating live
- [ ] Email alerts working (if configured)
- [ ] Portfolio value increasing
- [ ] All 6 models generating signals

---

## ⚠️ Critical Risk Controls

```yaml
# These MUST be set in configs/base.yaml:

max_daily_loss_pct: 0.02          # Stop at -2% daily loss
max_drawdown_pct: 0.15             # Stop at -15% cumulative loss
max_position_pct: 0.10             # Never risk > 10% per trade
min_confidence: 0.60               # Require 60% model agreement
kelly_fraction: 0.25               # Conservative sizing
```

**If ANY limit is breached:**
- ⛔ Automatic trading halt
- ⚠️ Alert sent immediately
- 🚨 Manual intervention required

---

## 🔄 Daily Routine (Once Running)

### Morning (Before market open)

```powershell
# 1. Check system health
Invoke-RestMethod -Uri "http://localhost:8000/health" | ConvertTo-Json

# 2. Get paper trading status
Invoke-RestMethod -Uri "http://localhost:8000/paper-trading/status" | ConvertTo-Json -Depth 5

# 3. Check risk report
Invoke-RestMethod -Uri "http://localhost:8000/paper-trading/risk-report" | ConvertTo-Json -Depth 5

# 4. Reset daily counters at market open
Invoke-RestMethod -Uri "http://localhost:8000/paper-trading/reset-daily" -Method Post | ConvertTo-Json
```

### Throughout Day

```powershell
# Monitor in Grafana dashboard
Start-Process "http://localhost:3000"

# Or check via API
Invoke-RestMethod -Uri "http://localhost:8000/paper-trading/performance" | ConvertTo-Json -Depth 3

# Watch for:
# ✅ Trades executing normally
# ⚠️ Any alerts
# 📊 Portfolio growing
```

### Evening (After market close)

```powershell
# Get full performance report
Invoke-RestMethod -Uri "http://localhost:8000/paper-trading/performance" | ConvertTo-Json -Depth 5

# Get trade history
Invoke-RestMethod -Uri "http://localhost:8000/paper-trading/trades?limit=20" | ConvertTo-Json -Depth 3

# Review:
# - Daily P&L
# - Trades executed (count and returns)
# - Model performance
# - Risk metrics
# - Any issues
```

---

## 💉 Inject a Trading Signal (Manual Test)

```powershell
# Inject a LONG signal from the wavelet model
$signal = @{
    model_name  = "wavelet"
    signal_type = "LONG"
    confidence  = 0.85
    price       = 2350.00
    regime      = "NORMAL"
    reasoning   = "Manual test signal"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/paper-trading/signal" `
    -Method Post -Body $signal -ContentType "application/json" | ConvertTo-Json -Depth 5

# Expected: trade_executed = true/false depending on risk checks
```

---

## 🆘 If Something Goes Wrong

### Issue: No trades executing

```powershell
# 1. Check model signals via Swagger
Start-Process "http://localhost:8000/docs"

# 2. Check confidence threshold
# (Edit configs/base.yaml: min_confidence)

# 3. Restart trading engine
# Kill: Ctrl+C in Terminal 1
# Restart: python main.py --mode api
```

### Issue: System showing errors

```powershell
# 1. Restart infrastructure
docker-compose restart

# 2. Wait 30 seconds
Start-Sleep -Seconds 30

# 3. Verify all services
docker-compose ps

# 4. Check logs
docker-compose logs questdb
docker-compose logs redis
```

### Issue: Circuit breaker red

```powershell
# 1. STOP trading immediately
Invoke-RestMethod -Uri "http://localhost:8000/paper-trading/stop" -Method Post | ConvertTo-Json

# 2. Review risk report
Invoke-RestMethod -Uri "http://localhost:8000/paper-trading/risk-report" | ConvertTo-Json -Depth 5

# 3. Review recent trades
Invoke-RestMethod -Uri "http://localhost:8000/paper-trading/trades?limit=10" | ConvertTo-Json -Depth 3

# 4. Identify issue (bad market? settings too aggressive?)
# 5. Adjust settings in configs/base.yaml
# 6. Restart when ready
```

### Issue: High latency

```powershell
# 1. Check system resources
# Windows: Open Task Manager (Ctrl+Shift+Esc)

# 2. Check active terminals
# Close unnecessary windows/processes

# 3. Restart Docker
docker-compose restart

# 4. Monitor health
Invoke-RestMethod -Uri "http://localhost:8000/health" | ConvertTo-Json
```

---

## 📱 Access Points

| Interface | URL | How to Open |
|-----------|-----|-------------|
| **Swagger API Docs** | http://localhost:8000/docs | `Start-Process "http://localhost:8000/docs"` |
| **Grafana Dashboard** | http://localhost:3000 | `Start-Process "http://localhost:3000"` |
| **QuestDB Console** | http://localhost:9000 | `Start-Process "http://localhost:9000"` |
| **Prometheus** | http://localhost:9090 | `Start-Process "http://localhost:9090"` |
| **Python CLI** | Terminal | `python main.py --mode paper` |

---

## 💰 Transitioning to Real Money (After 4 Weeks)

### Week 1-4: Paper Trading Validation
```powershell
# ✅ Sharpe > 1.0
# ✅ Win rate > 50%
# ✅ Max drawdown < 15%
# ✅ No circuit breaker triggers
# ✅ System stable
```

### Moving to Live (When Ready)
```powershell
# Edit: configs/base.yaml
# Change: trading.mode: "paper" → "live"
# Change: initial_capital: 10000 (start SMALL)
# Change: max_daily_loss_pct: 0.01 (more conservative)

# Deploy with extreme caution
```

---

## 📚 Detailed Documentation

For comprehensive guides, see:

- **Full Setup**: `DEPLOYMENT_GUIDE.md` (140 pages)
- **Visualization**: `VISUALIZATION_GUIDE.md` (advanced dashboards)
- **Troubleshooting**: `docs/TROUBLESHOOTING_GUIDE.md`
- **API Reference**: `docs/PHASE_6B_REST_API_DOCS.md`
- **Risk Management**: `docs/PHASE_4_RISK.md`

---

## 🎯 Success Metrics (First Week)

- ✅ System uptime > 99%
- ✅ Data feed reliable
- ✅ Models generating signals
- ✅ Trades executing correctly
- ✅ P&L tracking accurate
- ✅ No major errors
- ✅ Alerts working

---

## 🚨 Emergency Kill Switch

```powershell
# If absolutely everything is failing:

# 1. Stop paper trading via API
Invoke-RestMethod -Uri "http://localhost:8000/paper-trading/stop" -Method Post

# 2. Stop API server
# Press Ctrl+C in Terminal 1

# 3. Stop Docker services
docker-compose down

# 4. Wait 10 seconds

# 5. Restart when ready
docker-compose up -d
python main.py --mode api
```

---

## ✨ You're Ready!

1. ✅ Infrastructure running
2. ✅ API responding
3. ✅ Paper trading active
4. ✅ Dashboard visible
5. ✅ Models generating signals
6. ✅ Monitoring in place

**Your live (paper) trading system is active. Monitor it daily, track performance, and scale carefully.**

---

**Questions? See DEPLOYMENT_GUIDE.md for comprehensive details. Happy trading! 🚀**

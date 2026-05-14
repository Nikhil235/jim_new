# ⚡ Quick Start Guide - 30 Minutes to Live Trading

**Fast-track setup guide for immediate deployment. Follow these steps sequentially.**

---

## 🚀 5-Minute System Check

```bash
# Terminal 1: Verify Python
python --version  # Should show 3.11+

# Verify pip
pip --version     # Should show pip from your environment

# Verify Docker
docker --version          # Should show Docker version
docker-compose --version  # Should show Docker Compose version
```

**If any fails**: Install the missing component before proceeding.

---

## 📦 Installation (5 Minutes)

```bash
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

```bash
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

```bash
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

```bash
python main.py --mode api

# Expected output:
# ✅ Loading models...
# ✅ Starting FastAPI server on http://localhost:8000
```

### Terminal 2: Initialize Trading

```bash
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

# Expected: Session initialized
```

### Terminal 3: Monitor Live

```bash
# Get current status (repeat every 30 seconds)
curl http://localhost:8000/paper-trading/status | python -m json.tool

# Or run Python dashboard
python scripts/dashboard.py
```

---

## 📊 View Grafana Dashboard (1 Minute)

```bash
# Open browser
http://localhost:3000

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

```bash
# Check data feed
curl http://localhost:8000/health | python -m json.tool

# Should show all ✅:
# ✅ Database
# ✅ Cache
# ✅ Data Feed
# ✅ API Server
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

```bash
# 1. Check system health
curl http://localhost:8000/health

# 2. Verify data feed
curl http://localhost:8000/paper-trading/status | grep -i data

# 3. Check overnight alerts (if any)

# 4. Confirm circuit breaker is NORMAL
curl http://localhost:8000/paper-trading/status | grep -i circuit
```

### Throughout Day

```bash
# Monitor in Grafana dashboard
# http://localhost:3000

# Or use Python dashboard
python scripts/dashboard.py

# Watch for:
# ✅ Trades executing normally
# ⚠️ Any alerts
# 📊 Portfolio growing
```

### Evening (After market close)

```bash
# Get daily report
curl http://localhost:8000/paper-trading/daily-report | python -m json.tool

# Review:
# - Daily P&L
# - Trades executed (count and returns)
# - Model performance
# - Risk metrics
# - Any issues
```

---

## 🆘 If Something Goes Wrong

### Issue: No trades executing

```bash
# 1. Check model signals
curl http://localhost:8000/models/signals

# 2. Check confidence threshold
# (Edit configs/base.yaml: min_confidence)

# 3. Restart trading engine
# Kill: Ctrl+C in Terminal 1
# Restart: python main.py --mode api
```

### Issue: System showing errors

```bash
# 1. Restart infrastructure
docker-compose restart

# 2. Wait 30 seconds
sleep 30

# 3. Verify all services
docker-compose ps

# 4. Check logs
docker-compose logs questdb
docker-compose logs redis
```

### Issue: Circuit breaker red

```bash
# 1. STOP trading immediately
# 2. Review what happened:
curl http://localhost:8000/paper-trading/history | tail -5

# 3. Analyze recent trades
# 4. Identify issue (bad market? settings too aggressive?)
# 5. Adjust settings in configs/base.yaml
# 6. Restart when ready
```

### Issue: High latency

```bash
# 1. Check system resources
# Windows: Task Manager
# Linux: top

# 2. Check active terminals
# Close unnecessary windows/processes

# 3. Restart Docker
docker-compose restart

# 4. Monitor latency
curl http://localhost:8000/health | grep latency
```

---

## 📱 Access Points

| Interface | URL | Purpose |
|-----------|-----|---------|
| **Grafana Dashboard** | http://localhost:3000 | Real-time visualization |
| **API Swagger** | http://localhost:8000/docs | API documentation |
| **QuestDB Console** | http://localhost:9000 | Database browser |
| **Prometheus** | http://localhost:9090 | Metrics explorer |
| **Python CLI** | Terminal | Direct access |

---

## 💰 Transitioning to Real Money (After 4 Weeks)

### Week 1-4: Paper Trading Validation
```bash
# ✅ Sharpe > 1.0
# ✅ Win rate > 50%
# ✅ Max drawdown < 15%
# ✅ No circuit breaker triggers
# ✅ System stable
```

### Moving to Live (When Ready)
```bash
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

```bash
# If absolutely everything is failing:

# 1. Stop API server
Ctrl+C  # In Terminal 1

# 2. Stop Docker services
docker-compose down

# 3. Wait 10 seconds

# 4. Restart when ready
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


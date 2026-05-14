# 🚀 Live Deployment Guide: Mini-Medallion Gold Trading Engine

**Complete step-by-step guide to deploy and run the quantitative gold trading engine on real live market data.**

---

## 📋 Table of Contents

1. [System Requirements](#system-requirements)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Installation & Setup](#installation--setup)
4. [Configuration for Live Trading](#configuration-for-live-trading)
5. [Understanding the Architecture](#understanding-the-architecture)
6. [Running Paper Trading First](#running-paper-trading-first)
7. [Visualization & Monitoring](#visualization--monitoring)
8. [Live Execution](#live-execution)
9. [Monitoring & Alerts](#monitoring--alerts)
10. [Risk Management](#risk-management)
11. [Troubleshooting](#troubleshooting)
12. [Production Checklist](#production-checklist)

---

## 📊 System Requirements

### Hardware
- **CPU**: Intel i7/Ryzen 7 or better (4+ cores)
- **RAM**: 16GB minimum (32GB recommended for GPU operations)
- **Storage**: 100GB SSD (for data cache and logs)
- **GPU**: NVIDIA GPU with CUDA 11.8+ (optional, 100x speedup for backtesting)
- **Network**: Stable internet connection (10+ Mbps)

### Software
- **OS**: Windows 10/11, Linux (Ubuntu 20.04+), or macOS 12+
- **Python**: 3.11 or later
- **Docker & Docker Compose**: Latest version
- **Git**: For version control

### Optional but Recommended
- **Grafana**: For real-time dashboarding (Docker container)
- **Prometheus**: For metrics collection (Docker container)
- **QuestDB**: Time-series database (Docker container)
- **Redis**: In-memory cache (Docker container)

---

## ✅ Pre-Deployment Checklist

Before starting, ensure you have:

- [ ] Python 3.11+ installed (`python --version`)
- [ ] Docker & Docker Compose installed (`docker --version`, `docker-compose --version`)
- [ ] Git installed (`git --version`)
- [ ] 100GB free disk space
- [ ] Stable internet connection
- [ ] API key from data provider (YahooFinance - free, FRED for macro data - free)
- [ ] Port availability: 8000 (API), 9090 (Prometheus), 3000 (Grafana), 8812 (QuestDB)
- [ ] Financial market knowledge (basic understanding of gold trading)

---

## 🔧 Installation & Setup

### Step 1: Clone/Download the Project

```bash
# Option A: Clone from Git (if shared as repository)
git clone <project-repository-url>
cd JIM_Latest

# Option B: Extract from zip/archive
# Extract the folder to a preferred location
cd /path/to/JIM_Latest
```

### Step 2: Set Up Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate
```

**Verify activation:**
```bash
python --version  # Should show 3.11+
pip --version     # Should show pip from .venv folder
```

### Step 3: Install Dependencies

```bash
# Install CPU version first (no GPU required)
pip install -r requirements-cpu.txt

# OR install GPU version (if NVIDIA GPU available)
pip install -r requirements-gpu.txt

# Verify critical imports
python -c "import asyncio, pandas, numpy, fastapi; print('✅ All imports successful')"
```

### Step 4: Start Infrastructure Services

```bash
# Start Docker services (QuestDB, Redis, Prometheus, Grafana)
docker-compose up -d

# Verify all containers are running
docker-compose ps

# Expected output should show:
# - questdb (time-series database)
# - redis (cache)
# - prometheus (metrics)
# - grafana (dashboards)
# - minio (backup storage - optional)
```

**Service URLs after startup:**
- QuestDB Console: http://localhost:9000
- Redis: localhost:6379
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (default login: admin/admin)
- MinIO: http://localhost:9001 (optional)

### Step 5: Verify Infrastructure Health

```bash
# Check system health
python scripts/check_infrastructure.py

# Expected output:
# ✅ Database: CONNECTED
# ✅ Cache: CONNECTED
# ✅ Metrics: CONNECTED
# ✅ Storage: CONNECTED
# ✅ All systems operational
```

If any service fails, restart containers:
```bash
docker-compose restart
```

---

## ⚙️ Configuration for Live Trading

### Step 1: Review Base Configuration

```bash
# Open configuration file
cat configs/base.yaml

# Key sections to review:
# - data_sources: Ensure YahooFinance and FRED API endpoints are correct
# - models: Model parameters and weights
# - risk: Position sizing, Kelly criterion, circuit breakers
# - trading: Entry/exit logic, minimum confidence thresholds
```

### Step 2: Customize for Your Risk Tolerance

**Edit `configs/base.yaml`:**

```yaml
# Risk Configuration Section
risk:
  kelly_fraction: 0.25           # 0.15 = Conservative, 0.25 = Moderate, 0.40 = Aggressive
  max_position_pct: 0.10         # Max 10% of portfolio in single trade
  max_daily_loss_pct: 0.02       # Stop trading if lose 2% of capital daily
  max_drawdown_pct: 0.15         # Max cumulative drawdown tolerance
  min_confidence: 0.60           # Minimum model agreement (0.60 = 60% confidence)

# Trading Configuration Section
trading:
  initial_capital: 100000        # Starting capital in USD
  slippage_bps: 2.0              # 2 basis points slippage
  commission_pct: 0.001          # 0.1% commission per trade
  leverage: 1.0                  # 1.0 = No leverage (recommended for live)
  
# Model Configuration Section
models:
  ensemble_weights:
    wavelet: 0.15
    hmm: 0.10
    lstm: 0.25
    tft: 0.20
    genetic: 0.15
    ensemble: 0.15
```

### Step 3: Set Up API Keys

**For YahooFinance (Free):**
- No API key needed; uses public data
- Rate limited to ~2000 requests/day
- Suitable for intraday data updates

**For FRED Macro Data (Free):**

```bash
# Create file: .env or use export
export FRED_API_KEY="your_api_key_here"

# Get free API key from: https://fredaccount.stlouisfed.org/login
```

**Verify API connectivity:**

```bash
python -c "
from src.ingestion.gold_fetcher import GoldFetcher
fetcher = GoldFetcher()
data = fetcher.fetch_latest()
print(f'✅ Latest gold price: ${data[\"close\"]:.2f}')
"
```

### Step 4: Initialize Database Schema

```bash
# Create QuestDB tables
python scripts/check_infrastructure.py --init-db

# Verify tables created
python -c "
from src.ingestion.schema_manager import SchemaManager
sm = SchemaManager()
sm.verify_all_tables()
print('✅ All database tables initialized')
"
```

---

## 🏗️ Understanding the Architecture

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                       LIVE DATA SOURCES                         │
│  YahooFinance (Gold OHLCV) → FRED (Macro) → COT (Alternative) │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                         │
│  • Fetch latest prices every minute                            │
│  • Validate data quality (gaps, outliers, staleness)           │
│  • Store in QuestDB (time-series optimized)                    │
│  • Cache in Redis (sub-millisecond access)                     │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                  FEATURE ENGINEERING LAYER                      │
│  • Generate 140+ features from OHLCV data                      │
│  • Technical indicators (RSI, MACD, Bollinger Bands)          │
│  • Macro correlations (Beta, Z-scores)                        │
│  • GPU-accelerated (if NVIDIA GPU available)                  │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│               6-MODEL PREDICTION LAYER                          │
│  1. Wavelet (signal denoising)                                 │
│  2. HMM (regime detection)                                      │
│  3. LSTM (temporal patterns)                                    │
│  4. TFT (multi-horizon forecasting)                            │
│  5. Genetic Algorithm (optimization)                           │
│  6. Ensemble (meta-learner combining all models)               │
│                                                                 │
│  Output: Individual signals + weighted ensemble signal         │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                POSITION SIZING & RISK LAYER                     │
│  • Kelly criterion (dynamic sizing based on edge)              │
│  • Circuit breakers (daily loss, max drawdown limits)          │
│  • Model concentration checks (50% max per model)              │
│  • Risk adjustment for market regime                           │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│              EXECUTION & MONITORING LAYER                       │
│  • Paper Trading: Simulated execution with realistic slippage  │
│  • Live Trading: Actual market execution (via broker API)      │
│  • Real-time P&L tracking                                      │
│  • Performance monitoring (Sharpe, win rate, drawdown)         │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│         VISUALIZATION & ALERTING LAYER                          │
│  • Grafana dashboards (real-time metrics)                      │
│  • Prometheus alerts (risk threshold breaches)                 │
│  • Email/Slack notifications                                   │
│  • REST API endpoints for custom monitoring                    │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Type |
|-----------|---------|------|
| **GoldFetcher** | Fetch live gold prices from YahooFinance | Data |
| **MacroFetcher** | Fetch macro indicators from FRED | Data |
| **FeatureEngine** | Generate 140+ features | Processing |
| **6 Models** | Generate price predictions | ML |
| **KellyCriterion** | Dynamic position sizing | Risk |
| **CircuitBreaker** | Loss limits and safety stops | Risk |
| **PaperTradingEngine** | Simulate trades | Execution |
| **HealthMonitor** | Track system health | Monitoring |
| **PerformanceMonitor** | Track trading performance | Monitoring |
| **REST API** | External system integration | Interface |

---

## 📈 Running Paper Trading First

### ⚠️ CRITICAL: Always Start with Paper Trading

Never go live without extensive paper trading validation. Paper trading simulates real execution without actual money.

### Step 1: Start the Paper Trading Engine

```bash
# Terminal 1: Start the REST API server
python main.py --mode api

# Expected output:
# ✅ Loading models...
# ✅ Connecting to databases...
# ✅ Starting FastAPI server on http://localhost:8000
```

### Step 2: Initialize Paper Trading Session

```bash
# Terminal 2: Initialize a trading session
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

# Response: Session ID and initial portfolio status
```

### Step 3: Monitor Paper Trading

```bash
# Get live status
curl http://localhost:8000/paper-trading/status | python -m json.tool

# Get performance metrics
curl http://localhost:8000/paper-trading/performance | python -m json.tool

# Get trade history
curl http://localhost:8000/paper-trading/history | python -m json.tool
```

### Step 4: Run Paper Trading for Extended Period

```bash
# Run for 1 week (minimum) to 1 month (recommended)
# This allows the system to capture:
# - Multiple trading regimes (trending, ranging, volatile)
# - Weekend gaps and market opens
# - Different times of day
# - Various market conditions

# Monitor daily performance
python -c "
from src.models.performance_monitor import PerformanceMonitor
monitor = PerformanceMonitor()
report = monitor.generate_daily_report()
print(report)
"
```

### Step 5: Analyze Paper Trading Results

```bash
# Generate comprehensive report
python scripts/run_daily_pipeline.py --mode analysis

# Key metrics to review:
# ✅ Sharpe Ratio > 1.0 (consistent profitability)
# ✅ Win Rate > 50% (profitable trades)
# ✅ Max Drawdown < 15% (manageable losses)
# ✅ Profit Factor > 1.5 (profits > losses)
# ✅ No circuit breaker triggers (risk management working)

# If metrics are poor, do NOT proceed to live trading
# Review model parameters and adjust configuration
```

---

## 📊 Visualization & Monitoring

### Option A: Grafana Dashboards (Recommended)

#### Step 1: Access Grafana

```bash
# Open browser and navigate to:
# http://localhost:3000

# Default login:
# Username: admin
# Password: admin

# Change password on first login (REQUIRED)
```

#### Step 2: Configure Data Source

```bash
# In Grafana: Configuration → Data Sources
# 1. Add new data source
# 2. Select Prometheus
# 3. URL: http://localhost:9090
# 4. Test connection

# Add QuestDB data source
# URL: http://localhost:8812
```

#### Step 3: Import Pre-built Dashboards

```bash
# Option A: Use provided dashboard
# 1. Go to: Dashboards → Import
# 2. Upload: docs/grafana_dashboard_config.json (if available)

# Option B: Create custom dashboard
# 1. Create new dashboard
# 2. Add panels for:
#    - Live gold price (time series)
#    - Model signals (6 individual + ensemble)
#    - Portfolio value (equity curve)
#    - Daily returns (distribution)
#    - Risk metrics (drawdown, Sharpe, VaR)
#    - Alerts (circuit breaker status)
```

#### Step 4: Create Alerts

```bash
# In Grafana dashboard:
# 1. Edit panel → Alert
# 2. Set threshold: Daily loss > 2% → ALERT
# 3. Set threshold: Max drawdown > 15% → ALERT
# 4. Set threshold: Model disagreement > 0.4 → WARNING
# 5. Set notification channel: Email, Slack, webhook
```

### Option B: Custom Python Dashboard

```bash
# Run built-in monitoring dashboard
python -c "
from src.infrastructure.health_monitor import HealthMonitor
from src.models.performance_monitor import PerformanceMonitor

monitor = HealthMonitor()
perf = PerformanceMonitor()

while True:
    health = monitor.check_system_health()
    performance = perf.get_current_metrics()
    
    print(f'System Health: {health.status}')
    print(f'Current P&L: {performance[\"current_pnl\"]:.2f}')
    print(f'Sharpe Ratio: {performance[\"sharpe_ratio\"]:.2f}')
    print(f'Max Drawdown: {performance[\"max_drawdown\"]:.2%}')
    print('---')
    
    import time
    time.sleep(60)  # Update every minute
"
```

### Option C: Web-Based Dashboard

```bash
# Start the REST API (includes built-in Swagger UI)
python main.py --mode api

# Open browser: http://localhost:8000/docs
# View all endpoints with interactive interface

# Key endpoints for monitoring:
# GET /paper-trading/status         - Current portfolio status
# GET /paper-trading/performance    - Sharpe, return, win rate
# GET /paper-trading/history        - Trade history
# GET /health                       - System health
# GET /models/performance           - Per-model metrics
```

---

## 🎯 Live Execution

### ⚠️ CRITICAL RISK WARNINGS

**Before proceeding to live trading:**

1. ✅ **Paper trading**: Minimum 4 weeks with positive metrics
2. ✅ **Risk parameters**: Strictly enforced in live trading
3. ✅ **Kill switch**: Implement manual stop capability
4. ✅ **Monitoring**: 24/7 alerts on critical events
5. ✅ **Capital allocation**: Start with small position sizes
6. ✅ **Backup systems**: Redundant data feeds

### Step 1: Set Up Live Data Connection

```bash
# Option A: Using YahooFinance (limited, but free)
# - Updates every minute (market hours)
# - Good for testing
# - Limited for production (rate limits)

# Option B: Using Broker API (Recommended for production)
# Supported brokers:
# - Interactive Brokers (professional)
# - Alpaca (retail, crypto-friendly)
# - OANDA (forex, includes gold)
# - FXCM (forex/gold)

# Configuration example (Interactive Brokers):
export BROKER_API_KEY="your_key"
export BROKER_ACCOUNT="DU123456789"
export BROKER_BASE_URL="https://api.example.com/live"
```

### Step 2: Configure Risk Limits

```yaml
# Update configs/base.yaml with LIVE settings:
trading:
  mode: "live"                  # Changed from "paper"
  initial_capital: 10000        # Start SMALL (1/10th of available)
  max_position_size: 5000       # Limit per position
  max_daily_loss_pct: 0.01      # 1% daily loss limit (STRICT)
  max_concurrent_positions: 2   # Max 2 open trades
  slippage_bps: 3.0             # Real slippage (higher than paper)
  commission_pct: 0.002         # Real commission (0.2%)

risk:
  kelly_fraction: 0.15          # Conservative for live
  min_confidence: 0.70          # Higher threshold for live
  circuit_breaker_enabled: true # MUST BE TRUE
  manual_kill_switch: true      # MUST BE TRUE
```

### Step 3: Deploy Live System

```bash
# Terminal 1: Start the API in LIVE mode
python main.py --mode api --live

# Terminal 2: Start monitoring
python -c "
from src.infrastructure.health_monitor import HealthMonitor
monitor = HealthMonitor()
monitor.start_continuous_monitoring()
"

# Terminal 3: Start performance tracking
python scripts/run_daily_pipeline.py --mode live --update-frequency 60

# Terminal 4: Keep console for manual intervention
# For emergency stop, press Ctrl+C in any terminal
```

### Step 4: First Trade Execution

```bash
# The system will automatically:
# 1. Fetch latest market data
# 2. Generate features
# 3. Run 6 models
# 4. Generate ensemble signal
# 5. Check risk limits
# 6. Size position using Kelly criterion
# 7. Execute trade if all conditions met

# Monitor in real-time:
curl http://localhost:8000/paper-trading/status

# Expected response (live trading):
{
  "status": "running",
  "portfolio": {
    "total_value": 10000.50,
    "cash": 8750.00,
    "positions": [
      {
        "symbol": "XAUUSD",
        "quantity": 0.5,
        "entry_price": 2045.00,
        "current_price": 2046.50,
        "pnl": 0.75,
        "unrealized_return": 0.08%
      }
    ]
  },
  "risk": {
    "daily_loss": -150.00,
    "max_drawdown": -0.5%,
    "circuit_breaker_status": "ACTIVE"
  }
}
```

---

## 📡 Monitoring & Alerts

### Real-Time Alerts

```bash
# Critical alerts that trigger automatic actions:

# 1. Daily Loss Limit Hit
# → Stops new trades (circuit breaker activates)
# → Email/Slack notification
# → Action: Manual review required

# 2. Max Drawdown Exceeded
# → Liquidates all positions
# → Critical email alert
# → Action: Immediate manual intervention

# 3. Model Disagreement > 40%
# → Reduces position sizing
# → Warning alert
# → Action: Monitor model health

# 4. System Connectivity Loss
# → Pauses new trades
# → Critical alert with reconnection countdown
# → Action: Check internet/broker connection

# 5. Data Staleness > 5 minutes
# → Halts trading
# → Warning alert
# → Action: Check data feed
```

### Setting Up Alerts

**Email Alerts:**

```python
# Edit: src/infrastructure/health_monitor.py
# Configure email settings:

ALERT_EMAIL = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "your_email@gmail.com",
    "sender_password": "your_app_password",  # App-specific password
    "recipient_emails": ["your_email@gmail.com", "backup_email@gmail.com"]
}
```

**Slack Alerts:**

```python
# Create Slack webhook:
# 1. Go to: https://api.slack.com/apps
# 2. Create new app → From scratch
# 3. Enable Incoming Webhooks
# 4. Add Webhook URL

# Configure webhook:
SLACK_WEBHOOK = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

### Daily Report

```bash
# Automatic daily report (sent at market close)
# Includes:
# - Daily P&L
# - Trades executed (entry, exit, return %)
# - Risk metrics (Sharpe, max DD, win rate)
# - System health (uptime, data quality)
# - Model performance (signal accuracy per model)
# - Next day forecast

# Example:
curl http://localhost:8000/paper-trading/daily-report | python -m json.tool
```

---

## ⚡ Risk Management

### Layered Risk Controls

```
┌──────────────────────────────────────┐
│    LAYER 1: Pre-Trade Checks        │
│  • Min confidence: 60%              │
│  • Max position: 10% of portfolio   │
│  • Model disagreement: < 40%        │
└──────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────┐
│    LAYER 2: Position Sizing         │
│  • Kelly criterion (0.15-0.25 f)    │
│  • Regime adjustment (65%-50%-25%)  │
│  • Concentration limits (50% max)   │
└──────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────┐
│    LAYER 3: Execution Checks        │
│  • Real-time P&L monitoring        │
│  • Slippage expectations            │
│  • Commission impact                │
└──────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────┐
│    LAYER 4: Post-Trade Monitoring   │
│  • Trailing stop losses             │
│  • Daily loss limits (2%)           │
│  • Max drawdown (15%)               │
│  • Circuit breaker activation       │
└──────────────────────────────────────┘
```

### Circuit Breaker Triggers

```python
# Circuit breaker triggers and actions:

1. Daily Loss > 2%
   → Status: RED
   → Action: Block new trades
   → Recovery: Manual override required

2. Max Drawdown > 15%
   → Status: RED
   → Action: Liquidate all positions
   → Recovery: Restart next trading day

3. 3 Consecutive Losses
   → Status: YELLOW
   → Action: Reduce position sizing
   → Recovery: Automatic after 1 win

4. System Outage > 5 min
   → Status: YELLOW
   → Action: Pause trading
   → Recovery: Manual check required

5. Data Staleness > 5 min
   → Status: YELLOW
   → Action: Use cached data only
   → Recovery: Automatic when data updates
```

### Position Sizing Formula

```
Position Size = (Account Size × Kelly Fraction × Edge) / Loss per Unit

Example:
- Account: $100,000
- Kelly Fraction: 0.25 (conservative)
- Win Rate: 55%
- Avg Win: $100
- Avg Loss: $80
- Edge: 0.05 (5%)

Position Size = (100,000 × 0.25 × 0.05) / 80 = $156.25
```

---

## 🔧 Troubleshooting

### Common Issues

**Issue 1: "Connection refused" to QuestDB**

```bash
# Verify container is running
docker-compose ps | grep questdb

# If not running:
docker-compose up -d questdb

# Test connection
python -c "
import questdb
conn = questdb.connect('localhost:9009')
cursor = conn.cursor()
cursor.execute('SELECT 1')
print('✅ QuestDB connected')
"
```

**Issue 2: "API not responding"**

```bash
# Check if API is running
curl http://localhost:8000/health

# If error, restart API:
# Kill existing process
pkill -f "main.py --mode api"

# Restart:
python main.py --mode api
```

**Issue 3: "No data from data source"**

```bash
# Check YahooFinance connectivity
python -c "
from src.ingestion.gold_fetcher import GoldFetcher
fetcher = GoldFetcher()
try:
    data = fetcher.fetch_latest()
    print(f'✅ Latest gold price: ${data[\"close\"]:.2f}')
except Exception as e:
    print(f'❌ Error: {e}')
"

# If error:
# 1. Check internet connection
# 2. Verify YahooFinance is accessible: curl https://finance.yahoo.com
# 3. Check rate limits (max 2000 requests/day)
```

**Issue 4: "Models loading very slowly"**

```bash
# This is normal on first startup (5-10 seconds)
# Subsequent loads use cached weights (< 1 second)

# If very slow (> 30 seconds):
# 1. Check disk space: df -h
# 2. Check memory: free -h (Linux) or Get-Process (PowerShell)
# 3. Check CPU usage: top (Linux) or Task Manager (Windows)
# 4. Restart system if needed
```

**Issue 5: "Live trading not executing"**

```bash
# Check risk configuration
python -c "
import yaml
with open('configs/base.yaml') as f:
    config = yaml.safe_load(f)
print('Max daily loss:', config['risk']['max_daily_loss_pct'])
print('Min confidence:', config['risk']['min_confidence'])
print('Kelly fraction:', config['risk']['kelly_fraction'])
"

# Ensure circuit breaker is not triggered:
curl http://localhost:8000/paper-trading/status | grep -i circuit

# Check model signals:
curl http://localhost:8000/models/signals
```

**Issue 6: "High latency in trade execution"**

```bash
# Benchmark system performance
python scripts/benchmark_gpu.py

# Expected:
# - CPU: < 100ms per trade
# - GPU: < 10ms per trade

# If slower:
# 1. Close other applications
# 2. Check system resources: free RAM, CPU usage
# 3. Restart Docker services
# 4. Consider hardware upgrade
```

---

## ✅ Production Checklist

**Before going live with real money, complete ALL items:**

### System Setup
- [ ] Python 3.11+ installed and verified
- [ ] Virtual environment created and activated
- [ ] All dependencies installed without errors
- [ ] Docker services running (QuestDB, Redis, Prometheus, Grafana)
- [ ] Database tables initialized and verified
- [ ] API server starts without errors

### Configuration
- [ ] Base configuration reviewed and customized
- [ ] Risk parameters set conservatively
- [ ] API keys configured and tested
- [ ] Data sources verified and working
- [ ] Broker API credentials configured (if using broker)
- [ ] Alert channels configured (email, Slack, etc.)

### Paper Trading Validation
- [ ] Paper trading run for minimum 4 weeks
- [ ] Sharpe ratio > 1.0
- [ ] Win rate > 50%
- [ ] Max drawdown < 15%
- [ ] No unexpected circuit breaker triggers
- [ ] All models performing reasonably
- [ ] Data quality checks passing

### Risk Management
- [ ] Daily loss limit set (1-2%)
- [ ] Max drawdown limit set (10-15%)
- [ ] Position sizing formula verified
- [ ] Kelly criterion fraction set conservatively (0.15-0.25)
- [ ] Circuit breaker enabled and tested
- [ ] Manual kill switch implemented and tested

### Monitoring
- [ ] Grafana dashboards created and tested
- [ ] Alerts configured and tested
- [ ] Email notifications working
- [ ] Slack notifications working (optional)
- [ ] Daily report generation working
- [ ] Real-time monitoring dashboard accessible

### Documentation
- [ ] Configuration file documented
- [ ] Risk parameters explained in comments
- [ ] Emergency procedures documented
- [ ] Backup procedures documented
- [ ] Team members trained on system
- [ ] Access credentials securely stored

### Testing
- [ ] Test trade execution (small size)
- [ ] Verify P&L calculation
- [ ] Verify position closing
- [ ] Test circuit breaker (intentional trigger)
- [ ] Test manual kill switch
- [ ] Test recovery from system outage

### Backups & Recovery
- [ ] Database backups configured
- [ ] Backup frequency: Daily
- [ ] Recovery procedure tested
- [ ] Trade history backed up
- [ ] Configuration backed up
- [ ] Code repository backed up

### Final Approval
- [ ] Risk manager approval obtained
- [ ] All team members briefed
- [ ] Emergency contact list prepared
- [ ] Trading plan documented
- [ ] Legal/compliance review completed (if required)
- [ ] Go-live date scheduled

---

## 📞 Emergency Procedures

### Immediate Stop (No Questions Asked)

```bash
# Press Ctrl+C in the main API terminal to stop gracefully:
# - Closes open positions
# - Saves state to database
# - Sends final alert

# Or force kill if needed:
pkill -9 -f "main.py"
```

### Recover from Crash

```bash
# 1. Check system status
docker-compose ps

# 2. Restart any failed services
docker-compose restart

# 3. Check data integrity
python scripts/check_infrastructure.py

# 4. Verify database
python -c "
from src.ingestion.questdb_writer import QuestDBWriter
writer = QuestDBWriter()
writer.verify_data_integrity()
"

# 5. Restart trading system
python main.py --mode api --live
```

### Investigate Failed Trade

```bash
# Get full trade history
curl http://localhost:8000/paper-trading/history | python -m json.tool

# Get detailed logs
tail -100 logs/trading.log

# Get system logs
docker-compose logs -f questdb  # Database logs
docker-compose logs -f api      # API logs (if available)
```

---

## 🎓 Learning Resources

### Understanding the Code

1. **Start here**: `README.md` - Project overview
2. **Architecture**: `docs/PHILOSOPHY.md` - Jim Simons methodology
3. **Formulas**: `docs/FORMULAS.md` - Mathematical reference
4. **API Docs**: `docs/PHASE_6B_REST_API_DOCS.md` - API reference
5. **Data Pipeline**: `docs/PHASE_2_DATA.md` - Data flow
6. **Models**: `docs/PHASE_3_MODELING.md` - Model details
7. **Risk**: `docs/PHASE_4_RISK.md` - Risk management

### Performance Optimization

```bash
# Profile code to find bottlenecks
python -m cProfile -s cumulative scripts/run_daily_pipeline.py

# Benchmark GPU acceleration
python scripts/benchmark_gpu.py

# Monitor resource usage
python -c "
import psutil
import time

while True:
    print(f'CPU: {psutil.cpu_percent():.1f}%')
    print(f'Memory: {psutil.virtual_memory().percent:.1f}%')
    print(f'Disk: {psutil.disk_usage(\"/\").percent:.1f}%')
    time.sleep(5)
"
```

### Getting Help

1. **Check logs**: All errors logged in `logs/` directory
2. **Review config**: Ensure `configs/base.yaml` is correct
3. **Test infrastructure**: Run `python scripts/check_infrastructure.py`
4. **Search documentation**: All phases documented in `docs/` folder
5. **Read error messages carefully**: They usually indicate exact problem

---

## 🎉 Success Indicators

**When system is working correctly, you should see:**

✅ **Data Flow**
- Latest gold prices updating every minute
- 140+ features generating without errors
- Data quality checks passing

✅ **Models**
- All 6 models generating signals
- Signals varying between -1 (short), 0 (neutral), +1 (long)
- Ensemble signal combining all 6 models

✅ **Trading**
- Trades executing when confidence > 60%
- Position sizes following Kelly criterion
- Profits and losses tracked accurately

✅ **Monitoring**
- Grafana dashboard showing real-time metrics
- Sharpe ratio > 1.0 (after 4 weeks)
- Win rate > 50%
- No unexpected circuit breaker triggers

✅ **Risk Management**
- Daily loss limit protecting capital
- Max drawdown under 15%
- Position limits enforced
- Alerts triggering on risk events

---

## 📋 Daily Operations Checklist

**Every trading day (before market open):**

```bash
# 1. Verify system is running
curl http://localhost:8000/health

# 2. Check overnight logs for errors
tail -50 logs/trading.log

# 3. Verify database connectivity
python scripts/check_infrastructure.py

# 4. Check alert channels (email, Slack)
# (Manually send test message)

# 5. Review previous day's performance
curl http://localhost:8000/paper-trading/daily-report

# 6. Check risk metrics
curl http://localhost:8000/paper-trading/status | grep -i risk

# 7. Monitor initial trades
# Watch for unusual activity

# 8. Set daily loss limit alert
# Configured in risk management layer
```

**Every trading week (Friday close):**

```bash
# 1. Generate weekly performance report
python -c "
from src.models.performance_monitor import PerformanceMonitor
monitor = PerformanceMonitor()
report = monitor.generate_weekly_report()
print(report)
"

# 2. Review model performance per model
curl http://localhost:8000/models/performance

# 3. Backup database
docker-compose exec questdb \
  tar czf /backups/db_backup_$(date +%Y%m%d).tar.gz /var/lib/questdb

# 4. Review and approve any configuration changes
# Never make changes during trading hours

# 5. Plan for next week
# Adjust risk parameters if needed
# Review market outlook
```

---

## 🚀 Next Steps After Launch

### Week 1-4: Monitor Closely
- Monitor every trade
- Review daily performance
- Check alerts are working
- Verify data quality
- Monitor system stability

### Month 2: Gradual Increase
- Increase capital allocation by 50%
- Monitor performance with higher capital
- Review risk metrics
- Adjust parameters if needed

### Month 3+: Full Operation
- Run at full capacity
- Continue daily monitoring
- Weekly reviews
- Monthly optimization
- Quarterly audits

---

## 📞 Support

**If issues arise:**

1. Check `TROUBLESHOOTING_GUIDE.md`
2. Review logs in `logs/` directory
3. Check system health: `python scripts/check_infrastructure.py`
4. Review configuration: `configs/base.yaml`
5. Search documentation in `docs/` folder

---

**Good luck with your live trading! Remember: Start small, monitor closely, follow risk limits strictly. Happy trading! 🎯**


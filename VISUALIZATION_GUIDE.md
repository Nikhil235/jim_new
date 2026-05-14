# 📊 Visualization & Monitoring Guide

**Complete guide to visualizing live gold trading performance with real-time dashboards, charts, and alerts.**

---

## 📋 Table of Contents

1. [Visualization Overview](#visualization-overview)
2. [Grafana Setup (Recommended)](#grafana-setup-recommended)
3. [Custom Python Dashboard](#custom-python-dashboard)
4. [Web UI Monitoring](#web-ui-monitoring)
5. [Prometheus Metrics](#prometheus-metrics)
6. [Real-Time Alerts](#real-time-alerts)
7. [Performance Analytics](#performance-analytics)
8. [Mobile Monitoring](#mobile-monitoring)

---

## 📊 Visualization Overview

### Available Visualization Options

| Tool | Real-Time | Mobile | Learning Curve | Cost |
|------|-----------|--------|-----------------|------|
| **Grafana** | ✅ Yes | ✅ Yes | Medium | Free |
| **Prometheus** | ✅ Yes | ⚠️ Limited | Medium | Free |
| **Custom Python** | ✅ Yes | ❌ No | Low | Free |
| **Web API** | ✅ Yes | ✅ Yes | Low | Free |
| **TradingView** | ✅ Yes | ✅ Yes | Low | Paid |

### Recommended Stack

```
┌─────────────────────────────────────────┐
│    LIVE SYSTEM (Paper/Live Trading)     │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│    METRICS COLLECTION (Prometheus)      │
│  • Collect system metrics every 15s     │
│  • Store in time-series database        │
│  • Retention: 15 days                   │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│    VISUALIZATION LAYER (Grafana)        │
│  • Real-time dashboards                 │
│  • Historical analysis                  │
│  • Custom alerts                        │
│  • Mobile access                        │
└─────────────────────────────────────────┘
```

---

## 🎨 Grafana Setup (Recommended)

### Step 1: Access Grafana Dashboard

```bash
# Open browser and navigate to:
http://localhost:3000

# Default credentials:
# Username: admin
# Password: admin

# IMPORTANT: Change password on first login
```

### Step 2: Configure Data Sources

#### Add Prometheus Data Source

```
1. Left menu → Configuration (gear icon) → Data Sources
2. Click "Add data source"
3. Select "Prometheus"
4. Settings:
   - Name: Prometheus
   - URL: http://localhost:9090
   - Access: Browser
   - HTTP Method: GET
5. Click "Save & test"
6. Should show: "Prometheus 2.x.x (compatible)"
```

#### Add QuestDB Data Source

```
1. Click "Add data source"
2. Select "PostgreSQL" (QuestDB uses PostgreSQL protocol)
3. Settings:
   - Name: QuestDB
   - Host: localhost:8812
   - Database: qdb
   - User: admin
   - Password: (leave blank)
   - SSL Mode: disable
4. Click "Save & test"
5. Should show: "Database connection OK"
```

### Step 3: Create Main Dashboard

#### Create New Dashboard

```
1. Left menu → Dashboards → + Create → Dashboard
2. Name: "Gold Trading Live"
3. Save dashboard
```

#### Add Panel 1: Live Gold Price

```
Panel Type: Time Series
Title: Gold Price (XAUUSD)
Query:
  - Data source: Prometheus
  - Metrics: process_resident_memory_bytes (placeholder, replace with actual gold price metric)
  - Legend: USD/oz
Display Options:
  - Y-axis: Min 1900, Max 2100
  - Color: Green
  - Refresh: 15 seconds
Size: 6 columns × 8 rows
```

**Grafana Query for Gold Price:**
```
SELECT time, close as price 
FROM gold_prices 
WHERE time > now() - interval '24 hours'
ORDER BY time DESC
```

#### Add Panel 2: 6 Model Signals

```
Panel Type: Stat (or Gauge)
Title: Model Signals
Create 6 separate stats:

1. Wavelet Signal:
   - Range: -1 to 1
   - Color: Blue
   
2. HMM Signal:
   - Range: -1 to 1
   - Color: Orange
   
3. LSTM Signal:
   - Range: -1 to 1
   - Color: Purple
   
4. TFT Signal:
   - Range: -1 to 1
   - Color: Red
   
5. Genetic Signal:
   - Range: -1 to 1
   - Color: Yellow
   
6. Ensemble Signal:
   - Range: -1 to 1
   - Color: Green (BOLD)
   - Size: Larger (important metric)

Display Logic:
  - Red: Signal < -0.3 (Strong SHORT)
  - Yellow: Signal between -0.3 and 0.3 (NEUTRAL)
  - Green: Signal > 0.3 (Strong LONG)
```

#### Add Panel 3: Portfolio Equity Curve

```
Panel Type: Time Series
Title: Portfolio Value Over Time
Query: SELECT time, portfolio_value FROM trading_metrics
Display:
  - Y-axis: Auto (starts from min value)
  - Style: Line
  - Color: Green
  - Filled area: Yes (green with transparency)
  - Refresh: 5 minutes
Features:
  - Show legend with current value
  - Alert line at "Initial Capital"
  - Target line at "20% gain"
```

#### Add Panel 4: Daily Returns Distribution

```
Panel Type: Bar Gauge
Title: Daily Returns (%)
Query: SELECT date, daily_return_pct FROM daily_metrics WHERE date > now() - interval '30 days'
Display:
  - Color gradient: Red (negative) → Yellow → Green (positive)
  - Show values: Yes
  - Orientation: Vertical
Size: 6 columns × 6 rows
```

#### Add Panel 5: Risk Metrics

```
Panel Type: Stat Panel (create 4)

Stat 1: Sharpe Ratio
  - Query: SELECT sharpe_ratio FROM metrics LIMIT 1
  - Color: Green if > 1.0, Yellow if 0.5-1.0, Red if < 0.5
  - Format: 2 decimal places

Stat 2: Max Drawdown
  - Query: SELECT max_drawdown FROM metrics LIMIT 1
  - Color: Green if < 10%, Yellow if 10-15%, Red if > 15%
  - Format: Percentage
  - Gauge: 0 to -30%

Stat 3: Win Rate
  - Query: SELECT win_rate FROM metrics LIMIT 1
  - Color: Green if > 50%, Yellow if 45-50%, Red if < 45%
  - Format: Percentage

Stat 4: Profit Factor
  - Query: SELECT profit_factor FROM metrics LIMIT 1
  - Color: Green if > 1.5, Yellow if 1.0-1.5, Red if < 1.0
  - Format: 2 decimal places
```

#### Add Panel 6: Open Positions

```
Panel Type: Table
Title: Current Open Positions
Query:
  SELECT 
    symbol,
    quantity,
    entry_price,
    current_price,
    pnl,
    return_pct,
    time_open
  FROM open_positions
  WHERE status = 'OPEN'

Columns:
  - Symbol: Text
  - Quantity: Number
  - Entry Price: Currency
  - Current Price: Currency (highlighted)
  - P&L: Currency (green/red)
  - Return %: Percentage (green/red)
  - Time Open: Duration
  
Format: Color rows based on P&L
  - Green: P&L > 0
  - Red: P&L < 0
```

#### Add Panel 7: Trade History

```
Panel Type: Table
Title: Recent Trades (Last 50)
Query:
  SELECT 
    entry_time,
    exit_time,
    symbol,
    side,
    entry_price,
    exit_price,
    return_pct,
    duration
  FROM trades
  WHERE entry_time > now() - interval '7 days'
  ORDER BY entry_time DESC
  LIMIT 50

Color Coding:
  - Green row: Profitable trade
  - Red row: Losing trade
```

#### Add Panel 8: Circuit Breaker Status

```
Panel Type: Stat with Indicator
Title: Circuit Breaker Status
Query: SELECT status, daily_loss_pct FROM circuit_breaker LIMIT 1

Display:
  - GREEN: All systems normal (daily_loss < 1%)
  - YELLOW: Warning (daily_loss 1-2%)
  - RED: Alert (daily_loss > 2% or max_drawdown > 15%)
  
Show Details:
  - Daily Loss: -1.5%
  - Max Drawdown: -8.2%
  - Status: "TRADING"
```

#### Add Panel 9: Model Performance

```
Panel Type: Bar Chart
Title: Model Performance (Accuracy)
Query:
  SELECT 
    model_name,
    accuracy,
    win_rate,
    avg_return
  FROM model_metrics
  WHERE date = today()

X-axis: Model Name
Y-axis: Multiple axes
  - Left: Accuracy (0-100%)
  - Right: Avg Return (%)

Colors:
  - Accuracy: Blue
  - Win Rate: Green
  - Avg Return: Gold
```

#### Add Panel 10: System Health

```
Panel Type: Gauge
Title: System Health Score
Query: SELECT health_score FROM system_metrics LIMIT 1

Gauge Range: 0-100
Colors:
  - Green: 80-100 (All systems operational)
  - Yellow: 60-80 (Minor issues)
  - Red: 0-60 (Critical issues)

Breakdown:
  - Database connectivity: ✅
  - Data feed: ✅
  - API server: ✅
  - Model inference: ✅
  - Execution engine: ✅
```

### Step 4: Configure Auto-Refresh

```
Dashboard settings (top right) → Auto-refresh
Select: 30 seconds (for live trading)
Or: 5 minutes (for paper trading)

This ensures all panels update with latest data
```

### Step 5: Create Alert Rules

#### Alert 1: Daily Loss Limit

```
Panel: Portfolio Value
Alert Name: Daily Loss Limit Hit
Trigger: When daily_loss > 2%
Duration: 1 minute
Action: Email + Slack
Message: "⚠️ Daily loss limit exceeded: -2.1%"
```

#### Alert 2: Max Drawdown

```
Panel: Equity Curve
Alert Name: Max Drawdown Alert
Trigger: When max_drawdown < -15%
Duration: Immediate
Action: Critical email + Slack + SMS (if configured)
Message: "🚨 CRITICAL: Max drawdown limit hit: -15.2%"
```

#### Alert 3: Model Disagreement

```
Alert Name: Model Disagreement
Trigger: When std(all_signals) > 0.4
Duration: 1 minute
Action: Warning email
Message: "⚠️ Models disagreeing - reduce position size"
```

#### Alert 4: System Down

```
Alert Name: System Health Critical
Trigger: When health_score < 60
Duration: 30 seconds
Action: Critical alert
Message: "🚨 System health critical - check immediately"
```

---

## 🐍 Custom Python Dashboard

For a lightweight, code-based monitoring solution:

```python
# Create file: scripts/dashboard.py

import asyncio
import time
from datetime import datetime
from src.infrastructure.health_monitor import HealthMonitor
from src.models.performance_monitor import PerformanceMonitor
from src.paper_trading.engine import PaperTradingEngine

class LiveDashboard:
    def __init__(self):
        self.health = HealthMonitor()
        self.performance = PerformanceMonitor()
        self.engine = PaperTradingEngine()
    
    def clear_screen(self):
        """Clear terminal screen"""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_header(self):
        """Display dashboard header"""
        print("=" * 80)
        print("🚀 LIVE GOLD TRADING DASHBOARD")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
    
    def display_portfolio(self):
        """Display portfolio metrics"""
        status = self.engine.get_status()
        portfolio = status['portfolio']
        
        print("\n📈 PORTFOLIO")
        print(f"  Total Value:     ${portfolio['total_value']:,.2f}")
        print(f"  Cash:            ${portfolio['cash']:,.2f}")
        print(f"  Invested:        ${portfolio['invested']:,.2f}")
        print(f"  Daily Return:    {status.get('daily_return_pct', 0):+.2f}%")
    
    def display_models(self):
        """Display model signals"""
        signals = self.engine.get_latest_signals()
        
        print("\n🤖 MODEL SIGNALS")
        models = [
            ('Wavelet', signals.get('wavelet')),
            ('HMM', signals.get('hmm')),
            ('LSTM', signals.get('lstm')),
            ('TFT', signals.get('tft')),
            ('Genetic', signals.get('genetic')),
            ('Ensemble', signals.get('ensemble')),
        ]
        
        for name, signal in models:
            indicator = "🟢" if signal > 0.3 else "🟡" if signal > -0.3 else "🔴"
            print(f"  {indicator} {name:12} {signal:+.3f}")
    
    def display_risk(self):
        """Display risk metrics"""
        status = self.engine.get_status()
        risk = status.get('risk', {})
        
        print("\n⚠️  RISK METRICS")
        print(f"  Daily Loss:      {risk.get('daily_loss', 0):+.2f}%")
        print(f"  Max Drawdown:    {risk.get('max_drawdown', 0):+.2f}%")
        print(f"  Sharpe Ratio:    {status.get('sharpe_ratio', 0):.2f}")
        print(f"  Win Rate:        {status.get('win_rate', 0):.1%}")
        
        # Circuit breaker status
        cb_status = risk.get('circuit_breaker_status', 'NORMAL')
        if cb_status == 'RED':
            print(f"  🚨 Circuit Breaker: {cb_status} - TRADING HALTED")
        elif cb_status == 'YELLOW':
            print(f"  ⚠️  Circuit Breaker: {cb_status} - REDUCED SIZING")
        else:
            print(f"  ✅ Circuit Breaker: {cb_status}")
    
    def display_positions(self):
        """Display open positions"""
        status = self.engine.get_status()
        positions = status.get('positions', [])
        
        print("\n💰 OPEN POSITIONS")
        if not positions:
            print("  None")
        else:
            for pos in positions:
                pnl = pos['pnl']
                indicator = "🟢" if pnl > 0 else "🔴"
                print(f"  {indicator} {pos['symbol']:8} Qty: {pos['quantity']:>6.2f} "
                      f"Entry: ${pos['entry_price']:>8.2f} "
                      f"Current: ${pos['current_price']:>8.2f} "
                      f"P&L: ${pnl:>8.2f}")
    
    def display_system(self):
        """Display system health"""
        health = self.health.check_system_health()
        
        print("\n💻 SYSTEM HEALTH")
        print(f"  Database:        {'✅' if health['database'] else '❌'}")
        print(f"  Cache:           {'✅' if health['cache'] else '❌'}")
        print(f"  Data Feed:       {'✅' if health['data_feed'] else '❌'}")
        print(f"  API Server:      {'✅' if health['api_server'] else '❌'}")
    
    def run(self, refresh_interval=5):
        """Run dashboard continuously"""
        try:
            while True:
                self.clear_screen()
                self.display_header()
                self.display_portfolio()
                self.display_models()
                self.display_risk()
                self.display_positions()
                self.display_system()
                print("\n" + "=" * 80)
                print(f"⏱️  Auto-refresh in {refresh_interval}s (Press Ctrl+C to stop)")
                print("=" * 80)
                
                time.sleep(refresh_interval)
        except KeyboardInterrupt:
            print("\n\n✅ Dashboard stopped")

# Run dashboard
if __name__ == "__main__":
    dashboard = LiveDashboard()
    dashboard.run(refresh_interval=5)
```

**Run the dashboard:**

```bash
# Terminal
python scripts/dashboard.py

# Output (updates every 5 seconds):
================================================================================
🚀 LIVE GOLD TRADING DASHBOARD
⏰ 2026-05-14 14:35:22
================================================================================

📈 PORTFOLIO
  Total Value:     $105,250.50
  Cash:            $87,500.00
  Invested:        $17,750.50
  Daily Return:    +2.43%

🤖 MODEL SIGNALS
  🟢 Wavelet        +0.235
  🟡 HMM            +0.052
  🟢 LSTM           +0.412
  🟢 TFT            +0.185
  🟡 Genetic        +0.031
  🟢 Ensemble       +0.193

⚠️  RISK METRICS
  Daily Loss:      -0.51%
  Max Drawdown:    -5.23%
  Sharpe Ratio:    1.35
  Win Rate:        54.2%
  ✅ Circuit Breaker: NORMAL

💰 OPEN POSITIONS
  🟢 XAUUSD    Qty:   0.50 Entry: $2045.00 Current: $2062.50 P&L: $875.00

💻 SYSTEM HEALTH
  Database:        ✅
  Cache:           ✅
  Data Feed:       ✅
  API Server:      ✅

================================================================================
⏱️  Auto-refresh in 5s (Press Ctrl+C to stop)
================================================================================
```

---

## 🌐 Web UI Monitoring

Access real-time metrics through the REST API:

```bash
# All metrics as JSON (easy for custom web dashboards)
curl http://localhost:8000/paper-trading/status | python -m json.tool

# Subscribe to WebSocket for real-time updates
python -c "
import asyncio
import websockets
import json

async def monitor():
    async with websockets.connect('ws://localhost:8000/paper-trading/stream') as ws:
        while True:
            data = await ws.recv()
            metrics = json.loads(data)
            print(f'Portfolio: \${metrics[\"portfolio_value\"]:,.2f}')
            print(f'P&L: \${metrics[\"daily_pnl\"]:+,.2f}')
            print('---')

asyncio.run(monitor())
"
```

---

## 📊 Prometheus Metrics

### Available Metrics

```
# Trading metrics
trading_portfolio_value              # Current portfolio value
trading_daily_return_percent         # Daily return percentage
trading_sharpe_ratio                 # Sharpe ratio
trading_win_rate                     # Win rate percentage
trading_max_drawdown                 # Max drawdown percentage
trading_open_positions_count         # Number of open positions
trading_total_trades                 # Total trades executed

# Model metrics
model_signal_wavelet                 # Wavelet model signal
model_signal_hmm                     # HMM model signal
model_signal_lstm                    # LSTM model signal
model_signal_tft                     # TFT model signal
model_signal_genetic                 # Genetic algorithm signal
model_signal_ensemble                # Ensemble signal

# Risk metrics
risk_daily_loss_percent              # Daily loss percentage
risk_max_drawdown_percent            # Max drawdown percentage
risk_circuit_breaker_status          # Circuit breaker status (0=normal, 1=yellow, 2=red)

# System metrics
system_health_score                  # Overall system health (0-100)
system_database_latency_ms           # Database query latency
system_data_feed_latency_ms          # Data feed latency
system_uptime_seconds                # System uptime
```

### Query Examples

```bash
# Get current portfolio value
curl 'http://localhost:9090/api/v1/query?query=trading_portfolio_value'

# Get Sharpe ratio over last 24 hours
curl 'http://localhost:9090/api/v1/query_range?query=trading_sharpe_ratio&start=now-24h&end=now&step=5m'

# Get average portfolio value
curl 'http://localhost:9090/api/v1/query?query=avg(trading_portfolio_value)'

# Get 99th percentile latency
curl 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.99, system_database_latency_ms)'
```

---

## 🔔 Real-Time Alerts

### Email Alerts

```python
# Configure in src/infrastructure/health_monitor.py

import smtplib
from email.mime.text import MIMEText

class AlertManager:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = "your_email@gmail.com"
        self.sender_password = "your_app_password"  # App-specific password
        self.recipient_emails = [
            "you@gmail.com",
            "backup@gmail.com"
        ]
    
    def send_alert(self, subject, message, severity="WARNING"):
        """Send alert email"""
        try:
            msg = MIMEText(f"[{severity}] {message}")
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipient_emails)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            print(f"✅ Alert sent: {subject}")
        except Exception as e:
            print(f"❌ Failed to send alert: {e}")
    
    def alert_daily_loss_limit(self, daily_loss):
        """Alert when daily loss limit hit"""
        self.send_alert(
            "🚨 GOLD TRADING: Daily Loss Limit Hit",
            f"Daily loss: {daily_loss:.2f}%\n\n"
            f"Circuit breaker activated. Trading halted.",
            severity="CRITICAL"
        )
    
    def alert_max_drawdown(self, max_drawdown):
        """Alert when max drawdown exceeded"""
        self.send_alert(
            "🚨 GOLD TRADING: Max Drawdown Exceeded",
            f"Max drawdown: {max_drawdown:.2f}%\n\n"
            f"All positions liquidated. Manual intervention required.",
            severity="CRITICAL"
        )
    
    def alert_model_disagreement(self, std_dev):
        """Alert when models disagree"""
        self.send_alert(
            "⚠️  GOLD TRADING: Model Disagreement",
            f"Signal std dev: {std_dev:.3f}\n\n"
            f"Position sizes reduced by 50%.",
            severity="WARNING"
        )
    
    def alert_system_down(self, error):
        """Alert when system fails"""
        self.send_alert(
            "🚨 GOLD TRADING: System Down",
            f"Error: {error}\n\n"
            f"Immediate manual intervention required.",
            severity="CRITICAL"
        )
```

### Slack Alerts

```python
# Configure Slack webhook

import requests

class SlackAlertManager:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
    
    def send_alert(self, title, message, severity="warning", fields=None):
        """Send Slack alert"""
        color = {
            "critical": "#FF0000",
            "warning": "#FFA500",
            "info": "#0099FF"
        }.get(severity, "#0099FF")
        
        payload = {
            "attachments": [{
                "color": color,
                "title": f"🚀 {title}",
                "text": message,
                "fields": fields or [],
                "footer": "Gold Trading System",
                "ts": int(time.time())
            }]
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload)
            if response.status_code == 200:
                print(f"✅ Slack alert sent")
        except Exception as e:
            print(f"❌ Failed to send Slack alert: {e}")
    
    def alert_trade_executed(self, trade):
        """Alert on trade execution"""
        self.send_alert(
            "Trade Executed",
            f"New position opened in {trade['symbol']}",
            fields=[
                {"title": "Side", "value": trade['side'], "short": True},
                {"title": "Quantity", "value": str(trade['quantity']), "short": True},
                {"title": "Entry Price", "value": f"${trade['entry_price']:.2f}", "short": True},
                {"title": "Position Size", "value": f"${trade['position_size']:,.2f}", "short": True},
            ],
            severity="info"
        )
```

---

## 📈 Performance Analytics

### Daily Report

```bash
# Generate daily analytics
curl http://localhost:8000/paper-trading/daily-report | python -m json.tool

# Example output:
{
  "date": "2026-05-14",
  "portfolio": {
    "opening_value": 100000.00,
    "closing_value": 105250.50,
    "daily_return_pct": 5.25,
    "daily_pnl": 5250.50
  },
  "trades": {
    "total": 8,
    "winning": 5,
    "losing": 3,
    "win_rate": 62.5,
    "avg_win": 1250.00,
    "avg_loss": -835.00,
    "profit_factor": 1.89
  },
  "models": {
    "wavelet": {"accuracy": 58.2, "avg_return": 0.45},
    "hmm": {"accuracy": 52.1, "avg_return": 0.32},
    "lstm": {"accuracy": 64.3, "avg_return": 0.68},
    "tft": {"accuracy": 59.8, "avg_return": 0.52},
    "genetic": {"accuracy": 48.5, "avg_return": 0.18},
    "ensemble": {"accuracy": 63.1, "avg_return": 0.65}
  },
  "risk": {
    "sharpe_ratio": 1.35,
    "max_drawdown": -5.23,
    "drawdown_recovery_time": "4 hours",
    "consecutive_losses": 1
  }
}
```

### Weekly Report

```python
# Generate weekly analytics
from src.models.performance_monitor import PerformanceMonitor

monitor = PerformanceMonitor()
report = monitor.generate_weekly_report()

# Report includes:
# - Weekly P&L and returns
# - Model performance comparison
# - Best/worst trading days
# - Risk metrics trends
# - Recommendations for next week
```

---

## 📱 Mobile Monitoring

### Option 1: Grafana Mobile App

```bash
# Download from:
# iPhone: App Store - "Grafana"
# Android: Google Play - "Grafana"

# Login with your Grafana credentials
# Select "Gold Trading Live" dashboard
# View all metrics on mobile
```

### Option 2: REST API via Mobile Web

```html
<!-- Create simple mobile HTML dashboard -->
<!-- File: dashboard.html -->

<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gold Trading - Mobile</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 10px;
            background: #f0f0f0;
        }
        .card {
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
        }
        .value {
            font-weight: bold;
            font-size: 18px;
        }
        .positive { color: green; }
        .negative { color: red; }
        .status {
            text-align: center;
            font-size: 24px;
            padding: 20px;
        }
        .refresh { text-align: center; color: #999; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>🚀 Gold Trading</h1>
    
    <div class="card">
        <h2>Portfolio</h2>
        <div class="metric">
            <span>Total Value:</span>
            <span class="value" id="portfolio">$0.00</span>
        </div>
        <div class="metric">
            <span>Daily P&L:</span>
            <span class="value positive" id="daily_pnl">+$0.00</span>
        </div>
    </div>
    
    <div class="card">
        <h2>Signals</h2>
        <div id="signals"></div>
    </div>
    
    <div class="card">
        <h2>Risk</h2>
        <div class="metric">
            <span>Sharpe Ratio:</span>
            <span class="value" id="sharpe">0.00</span>
        </div>
        <div class="metric">
            <span>Max Drawdown:</span>
            <span class="value negative" id="drawdown">0.00%</span>
        </div>
        <div class="metric">
            <span>Win Rate:</span>
            <span class="value" id="win_rate">0%</span>
        </div>
    </div>
    
    <div class="card">
        <div class="status" id="status">✅ Running</div>
    </div>
    
    <div class="refresh">
        <p>Last updated: <span id="timestamp">--:--:--</span></p>
        <p>Auto-refresh: every 10 seconds</p>
    </div>
    
    <script>
        async function fetchMetrics() {
            try {
                const response = await fetch('http://localhost:8000/paper-trading/status');
                const data = await response.json();
                
                // Update portfolio
                document.getElementById('portfolio').textContent = 
                    '$' + data.portfolio.total_value.toFixed(2);
                
                // Update daily P&L
                const dailyPnL = data.daily_pnl || 0;
                document.getElementById('daily_pnl').textContent = 
                    (dailyPnL >= 0 ? '+' : '') + '$' + dailyPnL.toFixed(2);
                document.getElementById('daily_pnl').className = 
                    'value ' + (dailyPnL >= 0 ? 'positive' : 'negative');
                
                // Update timestamp
                document.getElementById('timestamp').textContent = 
                    new Date().toLocaleTimeString();
                
            } catch (error) {
                console.error('Error fetching metrics:', error);
            }
        }
        
        // Fetch on load and then every 10 seconds
        fetchMetrics();
        setInterval(fetchMetrics, 10000);
    </script>
</body>
</html>
```

---

## 🎯 Dashboard Best Practices

1. **Refresh Rate**
   - Live trading: 15-30 seconds
   - Paper trading: 5 minutes
   - Don't refresh faster than necessary (saves resources)

2. **Metrics to Monitor**
   - Primary: Portfolio value, daily P&L, Sharpe ratio
   - Secondary: Open positions, model signals
   - Tertiary: System health, alerts

3. **Alerts Should Trigger**
   - Daily loss > 2%
   - Max drawdown > 15%
   - System health < 60%
   - Data feed offline > 5 minutes
   - Model disagreement > 0.4

4. **Mobile Optimization**
   - Use Grafana mobile app
   - Keep dashboards simple
   - Focus on key metrics
   - Large fonts for easy reading

5. **Performance Optimization**
   - Limit time range on dashboards
   - Use sampling for historical data
   - Cache frequently used queries
   - Archive old data

---

**Your live trading dashboard is now complete and ready to monitor your gold trading system in real-time! 📊✨**


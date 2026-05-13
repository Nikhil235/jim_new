# Phase 6: Paper Trading & Live Deployment
> *Start small. Build a "Gold Printing Press" — a billion tiny profitable bites.*

**Duration**: Weeks 14–18 | **Status**: 🔴 Not Started

**Framework**: 
- ✅ Execution engine skeleton (`src/execution/engine.py`)
- ✅ Paper trading mode in main.py
- 🔴 Full paper trading simulator not yet implemented
- 🔴 Broker API integration incomplete

**Awaiting**: Phase 5 backtested models to deploy

---

## 6.1 Paper Trading (4 weeks minimum)

### Setup
- Deploy full system connected to LIVE market data
- Execute all signals in a simulated portfolio
- Log every signal, order, fill, and P&L as if it were real money

### Daily Monitoring Checklist
- [ ] Signal count within expected range?
- [ ] Execution latency acceptable?
- [ ] P&L tracking matches expected Sharpe?
- [ ] Risk metrics (VaR, DD) within bounds?
- [ ] Data feeds stable, no gaps?
- [ ] Model predictions consistent with backtest behavior?

### Pass Criteria to Go Live
| Metric | Requirement |
|--------|-------------|
| Live Sharpe vs Backtest Sharpe | Within 20% |
| Max Drawdown | < 8% |
| System uptime | > 99.5% |
| Data feed reliability | > 99.9% |
| Signal-to-execution latency | < 200ms |
| No critical bugs | 0 in final 2 weeks |

---

## 6.2 Live Deployment Stages

| Stage | Capital | Duration | Go/No-Go |
|-------|---------|----------|----------|
| **Alpha** | $10,000 | 2 weeks | Positive P&L, no system errors |
| **Beta** | $50,000 | 4 weeks | Sharpe > 1.5, Max DD < 5% |
| **Gamma** | $200,000 | 4 weeks | Consistent with Beta metrics |
| **Production** | Full allocation | Ongoing | Continuous monitoring |

**Scaling Rule**: Only advance to next stage if ALL metrics pass. One failure = stay at current stage or retreat.

---

## 6.3 Broker & Execution

| Component | Primary | Backup |
|-----------|---------|--------|
| Broker | Interactive Brokers (IBKR) | Direct CME via CQG |
| API | IBKR TWS API | FIX Protocol |
| Execution Algo | Custom TWAP | VWAP for large orders |
| Order Types | Limit orders only | No market orders ever |

### Execution Quality Metrics
- **Slippage**: Track actual vs expected fill price
- **Fill Rate**: Percentage of orders fully filled
- **Latency**: Signal → Order → Fill timestamps
- **Cost**: Commission + spread cost per trade

---

## 6.4 System Architecture (Production)

```
┌──────────────────────────────────────────────────┐
│                 PRODUCTION STACK                  │
├──────────────────────────────────────────────────┤
│                                                   │
│  [Live Data Feeds] ──► [Kafka] ──► [Feature Eng] │
│                                        │          │
│                                        ▼          │
│                               [Model Ensemble]    │
│                                        │          │
│                                        ▼          │
│                               [Meta-Label Critic] │
│                                        │          │
│                                        ▼          │
│                               [Risk Manager]      │
│                                        │          │
│                                        ▼          │
│                               [Kelly Sizer]       │
│                                        │          │
│                                        ▼          │
│                           [Execution Engine (C++)]│
│                                        │          │
│                                        ▼          │
│                               [Broker API]        │
│                                                   │
│  [Monitoring] ◄── Grafana + Prometheus + Alerts   │
│  [Logging]    ◄── ELK Stack (every event)         │
│  [Backup]     ◄── Auto-failover to secondary      │
│                                                   │
└──────────────────────────────────────────────────┘
```

---

## 6.5 Disaster Recovery

| Scenario | Response |
|----------|----------|
| Primary server fails | Auto-failover to backup within 30s |
| Data feed dies | Switch to backup feed, pause new entries |
| Broker API down | Queue orders, close positions via phone |
| Model produces NaN | Circuit breaker, flatten all positions |
| Internet outage | Co-located backup at broker's datacenter |

---

## 6.6 Deliverables Checklist

- [ ] Paper trading system deployed and running
- [ ] 4-week paper trading completed with passing metrics
- [ ] Live vs backtest comparison report
- [ ] Broker API integration tested (IBKR)
- [ ] Execution quality monitoring built
- [ ] Alpha stage ($10K) deployed
- [ ] Beta stage ($50K) deployed
- [ ] Gamma stage ($200K) deployed
- [ ] Disaster recovery tested
- [ ] Production deployment (full allocation)

---

*Back to [ROADMAP](../ROADMAP.md) | Next: [Phase 7](PHASE_7_CULTURE.md)*

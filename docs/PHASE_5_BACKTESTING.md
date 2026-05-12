# Phase 5: Backtesting & Validation
> *A model that looks perfect on past data is a "ghost." Guard against overfitting.*

**Duration**: Weeks 10–14 | **Status**: 🔴 Not Started

---

## 5.1 Anti-Overfitting Protocol

This is where most quant projects DIE. A strategy that returns 500% in backtest but fails live is worthless. We use Marcos López de Prado's rigorous framework.

### The Three Deadly Sins of Backtesting

| Sin | What It Is | Our Defense |
|-----|-----------|-------------|
| **Lookahead Bias** | Using future data in past decisions | Strict event-driven backtester with no future leakage |
| **Survivorship Bias** | Only testing on data that "survived" | Use complete historical datasets including delistings |
| **Overfitting** | Fitting noise instead of signal | Walk-forward + CPCV + Deflated Sharpe |

### Walk-Forward Analysis

```
Year:  2014  2015  2016  2017  2018  2019  2020  2021  2022  2023

Run 1: [===TRAIN===]  [TEST]
Run 2:       [===TRAIN===]  [TEST]
Run 3:             [===TRAIN===]  [TEST]
Run 4:                   [===TRAIN===]  [TEST]
Run 5:                         [===TRAIN===]  [TEST]
Run 6:                               [===TRAIN===]  [TEST]

Each TEST period is NEVER seen during training.
Final metric = AVERAGE across all test periods.
```

### Combinatorial Purged Cross-Validation (CPCV)

Unlike standard k-fold (which leaks time-series info), CPCV:
- Creates all possible train/test combinations
- **Purges** observations near the train/test boundary
- **Embargoes** a buffer period after each test fold
- Prevents autocorrelation leakage

### Deflated Sharpe Ratio (DSR)

```
DSR adjusts the Sharpe Ratio for:
  - Number of strategies tested (multiple testing bias)
  - Non-normal returns (skewness, kurtosis)
  - Length of backtest

If you tested 1,000 strategies and found one with Sharpe 2.0,
the DSR tells you if that 2.0 is REAL or just luck.

Rule: Only deploy if DSR p-value < 0.05
```

### White's Reality Check

Statistical bootstrap test confirming the best strategy's performance is NOT due to data-snooping across all tested strategies.

---

## 5.2 Backtester Architecture

```
┌─────────────────────────────────────────┐
│         EVENT-DRIVEN BACKTESTER         │
├─────────────────────────────────────────┤
│                                          │
│  [Historical Data Feed]                  │
│       │                                  │
│       ▼                                  │
│  [Event Queue] ← MarketEvent            │
│       │           SignalEvent            │
│       │           OrderEvent             │
│       │           FillEvent              │
│       ▼                                  │
│  [Strategy] → generates SignalEvent      │
│       │                                  │
│       ▼                                  │
│  [Risk Manager] → validates/rejects      │
│       │                                  │
│       ▼                                  │
│  [Execution Simulator]                   │
│       │  - Realistic slippage model      │
│       │  - Commission model              │
│       │  - Latency simulation            │
│       ▼                                  │
│  [Portfolio Tracker]                     │
│       │                                  │
│       ▼                                  │
│  [Performance Analytics]                 │
│                                          │
└─────────────────────────────────────────┘
```

**Key**: The backtester must simulate REAL execution conditions:
- Slippage based on historical spread data
- Commission per trade (broker-specific)
- Latency between signal and fill (50ms–500ms)
- Partial fills on large orders

---

## 5.3 Performance Metrics & Targets

| Metric | Formula | Target | Kill Threshold |
|--------|---------|--------|---------------|
| **Sharpe Ratio** | (Return - Rf) / StdDev | > 2.0 | < 1.0 |
| **Sortino Ratio** | (Return - Rf) / DownsideDev | > 3.0 | < 1.5 |
| **Max Drawdown** | Peak-to-trough | < 10% | > 15% |
| **Win Rate** | Winning trades / Total | > 51% | < 48% |
| **Profit Factor** | Gross profit / Gross loss | > 1.5 | < 1.1 |
| **Calmar Ratio** | Annual return / Max DD | > 2.0 | < 1.0 |
| **Avg Trade Duration** | Mean holding period | < 4 hours | > 2 days |
| **Trades per Day** | Count | > 10 | < 3 |
| **DSR p-value** | Deflated Sharpe | < 0.05 | > 0.10 |

**Kill Threshold** = if ANY metric hits this, the strategy is rejected.

---

## 5.4 Reporting Template

Every backtest produces a standardized report:

```markdown
## Backtest Report: [Strategy Name] v[Version]
### Date: [YYYY-MM-DD]

**Data Period**: [Start] to [End]
**Out-of-Sample**: [Start] to [End]

### Performance Summary
| Metric        | In-Sample | Out-of-Sample |
|---------------|-----------|---------------|
| Sharpe        |           |               |
| Max Drawdown  |           |               |
| Win Rate      |           |               |
| Profit Factor |           |               |
| DSR p-value   |           |               |

### Equity Curve: [chart]
### Monthly Returns Heatmap: [chart]
### Drawdown Chart: [chart]
### Regime Performance: [table by HMM regime]

### Verdict: PASS / FAIL / NEEDS REVIEW
```

---

## 5.5 Deliverables Checklist

- [ ] Event-driven backtester with realistic execution sim
- [ ] Walk-forward analysis framework
- [ ] CPCV implementation
- [ ] Deflated Sharpe Ratio calculator
- [ ] White's Reality Check implementation
- [ ] Slippage & commission models calibrated
- [ ] Standardized backtest report generator
- [ ] All strategies pass out-of-sample validation
- [ ] Performance dashboard built (Grafana)

---

*Back to [ROADMAP](../ROADMAP.md) | Next: [Phase 6](PHASE_6_DEPLOYMENT.md)*

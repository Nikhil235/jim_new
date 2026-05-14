# Phase 5: Backtesting & Validation - Implementation Plan
**Date**: May 13, 2026  
**Status**: Kickoff  
**Duration**: Weeks 10–14 (2–3 weeks to completion)  
**Overall Project Completion**: ~90% → ~95%

---

## 🎯 Objectives

1. **Build rigorous, anti-overfitting backtester** inspired by Marcos López de Prado's framework
2. **Validate all Phase 3 models** (Wavelet, HMM, LSTM, TFT, Genetic Algorithm, Ensemble)
3. **Ensure production readiness** with realistic execution simulation
4. **Generate statistical evidence** that strategies are NOT due to data-snooping
5. **Establish performance baselines** before live trading

---

## 📋 Architecture Overview

```
Phase 5: Backtesting & Validation
├── Core Backtester (Event-Driven)
│   ├── Event Queue (MarketEvent, SignalEvent, OrderEvent, FillEvent)
│   ├── Historical Data Feed Handler
│   ├── Execution Simulator (slippage, commission, latency)
│   └── Portfolio Tracker
├── Validation Framework
│   ├── Walk-Forward Analysis
│   ├── Combinatorial Purged Cross-Validation (CPCV)
│   ├── Deflated Sharpe Ratio (DSR) Calculator
│   └── White's Reality Check
├── Reporting & Analytics
│   ├── Backtest Report Generator
│   ├── Performance Dashboard (Grafana)
│   └── Regime-based Performance Analysis
└── Testing & CI/CD
    ├── Unit tests (event queue, execution sim)
    ├── Integration tests (full backtest workflows)
    └── End-to-end strategy validation
```

---

## 📦 Deliverables by Week

### Week 1: Core Backtester (This Week)

**Milestone 1.1: Event-Driven Backtester**
- [ ] Create `src/backtesting/events.py` - Event dataclasses (Market, Signal, Order, Fill)
- [ ] Create `src/backtesting/data_handler.py` - Historical data feed from QuestDB
- [ ] Create `src/backtesting/execution.py` - Realistic execution simulator
  - Slippage model (bid-ask spread based)
  - Commission model (per-trade + % basis)
  - Latency simulation (50–500ms)
- [ ] Create `src/backtesting/portfolio.py` - Portfolio state tracking
- [ ] Create `src/backtesting/backtester.py` - Main event loop orchestrator

**Milestone 1.2: Testing Framework**
- [ ] Create `tests/test_backtester_core.py` - Unit tests for events, data, execution
- [ ] Create `tests/test_execution_simulator.py` - Slippage & commission validation

**Target**: ~600 lines of production code, ~400 lines of tests

---

### Week 2: Validation Framework

**Milestone 2.1: Statistical Validators**
- [ ] Create `src/backtesting/walk_forward.py` - Walk-forward analysis (train/test splits)
- [ ] Create `src/backtesting/cpcv.py` - Combinatorial Purged Cross-Validation
- [ ] Create `src/backtesting/deflated_sharpe.py` - DSR calculator with p-value
- [ ] Create `src/backtesting/white_reality_check.py` - Bootstrap hypothesis test

**Milestone 2.2: Reporting**
- [ ] Create `src/backtesting/report_generator.py` - Standardized backtest reports
- [ ] Create `src/backtesting/metrics.py` - Sharpe, Sortino, Calmar, profit factor, win rate
- [ ] Create `src/backtesting/plotting.py` - Equity curves, drawdown, monthly heatmaps

**Milestone 2.3: Testing**
- [ ] Create `tests/test_validation_framework.py` - Walk-forward, CPCV, DSR tests
- [ ] Create `tests/test_backtesting_integration.py` - End-to-end backtest workflows

**Target**: ~700 lines of production code, ~500 lines of tests

---

### Week 3: Strategy Validation & Optimization

**Milestone 3.1: Run Backtests**
- [ ] Backtest all Phase 3 models (Wavelet, HMM, LSTM, TFT, Genetic, Ensemble)
- [ ] Generate baseline performance metrics
- [ ] Run walk-forward analysis on best models
- [ ] Calculate DSR p-values and validate

**Milestone 3.2: Performance Tuning**
- [ ] Identify underperforming models/parameters
- [ ] Fine-tune execution costs, Kelly fraction
- [ ] Run sensitivity analysis (spread, commission, latency)

**Milestone 3.3: Final Documentation**
- [ ] Generate performance reports for each strategy
- [ ] Update PROJECT_STATUS.md
- [ ] Create Phase 5 completion summary

**Target**: 5–10 complete backtest reports with DSR validation

---

## 🗂️ File Structure (New)

```
src/backtesting/
├── __init__.py
├── events.py            # Event dataclasses
├── data_handler.py      # QuestDB historical data feed
├── execution.py         # Realistic execution simulator
├── portfolio.py         # Portfolio state tracking
├── backtester.py        # Main event loop
├── walk_forward.py      # Walk-forward analysis
├── cpcv.py             # Combinatorial purged CV
├── deflated_sharpe.py  # DSR calculator
├── white_reality_check.py # Bootstrap test
├── metrics.py          # Performance metrics
├── report_generator.py # Report generation
└── plotting.py         # Visualization helpers

tests/
├── test_backtester_core.py           # Event loop unit tests
├── test_execution_simulator.py       # Slippage & commission tests
├── test_validation_framework.py      # Walk-forward, CPCV, DSR
└── test_backtesting_integration.py   # Full workflow integration

docs/
└── PHASE_5_BACKTESTING_COMPLETE.md   # Full technical report
```

---

## 📊 Success Criteria

### Backtester Quality
- ✅ Zero lookahead bias (event-driven, time-ordered processing)
- ✅ Realistic execution (slippage, commission, latency calibrated to real data)
- ✅ All major market events simulated correctly

### Statistical Rigor
- ✅ All models pass walk-forward validation
- ✅ Out-of-sample performance within 10% of in-sample
- ✅ DSR p-value < 0.05 for all deployment candidates

### Performance Targets
- ✅ Best model Sharpe > 2.0 (in-sample and out-of-sample)
- ✅ Max drawdown < 10%
- ✅ Win rate > 51%
- ✅ Profit factor > 1.5
- ✅ Avg trade duration < 4 hours

### Testing & Documentation
- ✅ 80+ tests for backtesting framework
- ✅ 100% code coverage for core backtester
- ✅ Full backtest reports for each strategy

---

## 💡 Key Implementation Notes

### Event-Driven Design (Critical)
- Process events in strict chronological order
- NO peeking at future data (prevents lookahead bias)
- Clean separation between market feed, signals, and execution

### Realistic Execution Simulation
- **Slippage**: Model based on historical bid-ask spreads
- **Commission**: Broker-specific (assume $1–2 per trade for gold futures)
- **Latency**: Simulate 100–500ms delay between signal and fill

### Anti-Overfitting Validation
- Walk-forward: Test on data NEVER seen during training
- CPCV: Prevent time-series leakage across fold boundaries
- DSR: Account for multiple testing bias (correct p-values)

### Performance Reporting
- Separate in-sample vs. out-of-sample metrics
- Regime-based analysis (NORMAL, GROWTH, CRISIS)
- Monthly returns heatmap for regime detection

---

## 🚀 Go Live Criteria (Phase 6)

Once Phase 5 is complete:
1. All models pass DSR validation (p < 0.05)
2. Out-of-sample Sharpe > 1.5 for deployment candidate
3. Max drawdown < 10% in worst case scenario
4. Ready for Phase 6: Paper Trading & Deployment

---

## 📅 Timeline

| Week | Milestone | Owner | Status |
|------|-----------|-------|--------|
| Week 1 | Core backtester + events | Copilot | 🔴 Not Started |
| Week 2 | Validation framework + reporting | Copilot | 🔴 Not Started |
| Week 3 | Strategy validation + tuning | Copilot | 🔴 Not Started |

**Target Completion**: May 27, 2026 (End of Week 3)

---

## 📚 References

- Marcos López de Prado. *Advances in Financial Machine Learning*, Chapter 11–14
- Deflated Sharpe Ratio: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- Walk-Forward Analysis: Standard practice in quantitative finance
- White's Reality Check: White (2000), "A Reality Check for Data Snooping"

---

*Next: [Phase 5 Progress Tracking](PHASE_5_PROGRESS_TRACKING.md)*

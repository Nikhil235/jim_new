# Phase 4: Risk Management & Meta-Labeling
> *The "Critic" that watches the "Trader"*

**Duration**: Weeks 8–12 | **Status**: 🔴 Not Started

---

## 4.1 Meta-Labeling (Two-Model System)

The core Simons insight: don't just predict direction — predict your OWN accuracy.

```
Model 1: "The Trader"              Model 2: "The Critic"
┌─────────────────────┐            ┌─────────────────────┐
│ Predicts: BUY/SELL  │──signal──►│ Predicts: Probability│
│                     │            │ that Model 1 is RIGHT│
└─────────────────────┘            └──────────┬──────────┘
                                              │
                                   Confidence > 65%?
                                      │           │
                                     YES          NO
                                      │           │
                                   EXECUTE     SKIP TRADE
```

**Model 2 Inputs**:
- Model 1's raw signal + confidence
- Current regime (from HMM)
- Current volatility vs historical
- Time of day / day of week
- Spread width (liquidity proxy)
- Recent model 1 accuracy (rolling window)

**Implementation**:
```python
class MetaLabeler:
    def __init__(self, threshold=0.65):
        self.critic = XGBClassifier()
        self.threshold = threshold
    
    def should_trade(self, trader_signal, market_features):
        critic_input = np.concatenate([trader_signal, market_features])
        confidence = self.critic.predict_proba(critic_input)[0][1]
        return confidence > self.threshold, confidence
```

---

## 4.2 GPU Monte Carlo Simulations

Run **100,000 scenarios per hour** to know your risk at all times.

**Stress Scenarios**:
| Scenario | Shock | Expected Gold Impact |
|----------|-------|---------------------|
| USD Flash Rally | DXY +3% in 1 hour | Gold -2.5% to -4% |
| Liquidity Crisis | Spread 5x normal | Slippage explosion |
| Flash Crash | Gold -5% in 5 min | Circuit breaker test |
| Rate Surprise | Fed +50bps unexpected | Gold -3% to +2% |
| Geopolitical Event | VIX spike to 40+ | Gold +3% to +8% |

**Output Metrics** (computed every hour):
- **VaR (95%)**: Max expected loss in 95% of scenarios
- **CVaR (99%)**: Average loss in worst 1% of scenarios
- **Max Drawdown Distribution**: Histogram of possible drawdowns

```python
import cupy as cp

def gpu_monte_carlo(current_position, returns_dist, n_sims=100000):
    # Generate random scenarios on GPU
    scenarios = cp.random.multivariate_normal(
        mean=returns_dist.mean, cov=returns_dist.cov, size=n_sims
    )
    pnl = current_position @ scenarios.T
    var_95 = float(cp.percentile(pnl, 5))
    cvar_99 = float(cp.mean(pnl[pnl <= cp.percentile(pnl, 1)]))
    return var_95, cvar_99
```

---

## 4.3 Dynamic Kelly Criterion

```
f* = (p × b - q) / b

Where:
  f* = fraction of capital to bet
  p  = probability of winning (from Meta-Label Critic)
  b  = win/loss ratio (from rolling backtest stats)
  q  = 1 - p
```

**Safety Rules**:
- Use **Half-Kelly** (f*/2) — full Kelly is too aggressive
- **Hard cap**: Max 5% of portfolio per position regardless
- **Regime adjustment**: In Crisis regime, use Quarter-Kelly
- Recalculate every trade using latest Critic confidence

---

## 4.4 Circuit Breakers

| Trigger | Action | Auto-Reset |
|---------|--------|------------|
| Daily loss > 2% | Halt trading 24 hours | Next trading day |
| Drawdown > 5% from peak | Reduce size by 50% | When DD recovers to 3% |
| Drawdown > 10% from peak | STOP all trading | Manual review only |
| Model disagreement > 70% | Minimum position only | When agreement > 50% |
| Data feed latency > 500ms | Close all positions | When latency normalizes |
| Spread > 3x normal | Pause new entries | When spread normalizes |
| 3 consecutive losses > 1% | Reduce size by 25% | After 2 profitable trades |

---

## 4.5 Position Management

```
┌─────────────────────────────────────────┐
│           POSITION LIFECYCLE            │
├─────────────────────────────────────────┤
│                                          │
│  Signal Generated                        │
│      │                                   │
│      ▼                                   │
│  Meta-Label Check (Critic > 65%?)        │
│      │                                   │
│      ▼                                   │
│  Kelly Sizing (Half-Kelly, max 5%)       │
│      │                                   │
│      ▼                                   │
│  Risk Check (VaR budget available?)      │
│      │                                   │
│      ▼                                   │
│  EXECUTE (TWAP/VWAP for larger orders)   │
│      │                                   │
│      ▼                                   │
│  Monitor: Trailing stop + Time stop      │
│      │                                   │
│      ▼                                   │
│  EXIT (signal reversal / stop / target)  │
│                                          │
└─────────────────────────────────────────┘
```

---

## 4.6 Deliverables Checklist

- [ ] Meta-labeling framework built and tested
- [ ] XGBoost Critic model trained
- [ ] GPU Monte Carlo engine (100K sims/hour)
- [ ] Dynamic Kelly Criterion position sizer
- [ ] All circuit breakers implemented and tested
- [ ] Real-time VaR/CVaR dashboard in Grafana
- [ ] Risk reporting automated (daily Slack/email)
- [ ] Position lifecycle manager built

---

*Back to [ROADMAP](../ROADMAP.md) | Next: [Phase 5](PHASE_5_BACKTESTING.md)*

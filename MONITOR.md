# 24-Hour Monitoring Checklist

## Every 2–3 Hours

| Metric | Current | Prior | Δ | OK? |
|--------|---------|-------|---|-----|
| Trade count | | | | |
| Win rate | | | | |
| Avg P&L/trade | | | | |
| Total realized P&L | | | | |
| Max drawdown | | | | |

## Signal Split

| Metric | Current | Prior | Δ | OK? |
|--------|---------|-------|---|-----|
| LONG % | | | | |
| SHORT % | | | | |
| HOLD % | | | | |
| Ensemble conf avg | | | | |
| Ensemble conf med | | | | |
| LOW_CONFIDENCE rejects | | | | |
| HOLD_SIGNAL rejects | | | | |

## Risk Checks

| Metric | Current | Limit | OK? |
|--------|---------|-------|-----|
| Daily loss used | | 5% max | |
| Consecutive loss streak | | 5 max | |
| Cooldown hits | | — | |
| Event-guard hits | | — | |
| Position-limit rejections | | — | |

## Model Health

| Model | LONG | SHORT | HOLD | Avg Conf |
|-------|------|-------|------|----------|
| TFT | | | | |
| Genetic | | | | |
| WaveletBasic | | | | |
| WaveletPro | | | | |
| HMM | | | | |
| HMMPro | | | | |
| LSTM | | | | |

**HMM vs HMMPro disagreement rate:** ___ (target: <60%)

## Good Signs

- Trade count rises, but not too fast
- Win rate stays above 40%
- Avg P&L per trade stays stable or improves
- HOLD rate drops without hurting expectancy
- Confidence rises a little, not dramatically

## Bad Signs

- More trades but worse win rate
- Avg P&L per trade shrinks
- One weak fallback starts dominating
- Drawdown grows too fast
- System trades on noisy disagreement

## End-of-Day Decision

- **Keep settings** if trade frequency and profitability both improve
- **Tighten thresholds slightly** if trade count jumps but quality drops
- **Revert the weakest change** if one model clearly adds noise
- Only change one threshold at a time

## Hard Alert Thresholds

| Alert | Trigger | Action |
|-------|---------|--------|
| Data feed stale | consecutive_failures ≥ 2 | Check yfinance/MetalPriceAPI status |
| Model crashed | model_errors[name] > 5 | Restart the loop, check model code |
| Max drawdown | > 5% from peak | Halt trading, review positions |
| Consecutive losses | > 5 in a row | Reduce position sizing by 50% |
| Ensemble confidence | median < 0.15 over 1hr | Tighten model thresholds |

## Fetch Commands

```powershell
# Trade stats
python -c "from src.models.performance_tracker import get_performance_tracker; t=get_performance_tracker(); print(t.summary())"

# Gate rejection stats
python -c "from src.utils.shared_state import get_gate_stats; print(get_gate_stats())"

# Rejection counts CSV-style
python -c "from src.utils.shared_state import get_gate_stats; s=get_gate_stats(); [print(f'{k}: {v}') for k,v in sorted(s.items())]"

# Ensemble config
python -c "from src.utils.shared_state import state_manager; c=state_manager.get_config(); print(f'rsi={c.rsi_threshold} min_conf={c.min_confidence} min_bars={c.min_bars_between_trades}')"

# System health (data feed, model crashes)
python -c "from src.paper_trading.live_inference import SYSTEM_HEALTH; import json; print(json.dumps({k:str(v) if not isinstance(v,(int,float,bool)) else v for k,v in SYSTEM_HEALTH.items()}, indent=2))"

# Per-model error counts
python -c "from src.paper_trading.live_inference import SYSTEM_HEALTH; [print(f'{m}: {e} errors') for m,e in sorted(SYSTEM_HEALTH['model_errors'].items()) if e > 0]"

# Stale data alert
python -c "from src.paper_trading.live_inference import SYSTEM_HEALTH; print('DATA STALE!' if SYSTEM_HEALTH['data_feed_stale'] else 'Data feed OK')"

# Health endpoint (requires dashboard server running)
# curl http://localhost:8001/controls/health

# Model crash check
python -c "from src.paper_trading.live_inference import SYSTEM_HEALTH; dead=[m for m,c in SYSTEM_HEALTH['model_errors'].items() if c>5]; print(f'Dead models: {dead}') if dead else print('All models healthy')"
```

# How the Ensemble Model Calculates Its Signal

The **Ensemble** is not a single model — it's a **two-layer decision system** (meta-learner). Here's exactly how it works, step by step:

---

## Layer 0 — The 5 "Worker" Models
These all run independently and each gives a vote + confidence score:

| Model | What It Does | Best In |
|-------|-------------|---------|
| **Wavelet** | Filters noise from price data using wave math, detects trend | Any market |
| **HMM** | Detects which "hidden state" (regime) the market is in | Transitions |
| **LSTM** | Deep learning; predicts next move from sequences of past prices | Trending |
| **TFT** | Forecasts multiple steps ahead simultaneously | Growth |
| **Genetic** | Evolves trading rules via natural selection | Any |

Each produces something like: `{signal: "LONG", confidence: 0.82}`

---

## Layer 1 — The Ensemble Combines Them (Two Modes)

### Mode A: ML Meta-Learner (when trained on 50+ historical trades)
If there is enough history, the system uses an XGBoost Classifier:
1. Feature vector → XGBoost → P(LONG), P(HOLD), P(SHORT)
2. Feature vector includes:
  - direction × confidence for each model (signed confidence)
  - raw confidence for each model
  - regime code (GROWTH=+1, NORMAL=0, CRISIS=−1)
  - model agreement score (are they voting the same way?)
  - DXY momentum + bond yield momentum (macro data)

If P(LONG) > 55% → signal = **LONG**. If P(SHORT) > 55% → **SHORT**. Otherwise → **HOLD**.

### Mode B: Dynamic Regime Weighting (the current live mode)
When there's not enough training data, it uses a weighted vote:

1. **Assign regime-based weights**
   - GROWTH: wavelet:25%, hmm:15%, lstm:10%, ensemble:50%
   - NORMAL: wavelet:35%, hmm:25%, lstm:10%, ensemble:30%
   - CRISIS: wavelet:15%, hmm:45%, lstm:0%, ensemble:40%

2. **Performance adaptation (after 10+ trades)**
   - `weight = 60% regime_weight + 40% rolling_sharpe_weight`
   - Models that WON recently get heavier votes.

3. **Agreement bonus/penalty**
   - If ≥4 of 7 models agree → agreeing models get +15% boost.
   - Lone dissenter gets −15% penalty.

4. **Weighted vote**
   - `score["LONG"] += weight[model] × confidence` (for each LONG voter)
   - `score["SHORT"] += weight[model] × confidence` (for each SHORT voter)

5. **Disagreement penalty on final confidence**
   - `disagreement = 1 - max(longVoters, shortVoters) / totalModels`
   - `final_confidence *= (1 - 0.3 × disagreement)`

6. **Output**
   - If `best_score < 0.25` → HOLD. Else → best direction.

---

## Layer 2 — Dynamic Weight Adjustments (Live, Ongoing)

After every closed trade, the `DynamicWeightAdjuster` updates each model's weight for **next time**:

`new_weight = normalize(regime_base × performance_multiplier × agreement_factor)`

The **performance multiplier** is based on rolling Sharpe ratio (last 50 trades):
- A model that's been winning lately → Sharpe goes up → gets more weight
- A model that's been losing → Sharpe goes down → weight shrinks

This is exactly how Renaissance Technologies operates — the models that have been **right recently** are trusted more, and the weights constantly adapt.

---

### In Plain English

> "Every 60 seconds, Wavelet + HMM + LSTM + TFT + Genetic all look at the gold price from their own angle and vote LONG/SHORT/HOLD. The Ensemble collects all the votes, weights them by who has been winning lately and what the current market regime is, applies a penalty if models disagree, and produces one final signal with a confidence score. If confidence > 60%, the paper trading engine executes the trade."

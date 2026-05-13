# Phase 3: Mathematical Modeling
> *Avoid "linear" thinking. Gold is a non-linear, non-stationary asset.*

**Duration**: Weeks 4–10 | **Status**: 🔴 Not Started

---

## 3.0 Overview

This phase implements advanced machine learning models to discover and exploit market patterns:
- **Genetic Algorithm**: Evolve optimal strategy parameters
- **LSTM Networks**: Learn temporal patterns in returns
- **Temporal Fusion Transformer (TFT)**: Multi-horizon forecasting with attention
- **Variational Autoencoders (VAE)**: Anomaly detection in order flow
- **Ensemble Methods**: Combine all models via stacking

**Note**: Phase 2 data pipeline is ✅ complete. Phase 2.5 API is ✅ complete. This phase builds on top of those.

---

## 3.1 Signal Detection: Wavelet Transforms (DWT)

**What**: Decompose gold price into different "frequencies" using Discrete Wavelet Transforms.

**Why**: Unlike Moving Averages (which blur everything), wavelets isolate noise from trend in real-time.

**Goal**: Spot trend reversals BEFORE they appear on standard charts.

```
Gold Price Signal
    │
    ▼
┌──────────────────────────┐
│  Wavelet Decomposition    │
│  (Daubechies db4)         │
├──────────────────────────┤
│  Level 1: Ultra-HF noise  │  ← Remove
│  Level 2: HF noise        │  ← Remove
│  Level 3: Medium freq     │  ← Trading signal
│  Level 4: Low freq trend  │  ← Direction signal
│  Level 5: Structural      │  ← Macro context
└──────────────────────────┘
    │
    ▼
  Reconstruct WITHOUT noise = Clean "true" signal
```

**Implementation**:
- Library: `PyWavelets` + `cuSignal` (GPU-accelerated)
- Wavelet family: **Daubechies-4** (`db4`)
- Decompose to 5 levels
- Remove levels 1–2 for de-noised trend signal
- GPU acceleration via CuPy for real-time processing

**Key Code Pattern**:
```python
import pywt
import numpy as np

def wavelet_denoise(price_series, wavelet='db4', level=5):
    coeffs = pywt.wavedec(price_series, wavelet, level=level)
    # Zero out high-frequency noise (levels 1-2)
    coeffs[1] = np.zeros_like(coeffs[1])  # Detail level 1
    coeffs[2] = np.zeros_like(coeffs[2])  # Detail level 2
    return pywt.waverec(coeffs, wavelet)
```

---

## 3.2 Regime Detection: Hidden Markov Models (HMM)

**What**: Gold behaves differently in Crisis vs Normal vs Growth regimes.

**Why**: A mean-reversion strategy in calm markets will BLOW UP in a crisis.

```
Market States (Latent):
┌──────────┐    ┌──────────┐    ┌──────────┐
│  CRISIS  │◄──►│  NORMAL  │◄──►│  GROWTH  │
│ High Vol │    │ Med Vol  │    │ Low Vol  │
│ Trending │    │ MeanRev  │    │ Range    │
└──────────┘    └──────────┘    └──────────┘
```

**Emission Variables**: Returns, realized vol, DXY correlation, VIX level, TIPS spread

**Implementation**:
```python
from hmmlearn import hmm

model = hmm.GaussianHMM(
    n_components=3,       # 3 regimes
    covariance_type="full",
    n_iter=1000
)
# Features: [returns, volatility, dxy_corr, vix, tips]
model.fit(feature_matrix)
current_regime = model.predict(latest_features)
```

**Strategy per Regime**:
| Regime | Strategy | Position Sizing |
|--------|----------|----------------|
| Crisis (High Vol) | Trend Following | Small, with wide stops |
| Normal (Med Vol) | Mean Reversion | Normal sizing |
| Growth (Low Vol) | Carry/Range | Larger, tight stops |

---

## 3.3 Pattern Discovery: Genetic Algorithms (GA)

**What**: Let the computer EVOLVE optimal trading strategies.

**Why**: Finds non-intuitive formulas you'd never think of — the Simons way.

```
Gen 0: 1,000 random strategies
   ↓ [Backtest ALL on GPU]
   ↓ [Rank by Sharpe Ratio]
Top 100 survive
   ↓ [Crossover + Mutation]
Gen 1: 1,000 new strategies
   ↓ ... repeat 500 generations ...
RESULT: Optimized, non-intuitive strategies
```

**Genome Structure** (what the GA evolves):
```python
genome = {
    'lookback_fast': (5, 200),      # Fast window
    'lookback_slow': (20, 500),     # Slow window
    'volatility_window': (10, 100),
    'entry_threshold': (0.5, 3.0),  # Std deviations
    'exit_threshold': (0.1, 2.0),
    'regime_weight': (0.0, 1.0),    # HMM influence
    'wavelet_level': (2, 5),
    'stop_loss_atr': (1.0, 5.0),
    'take_profit_atr': (1.0, 8.0),
}
```

**Fitness Function**: Sharpe Ratio × √(Trade Count) / Max Drawdown

**Libraries**: `DEAP` for GA, GPU-parallel fitness evaluation

---

## 3.4 Deep Learning Models

| Model | Use Case | Key Details |
|-------|----------|-------------|
| **LSTM** | Tick sequence prediction | 3-layer bidirectional, 128 hidden units |
| **Temporal Fusion Transformer** | Multi-horizon forecast | Attention-based, interpretable |
| **Variational Autoencoder** | Anomaly detection in order flow | Latent space = "normal" behavior |
| **PPO (Reinforcement Learning)** | Dynamic position sizing | Actor-Critic with market env |

### TFT Architecture (Primary Deep Model)
```
Static Covariates (regime, day_of_week)
    │
Variable Selection Network
    │
LSTM Encoder ──► Interpretable Multi-Head Attention ──► Quantile Output
    │                                                      │
Known Future Inputs                              [10%, 50%, 90%]
(calendar, scheduled events)                     prediction intervals
```

---

## 3.5 The Ensemble: Master Model

> *No single model trades alone. Combine them like a committee of scientists.*

```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Wavelet  │ │   HMM    │ │   GA     │ │   TFT    │
│ Signal   │ │ Regime   │ │ Evolved  │ │ Forecast │
└────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
     └──────┬─────┴──────┬─────┘             │
            ▼            ▼                   │
     ┌─────────────────────────┐             │
     │  STACKING META-LEARNER  │◄────────────┘
     │  (XGBoost / LightGBM)   │
     └──────────┬──────────────┘
                ▼
         FINAL SIGNAL: Long / Short / Flat
         + Confidence Score [0-1]
```

**Stacking approach**: Each model outputs a signal → feed all signals as features into XGBoost → final decision.

---

## 3.6 Deliverables Checklist

- [ ] Wavelet de-noising pipeline on GPU (cuSignal)
- [ ] HMM regime detector trained and validated
- [ ] Genetic Algorithm framework running on GPU cluster
- [ ] LSTM model trained on tick data
- [ ] TFT model for multi-horizon forecasting
- [ ] VAE anomaly detector for order flow
- [ ] Ensemble stacking meta-learner
- [ ] All models versioned in MLflow

---

*Back to [ROADMAP](../ROADMAP.md) | Next: [Phase 4](PHASE_4_RISK.md)*

"""
Wavelet Pro Model - Integration & Validation Guide
═════════════════════════════════════════════════════

IMPLEMENTATION SUMMARY
══════════════════════

This guide helps you:
1. Understand Wavelet Pro architecture
2. Integrate it into your trading system
3. Validate each component before going live
4. Compare with the basic Wavelet model
5. Replace the basic model once verified

QUICK START
═══════════

# Import and initialize
from src.models.wavelet_pro import WaveletPro, WaveletProConfig
import pandas as pd

# Create model
wavelet_pro = WaveletPro()

# Train (wavelet models mostly analyze, not learn parameters)
prices_df = pd.DataFrame({"close": [...your prices...]})
wavelet_pro.train(prices_df)

# Generate signal
signal, confidence, reasoning = wavelet_pro.generate_signal(prices)
# Returns: ("LONG"/"SHORT"/"HOLD", 0.0-1.0, explanation)

# Engineer features for external models
features = wavelet_pro.engineer_features(prices_df)  # 30+ features


KEY IMPROVEMENTS OVER BASIC WAVELET
═══════════════════════════════════

1. DECOMPOSITION DEPTH
   Basic:  5 levels (D1-D5, A5)
   Pro:    6 levels (D1-D6, A6) ← Better trend isolation

2. SIGNAL GENERATION
   Basic:  Simple trend slope
   Pro:    Wavelet Oscillator (D3+D4) + trend filter (A6)
           Zero-crossing detection + overbought/oversold conditions

3. FEATURE ENGINEERING
   Basic:  ~5 features (trend, noise level, etc.)
   Pro:    30+ features including:
           - Oscillator statistics (z-score, mean, std)
           - D1-D6 RMS, max, std
           - Energy per level + entropy
           - A6 slope + trend direction
           - Reconstruction error
           - Noise level metrics

4. DENOISING METHOD
   Basic:  Zero-out high-frequency coefficients
   Pro:    Soft thresholding (Donoho-Johnstone) ← Preserves structure

5. VOLATILITY ANALYSIS
   Basic:  Not included
   Pro:    CWT (Continuous Wavelet Transform) with Morlet wavelet
           - Time-frequency power spectrum
           - Cycle detection across scales
           - Dominant frequency tracking

6. NEURAL NETWORK
   Basic:  Not included
   Pro:    Optional WNN with Morlet activation (for prediction)
           - Multi-layer architecture
           - Wavelet-aware activation function
           - ABC optimization for hyperparameters

7. HYPERPARAMETER TUNING
   Basic:  Manual configuration
   Pro:    ABC (Artificial Bee Colony) optimizer
           - Automated search over learning rates, layer sizes, dropout
           - Swarm intelligence (better than grid search)


ARCHITECTURE OVERVIEW
═════════════════════

Data Input (Gold Price Time Series)
         ↓
┌────────────────────────────────────┐
│ PHASE 4: DWT DECOMPOSITION         │
│ - 6-level Daubechies-4 (db4)      │
│ - Output: [A6, D6, D5, D4, D3, D2, D1]
└────────────────────────────────────┘
         ↓
┌────────────────────────────────────┐
│ PHASE 4.5: CWT ANALYSIS            │
│ - Morlet wavelet for volatility    │
│ - Scalogram for time-frequency     │
└────────────────────────────────────┘
         ↓
┌────────────────────────────────────┐
│ PHASE 5: FEATURE ENGINEERING       │
│ - 30+ wavelet-derived features     │
│ - Technical indicators on denoised │
│ - Cross-asset features (DXY, VIX)  │
└────────────────────────────────────┘
         ↓
┌────────────────────────────────────┐
│ PHASE 6: WNN (Optional)            │
│ - Input: 30 features               │
│ - Activation: Morlet wavelet       │
│ - Output: Price prediction         │
└────────────────────────────────────┘
         ↓
┌────────────────────────────────────┐
│ PHASE 8: SIGNAL GENERATION         │
│ - Wavelet Oscillator (D3+D4)       │
│ - Trend Filter (A6 slope)          │
│ - Zero-crossing detection          │
│ - Overbought/Oversold detection    │
│ - Signal Fusion Logic              │
└────────────────────────────────────┘
         ↓
   OUTPUT: Signal + Confidence + Reasoning


DETAILED COMPONENT EXPLANATION
═════════════════════════════════

## 1. DWT (6-Level Decomposition)

Decomposes gold price into frequency bands:

Level | Component | Frequency | Time Scale | Economic Meaning
─────────────────────────────────────────────────────────────
D1    | Noise     | 2-4 bars  | 10-20 min  | Microstructure, tick noise
D2    | Noise     | 4-8 bars  | 20-40 min  | Order flow noise
D3    | Cycle     | 8-16 bars | 40min-2hr  | Intraday cycles
D4    | Cycle     | 16-32 bars| 2-4 hrs    | Mid-term trends
D5    | Trend     | 32-64 bars| 4-8 hrs    | Daily trends
D6    | Trend     | 64-128    | 8-16 hrs   | Weekly trends
A6    | Structure | >128      | >16 hrs    | Long-term trend

WHY 6 LEVELS?
- Removes noise (D1, D2)
- Captures cycles (D3, D4)
- Preserves trend (D5, D6, A6)
- ~2^6 = 64x compression


## 2. Wavelet Oscillator (D3 + D4)

PRIMARY TRADING SIGNAL

Formula: WaveletOsc(t) = D3(t) + D4(t)

This filters:
✓ OUT: High-frequency noise (D1, D2)
✓ OUT: Long-term trend (A6, D5, D6)
✓ IN:  Mid-term cycles (D3, D4)

SIGNAL GENERATION:
- Bullish crossover: Osc crosses above 0 (from negative)
- Bearish crossover: Osc crosses below 0 (from positive)
- Overbought:  Osc > +2σ (reduce position)
- Oversold:    Osc < -2σ (add position)

TREND FILTER (A6):
- Only BUY if A6 slope > 0 (bullish trend)
- Only SELL if A6 slope < 0 (bearish trend)
- This prevents counter-trend trading


## 3. Soft Thresholding Denoising

Donoho-Johnstone Threshold:
λ = σ * √(2 * ln(N))

Where:
- σ = Median Absolute Deviation (robust noise estimate)
- N = Number of samples
- λ = Threshold for each decomposition level

Application:
d̂_j,k = sign(d_j,k) * max(0, |d_j,k| - λ)

Benefits:
✓ Removes noise while preserving structure
✓ Better than hard thresholding (zero-out)
✓ Fewer edge artifacts


## 4. Continuous Wavelet Transform (CWT)

Detects time-frequency volatility patterns:

CWT(a,b) = (1/√a) ∫ x(t) ψ((t-b)/a) dt

Parameters:
- Wavelet: Morlet (complex = phase + magnitude)
- Scales: [2, 4, 8, 16, 32, 64, 128, 256, 512]
- Output: Power spectrum (|CWT|²)

Interpretation:
High power at small scales   → High-freq volatility (noise)
High power at medium scales  → Intraday cycles (tradeable)
High power at large scales   → Long-term trends (context)


## 5. 30+ Engineered Features

WAVELET CORE (15 features):
- wavelet_oscillator (z-score normalized)
- D1-D6 RMS values (noise level)
- D1-D6 Max values (peak magnitude)
- D1-D6 Std dev (variability)
- A6 slope (trend direction)
- A6 MACD (low-freq momentum)

WAVELET STATISTICS (10 features):
- oscillator_mean, oscillator_std
- oscillator_z_score
- noise_level (D1+D2 RMS)
- reconstruction_error
- wavelet_entropy
- energy_per_level (D1-D6)

TECHNICAL INDICATORS (5+ features):
- log_return (on original price)
- RSI on denoised price
- MACD on A6
- ATR on denoised price
- Bollinger Bands on A6

MACRO FEATURES (if included):
- DXY returns
- Real yield changes
- VIX changes
- Correlation with USD


## 6. Wavelet Neural Network (Optional)

If enabled (config.wnn_enabled=True):

ARCHITECTURE:
Input (30 features) → Dense(128) → Morlet → Dropout(0.2)
                  → Dense(64)  → ReLU  → Dropout(0.2)
                  → Dense(32)  → ReLU  → Dropout(0.2)
                  → Dense(1)   → Linear → Output

ACTIVATION FUNCTIONS:
- Morlet: ψ(x) = cos(1.75x) * e^(-x²/2)
  Better for oscillatory price patterns
- ReLU: max(0, x)
  For intermediate layers

OUTPUT:
- Single-step prediction (next bar return)
- Multi-step predictions (1, 5, 10, 20 bars ahead)

TRAINING:
- Loss: Mean Squared Error (MSE)
- Optimizer: Adam (learning rate 0.001)
- Early stopping: Patience=10 epochs


## 7. ABC Optimization (Optional)

For automatic hyperparameter tuning:

PARAMETERS OPTIMIZED:
- Learning rate (1e-4 to 1e-2)
- Number of hidden layers (1-4)
- Neurons per layer (32-256)
- Dropout rate (0.1-0.5)
- Batch size (16-128)

ABC PHASES:
1. Employed Bee: Local search around each solution
2. Onlooker Bee: Probabilistic selection of best solutions
3. Scout Bee: Replace abandoned solutions with random ones

ADVANTAGES:
✓ Better than grid search (fewer evaluations)
✓ Better than random search (exploitative)
✓ Parallelize across bees (GPU acceleration)


INTEGRATION WITH EXISTING SYSTEM
═════════════════════════════════

STEP 1: ADD TO ENSEMBLE

File: src/models/ensemble_stacking.py

Add WaveletPro alongside other models:

```python
from src.models.wavelet_pro import WaveletPro

class EnsembleStack:
    def __init__(self):
        self.models = {
            'wavelet_basic': WaveletDenoiser(),  # Old model
            'wavelet_pro': WaveletPro(),         # New model
            'hmm': HMMRegimeDetector(),
            'lstm': LSTMTemporal(),
            # ... other models
        }

    def predict(self, data):
        # Get signals from all models
        wavelet_pro_sig = self.models['wavelet_pro'].generate_signal(data)
        # ... other models
        # Combine with voting or stacking
```


STEP 2: BACKTESTING

File: src/backtesting/model_strategies.py

Add WaveletProStrategy:

```python
class WaveletProStrategy:
    def __init__(self):
        self.model = WaveletPro()
        self.model.train(historical_data)
    
    def generate_signal(self, current_price_window):
        signal, confidence, reasoning = self.model.generate_signal(current_price_window)
        return {
            'signal': signal,
            'confidence': confidence,
            'model': 'wavelet_pro',
            'reasoning': reasoning,
        }
```


STEP 3: LIVE INFERENCE

File: src/paper_trading/live_inference.py

Add WaveletPro inference:

```python
def run_wavelet_pro(df: pd.DataFrame) -> Dict:
    """Run WaveletPro inference on latest data."""
    wavelet_pro = WaveletPro()
    
    signal, confidence, reasoning = wavelet_pro.generate_signal(
        df['close'].values
    )
    
    return {
        'signal': signal,
        'confidence': confidence,
        'reasoning': reasoning,
    }
```


VALIDATION CHECKLIST
═════════════════════

Before replacing basic Wavelet model, verify:

□ DWT Decomposition
  □ 6-level decomposition works correctly
  □ Reconstruction accuracy >99%
  □ Coefficient sizes reasonable

□ Wavelet Oscillator
  □ D3+D4 computed correctly
  □ Zero-crossings detected
  □ Trend filter (A6) working

□ Denoising
  □ Soft thresholding reduces variance
  □ Donoho-Johnstone threshold computed
  □ Denoised signal correlates with original

□ Feature Engineering
  □ 30+ features generated
  □ No NaN/infinite values
  □ Features normalized/scaled properly

□ Signal Generation
  □ Returns LONG/SHORT/HOLD
  □ Confidence in [0, 1]
  □ Reasoning non-empty

□ Backtesting
  □ Sharpe ratio > 1.5
  □ Win rate > 55%
  □ Max drawdown < 15%
  □ Better than basic Wavelet model

□ Comparison with Basic
  □ Pro agrees with basic model 70%+ of the time
  □ Pro has higher confidence (average)
  □ Pro generates fewer whipsaws (signal changes)


PERFORMANCE TARGETS
═══════════════════

Metric               Target        Notes
────────────────────────────────────────
Wavelet SNR (dB)     > +5 dB        Noise reduction
Decomposition Stable > 0.9 corr     Coefficient consistency
Oscillator Accuracy  > 70%          Zero-crossing near reversals

Trading (Backtest):
Sharpe Ratio         > 1.5          Risk-adjusted returns
Win Rate             > 55%          Trade quality
Max Drawdown         < 15%          Risk control
Profit Factor        > 1.5          Gross profit / loss

vs Basic Wavelet:
Agreement Rate       > 70%          Signal agreement
Improvement          > 10%          In Sharpe or Profit Factor


RUN TESTS
═════════

Execute test suite:

```bash
cd e:\PRO\JIMxNik\jim_new
python -m pytest tests/test_wavelet_pro.py -v

# Expected output:
# test_dwt_6_levels PASSED
# test_soft_thresholding_denoises PASSED
# test_wavelet_oscillator PASSED
# test_cwt_computation PASSED
# test_feature_count PASSED
# test_signal_format PASSED
# ... (30+ tests total)
```


NEXT STEPS
══════════

1. Run comprehensive tests
   → python -m pytest tests/test_wavelet_pro.py -v

2. Backtest WaveletPro on historical data (2015-2026)
   → Compare Sharpe, drawdown, win rate vs basic model

3. Paper trade on live gold prices for 2-4 weeks
   → Monitor signal quality, frequency, consistency

4. Compare with basic Wavelet model
   → If Pro > Basic by ≥10%, proceed to replace

5. Replace in ensemble
   → Update src/models/ensemble_stacking.py
   → Retrain ensemble meta-learner

6. Deploy to live trading (with circuit breakers)
   → Start with 50% of capital allocated to WaveletPro
   → Gradually increase to 100% as confidence grows


DEBUGGING
═════════

If Wavelet Pro underperforms:

1. Check DWT Decomposition
   - Are coefficients reasonable (not too large)?
   - Is A6 trend clear and smooth?
   
2. Check Wavelet Oscillator
   - Does D3+D4 oscillate around zero?
   - Are zero-crossings aligned with price reversals?

3. Check Denoising Quality
   - Is SNR improvement > 5 dB?
   - Are important price structures preserved?

4. Check Signal Generation
   - Are trend filters preventing counter-trend trades?
   - Are overbought/oversold conditions helpful?

5. Check Backtest
   - Is transaction cost realistic (0.10 USD/oz)?
   - Are slippage estimates correct?
   - Is walk-forward validation properly timed?


SUPPORT FEATURES
════════════════

Configuration (WaveletProConfig):
- dwt_wavelet: "db4" (Daubechies-4)
- dwt_levels: 6 (vs 5 in basic)
- denoise_method: "soft" (soft thresholding)
- threshold_method: "donoho" (Donoho-Johnstone)
- cwt_wavelet: "morl" (Morlet for CWT)
- cwt_scales: [2, 4, 8, ..., 512]
- wnn_enabled: False (optional, enable if needed)
- train_abc: False (optional ABC optimization)

Easy to configure:

```python
config = WaveletProConfig(
    dwt_levels=6,
    denoise_method="soft",
    cwt_scales=[2, 4, 8, 16, 32, 64, 128, 256],
    wnn_enabled=True,
    train_abc=True,  # Enable ABC optimization
)
wavelet_pro = WaveletPro(config=config)
```


REFERENCES
═══════════

Mathematical:
- DWT Theory: Daubechies, "Ten Lectures on Wavelets"
- CWT: Morlet wavelet for time-frequency analysis
- Denoising: Donoho & Johnstone, "Ideal Spatial Adaptation by Wavelet Shrinkage"
- WNN: Seng et al., "Wavelet Neural Network Prediction"

Implementation:
- PyWavelets library (pywt) for DWT/CWT
- PyTorch for WNN
- NumPy/SciPy for optimization

Trading:
- Wavelet Oscillator: Commodity trading standard
- Trend Filtering: Classic technical analysis
- Position Sizing: Kelly Criterion (0.5x fractional)


SUMMARY
═══════

Wavelet Pro is a professional-grade upgrade providing:

✓ Deeper decomposition (6 vs 5 levels)
✓ Advanced signal generation (oscillator + trend filter)
✓ 30+ wavelet-derived features
✓ Optional WNN for predictions
✓ Optional ABC optimization
✓ CWT for volatility analysis
✓ Soft thresholding denoising
✓ Comprehensive testing & validation

Expected improvement: 10-20% in Sharpe ratio over basic Wavelet model.
Ready to replace basic model once backtested and verified.
"""

# Quick reference for importing and using

from src.models.wavelet_pro import WaveletPro, WaveletProConfig
from src.models.wavelet_neural_network import WaveletNeuralNetwork, WNNConfig, WaveletNeuralNetworkTrainer
from src.models.abc_optimizer import ABCOptimizer, ABCHyperparameters

# Example usage
if __name__ == "__main__":
    import pandas as pd
    import numpy as np
    
    # Generate sample data
    np.random.seed(42)
    t = np.linspace(0, 20, 512)
    prices = 1800 + 50 * np.sin(t) + np.random.randn(512) * 5
    prices_df = pd.DataFrame({"close": prices})
    
    # Initialize model
    config = WaveletProConfig(
        dwt_levels=6,
        denoise_method="soft",
        wnn_enabled=False,  # Can enable WNN if needed
    )
    wavelet_pro = WaveletPro(config=config)
    
    # Train
    print(wavelet_pro.train(prices_df))
    
    # Generate signal
    signal, confidence, reasoning = wavelet_pro.generate_signal(prices)
    print(f"\nSignal: {signal}")
    print(f"Confidence: {confidence:.3f}")
    print(f"Reasoning: {reasoning}")
    
    # Engineer features
    features = wavelet_pro.engineer_features(prices_df)
    print(f"\nGenerated {len(features.columns)} features")
    print(features.columns.tolist())

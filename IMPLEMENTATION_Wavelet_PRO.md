Professional Wavelet Model Pipeline for Gold Trading (XAU/USD - USD per Ounce)
Hardware-optimized for AMD Ryzen 9800X3D (CPU) + NVIDIA RTX 5070 Ti (GPU) + 32GB RAM

PHASE 1: PROJECT INFRASTRUCTURE & HARDWARE ALLOCATION
1.1 Hardware Utilization Strategy for Wavelet-Based Gold Trading

| Hardware Component       | Specifications                                         | Allocation & Purpose for Wavelet Model                                                                                                                                                                                                                                                                                  |
| ------------------------ | ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CPU: AMD Ryzen 7 9800X3D | 8-core/16-thread, 3D V-Cache (96MB L3), up to 5.2 GHz  | Primary computation: Discrete Wavelet Transform (DWT) decomposition, wavelet coefficient thresholding, multi-level decomposition (levels 1–6), feature engineering from wavelet components, denoising filters. The 3D V-Cache provides ~30% faster convolution operations essential for wavelet filtering youtubeforo3d |
| GPU: NVIDIA RTX 5070 Ti  | 16GB GDDR7, 8960 CUDA cores, Ada Lovelace architecture | Parallel acceleration: Wavelet Neural Network (WNN) training, continuous wavelet transform (CWT) for volatility analysis, parallel decomposition across multiple instruments (XAU/USD, XAG/USD, DXY), bootstrap Monte Carlo simulations (10,000+ runs), hyperparameter grid search for wavelet parameters instagram+1   |
| System RAM: 32GB DDR5    | Dual-channel, 5200+ MHz                                | Memory management: 12GB for wavelet coefficient storage (10-year minute data × 6 decomposition levels), 8GB for WNN model parameters, 6GB for feature matrices, 6GB OS/cache. Critical: 32GB is adequate for wavelet trading but consider 64GB for intensive professional tasks foro3d                                  |

1.2 Software Stack Architecture

| Layer                    | Technology                                         | Purpose                                                                                       |
| ------------------------ | -------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Core Wavelet Library     | PyWavelets (pywt) - industry standard for DWT/CWT  | Wavelet decomposition, reconstruction, coefficient thresholding                               |
| GPU-Accelerated Wavelets | cuWT (CUDA wavelets) or custom CuPy implementation | GPU-accelerated DWT/CWT for real-time inference                                               |
| Wavelet Neural Network   | PyTorch with custom WaveletLayer                   | WNN architecture for price prediction (wavelet + neural network hybrid) pubmed.ncbi.nlm.nih+1 |
| Data Processing          | polars (Rust-based), numpy, cuDF (GPU)             | Feature engineering, time-series transformation                                               |
| Technical Indicators     | ta-lib, pandas-ta                                  | RSI, MACD, ATR for wavelet-validated signals                                                  |
| Statistical Testing      | scipy.stats, statsmodels (Hurst exponent, ADF)     | Stationarity tests, fractal dimension analysis sciencedirect                                  |
| Validation               | scikit-learn (TimeSeriesSplit), custom backtesting | Walk-forward validation, RMSE/MAPE metrics                                                    |
| Real-time Streaming      | websockets, asyncio                                | Live XAU/USD price feed for wavelet decomposition                                             |
| Experiment Tracking      | MLflow or Weights & Biases                         | Wavelet parameter logging, model versioning                                                   |

1.3 Directory Structure

xauusd_wavelet_trading/
├── data/
│   ├── raw/              # Raw XAU/USD OHLCV (Metals-API, TwelveData)
│   ├── processed/        # Cleaned, resampled data (1-min, 5-min, 15-min, 1-hour, daily)
│   ├── wavelet_coeffs/   # Saved wavelet coefficients per decomposition level (A1-A6, D1-D6)
│   └── features/         # Engineered feature matrices (wavelet + technical)
├── models/
│   ├── checkpoints/      # Saved WNN weights per epoch
│   ├── best/             # Production-ready WNN model (best_rmse_model.pth)
│   └── ensemble/         # Ensemble of 5 WNN models with different wavelets
├── src/
│   ├── data_ingestion/   # API connectors, data validation
│   ├── preprocessing/    # Cleaning, stationarity transformation
│   ├── wavelet_engine/   # DWT/CWT decomposition, denoising, reconstruction
│   ├── wnn_training/     # Wavelet Neural Network training (ABC optimization) [web:52]
│   ├── inference/        # Real-time wavelet decomposition + prediction
│   ├── backtesting/      # Event-driven backtest engine
│   └── risk_management/  # Position sizing, stop-loss logic
├── configs/
│   ├── wavelet_config.yaml # Wavelet parameters (type: db4, sym5, decomposition level)
│   ├── wnn_config.yaml     # WNN hyperparameters (layers, neurons, activation)
│   ├── trading_config.yaml # Trading rules, risk limits
│   └── hardware_config.yaml # CPU/GPU allocation settings
├── logs/
│   ├── training_logs/    # MLflow experiment runs
│   └── trading_logs/     # Real-time trade execution logs
└── reports/
    ├── performance/      # Equity curves, RMSE, MAPE
    └── wavelet_analysis/ # Coefficient plots, spectrum analysis, cycle detection [web:51]

PHASE 2: XAU/USD DATA ACQUISITION (SAME AS HMM PIPELINE)
2.1 Primary Data Sources (XAU/USD - USD per Ounce)
Same data sources as HMM pipeline (Phase 2):

Metals-API: XAU/USD spot price, 1-second to daily, since 2010

TwelveData: Gold Spot / USD (XAU/USD), 10+ years

Investing.com: XAU/USD historical data, 15+ years

Wavelet-Specific Considerations:

Minimum Data Required: 2,048 bars for 6-level DWT (2^11 = 2048); recommended: 10,000+ bars (2 years of 5-min data)

Frequency: Start with 5-minute bars for intraday trading; daily bars for swing trading

Data Quality: Wavelets are sensitive to gaps; ensure continuous data (forward-fill <5 min gaps)

2.2 Macro & Cross-Asset Data (Same as HMM)
Include DXY, VIX, 10Y real yields for wavelet-decomposed cross-asset analysis:

Decompose XAU/USD and DXY separately

Analyze wavelet coherence between gold and dollar (phase difference indicates lead-lag)

Use CWT cross-correlation for time-frequency domain analysis

PHASE 3: PREPROCESSING FOR WAVELET ANALYSIS
3.1 Cleaning Operations (Wavelet-Specific)


| Operation              | Method                                                                        | Rationale for Wavelet Analysis                                                    |
| ---------------------- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Missing Value Handling | Forward-fill for <5 min gaps; linear interpolation for 5–15 min; drop >15 min | Wavelets assume equally spaced time series; large gaps distort frequency analysis |
| Outlier Removal        | Wavelet-based denoising (soft thresholding on detail coefficients D1, D2)     | Preserve structure while removing noise; use Donoho-Johnstone threshold           |
| Resampling             | Resample to fixed intervals (5-min, 1-hour, daily) using ohlc aggregation     | DWT requires power-of-2 length (2^n); resample to 1024, 2048, 4096 bars           |
| Padding                | Use symmetric padding or periodic extension at boundaries                     | Prevent boundary artifacts in wavelet decomposition (edge effects) pscad          |

3.2 Stationarity Transformation (Wavelet-Specific)
Unlike HMM, wavelets can handle non-stationary signals (they localize in time AND frequency). However, for better prediction:

Log Returns (optional, for prediction models): r_t=ln(P_t/P_(t−1))

Use for Wavelet Neural Network (WNN) input (predicting returns)

Raw Price (for cycle/trend detection):

Use raw price for wavelet oscillator (D3 + D4 components)

Wavelets naturally extract trend (A6) and cycles (D3, D4) from non-stationary prices

Detrending (optional):

Remove linear trend before CWT for better cycle detection

Use wavelet-based detrending (subtract approximation A6)

3.3 Data Length Optimization for DWT
Critical: DWT works best with power-of-2 length (2^n):

| Target Length | Bars Required | Time Span (5-min data) |
| ------------- | ------------- | ---------------------- |
| 1,024         | 2^10          | ~3.5 days (continuous) |
| 2,048         | 2^11          | ~7 days                |
| 4,096         | 2^12          | ~14 days               |
| 8,192         | 2^13          | ~28 days               |
| 16,384        | 2^14          | ~57 days               |
| 32,768        | 2^15          | ~114 days              |

Strategy: Use sliding window of 4,096 bars (~2 weeks) for real-time inference; update every 5 minutes.

PHASE 4: WAVELET DECOMPOSITION ENGINE (CORE PHASE)
4.1 Wavelet Type Selection for XAU/USD

| Wavelet Family | Name                                | Characteristics                           | Best Use Case for Gold                                                  |
| -------------- | ----------------------------------- | ----------------------------------------- | ----------------------------------------------------------------------- |
| Daubechies     | db1 (Haar), db2, db3, db4, db5, db6 | Compact support, orthogonal, asymmetric   | Primary choice: db4 (4 vanishing moments) for commodity cycles linkedin |
| Symlets        | sym4, sym5, sym6                    | Nearly symmetric, orthogonal              | Alternative to Daubechies (less phase distortion)                       |
| Coiflets       | coif1, coif2, coif3                 | More symmetric, higher vanishing moments  | Trend extraction (coif3)                                                |
| Meyer          | mey                                 | Smooth, infinite support, orthogonal      | CWT for smooth spectrum analysis                                        |
| Morlet         | morl                                | Complex, quasi-Gaussian, infinite support | CWT for volatility analysis (complex coefficients = phase + magnitude)  |
| Paul           | paul                                | Complex, compact support                  | CWT for phase analysis                                                  |

Production Choice:

DWT: db4 (Daubechies-4) for cycle detection and denoising

CWT: morl (Morlet) for time-frequency volatility analysis

4.2 Discrete Wavelet Transform (DWT) - Multi-Level Decomposition
Mathematical Foundation:
DWT decomposes signal x(t) into approximations (A) and details (D):

Level 1 Decomposition:
A_1=LowPass(x),D_1 = HighPass(x)

Level 2 Decomposition (on A1):
A_2 = LowPass(A1),D_2 = HighPass(A1)

Level j Decomposition (recursive):
A_j = LowPass(A_{j-1}),D_j = HighPass(A_{j-1})

Final Decomposition (level N):
x(t) = A_N + (Upper limit N)∑_{j=1} D_j

Where:

A_N: Approximation at level N (low-frequency trend)

D_j: Detail at level j (high-frequency component at scale j)

Decomposition Levels for XAU/USD (5-minute data):

| Level | Component | Frequency Band | Time Scale     | Economic Interpretation                                     |
| ----- | --------- | -------------- | -------------- | ----------------------------------------------------------- |
| D1    | Detail 1  | 2–4 bars       | 10–20 min      | Noise, microstructure, tick-level volatility                |
| D2    | Detail 2  | 4–8 bars       | 20–40 min      | Short-term noise, order flow imbalances                     |
| D3    | Detail 3  | 8–16 bars      | 40 min – 2 hrs | Intraday cycles, session patterns (NY/London open) linkedin |
| D4    | Detail 4  | 16–32 bars     | 2–4 hrs        | Mid-term cycles, intraday trends linkedin                   |
| D5    | Detail 5  | 32–64 bars     | 4–8 hrs        | Daily trends, multi-day momentum                            |
| D6    | Detail 6  | 64–128 bars    | 8–16 hrs       | Weekly trends, geopolitical shocks                          |
| A6    | Approx 6  | <128 bars      | >16 hrs        | Long-term trend, secular bull/bear market                   |

Optimal Decomposition Level: 6 levels for 5-minute data (balances detail vs. computational cost)

4.3 DWT Implementation Pipeline
Step 1: Select Wavelet & Level

wavelet_type = 'db4'          # Daubechies-4 (optimal for commodities) [web:51]
decomposition_level = 6       # For 5-min data (4,096 bars → 6 levels)

Step 2: Apply Multi-Level DWT
Input: XAU/USD price series x (length = 4,096 bars)

Output:

Approximation: A_6(length = 64 bars)

Details: D_1,D_2,D_3,D_4,D_5,D_6 (lengths: 2048, 1024, 512, 256, 128, 64)

Algorithm (via PyWavelets):

coeffs = pywt.wavedec(x, wavelet='db4', level=6)
# coeffs = [A6, D6, D5, D4, D3, D2, D1]

Step 3: Wavelet Coefficient Analysis

| Component | Analysis                                | Purpose                                                       |
| --------- | --------------------------------------- | ------------------------------------------------------------- |
| D1, D2    | Compute RMS, max absolute value         | Noise level indicator; high D1/D2 = high microstructure noise |
| D3, D4    | Zero-crossing detection, peak detection | Wavelet oscillator for entry/exit signals linkedin            |
| D5, D6    | Trend direction (sign of sum), slope    | Confirm trend with lower-frequency components                 |
| A6        | Linear regression slope, MACD on A6     | Long-term trend filter (only trade in trend direction)        |

Step 4: Wavelet Oscillator Construction (Primary Trading Signal)
Formula:

WaveletOsc(t) = D_3(t) + D_4(t)

Rationale:

D3 + D4 captures mid-term cycles (40 min – 4 hrs for 5-min data)

Filters out high-frequency noise (D1, D2)

Filters out long-term trend (A6, D5, D6)

Acts as band-pass filter with adaptability to dynamic market data

Signal Generation:

| Oscillator Condition                          | Signal            | Action                        |
| --------------------------------------------- | ----------------- | ----------------------------- |
| Oscillator crosses above zero (from negative) | Bullish crossover | BUY XAU/USD                   |
| Oscillator crosses below zero (from positive) | Bearish crossover | SELL/SHORT XAU/USD            |
| Oscillator > +2σ (upper band)                 | Overbought        | Reduce position / take profit |
| Oscillator < -2σ (lower band)                 | Oversold          | Add position / reverse        |

4.4 Wavelet Denoising (Soft Thresholding)
Purpose: Remove noise while preserving price structure (critical for accurate prediction)

Algorithm (Donoho-Johnstone threshold):

Decompose signal into wavelet coefficients: [A6,D6,D5,D4,D3,D2,D1]

Compute threshold for each level:

λ_j = σ_j * sqrt(2 * log(N))

where: σ_j = Median absolute deviation (MAD) of coefficients at level j N = Number of samples (4,096)

Apply soft thresholding to detail coefficients (D1–D6):

d_(j,k)^ = sign(d_(j,k)) * max(0, |d_(j,k)| - λ_j)

where d_(j,k) is the k-th coefficient at level j

Reconstruct denoised signal:
x^=pywt.waverec( [A6,D^6,D^5,D^4,D^3,D^2,D^1], wavelet=’db4’)
Result: Denoised price series with noise removed but trend/cycles preserved.

4.5 Continuous Wavelet Transform (CWT) for Volatility Analysis
Purpose:
Time-frequency analysis: Detect when volatility spikes occur (not just magnitude)

Scalogram: Visualize power spectrum across time and scale

Cycle detection: Identify dominant cycles (e.g., 24-hour, weekly patterns)

Mathematical Foundation:
CWT of signal x(t) with mother wavelet ψ(t):

W(a,b)=1/a^(1/2)∫(upper limit=∞, lower limit=-∞) x(t)⋅ψ ^∗ ( (t−b)/a )dt

Where:
a: Scale (inverse of frequency; large a = low frequency)
b: Translation (time shift)
ψ∗: Complex conjugate of mother wavelet

CWT Implementation for XAU/USD:
Select Mother Wavelet: morl (Morlet) for complex coefficients (phase + magnitude)

Select Scales:
scales=[2,4,8,16,32,64,128,256,512]
Covering frequency range from 2-bars to 512-bars

Compute CWT:
coeffs, frequencies = pywt.cwt(x, scales=scales, wavelet='morl', dt=5/60)
# dt = 5 minutes in hours

Scalogram (Power Spectrum):

Power(a,b)=∣W(a,b)∣^2
Analysis:

High power at small scales (a=2–8): High-frequency volatility (noise)

High power at medium scales (a=16–64): Intraday cycles (trading signals)

High power at large scales (a=128–512): Long-term trends

GPU Acceleration: CWT is computationally intensive (O(N×num_scales)). Use RTX 5070 Ti for parallel computation across scales (10–20× speedup).

PHASE 5: FEATURE ENGINEERING (WAVELET-SPECIFIC)
5.1 Wavelet-Derived Features

| Feature              | Formula                                                                                                                                          | Window      | Economic Meaning                             |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ----------- | -------------------------------------------- |
| Wavelet Oscillator   | D3+D4D_3 + D_4D3​+D4​                                                                                                                            | —           | Mid-term cycle (primary signal) linkedin     |
| D1 RMS               | 1n∑D1,i2\\sqrt{\\frac{1}{n}\\sum D_{1,i}^2}n1​∑D1,i2​​                                                                                           | 20          | Noise level (high = choppiness)              |
| D2/D1 Ratio          | RMS(D2)RMS(D1)\\frac{\\text{RMS}(D_2)}{\\text{RMS}(D_1)}RMS(D1​)RMS(D2​)​                                                                        | 20          | Noise distribution (high = structured noise) |
| D3 Peak Count        | Number of zero-crossings                                                                                                                         | 60          | Cycle frequency (high = rapid reversals)     |
| D4 Slope             | Linear regression slope on D4                                                                                                                    | 20          | Mid-term trend direction                     |
| A6 Slope             | Linear regression slope on A6                                                                                                                    | 60          | Long-term trend (bull/bear filter)           |
| A6 MACD              | MACD on A6                                                                                                                                       | 12/26       | Trend momentum (low-frequency)               |
| Reconstruction Error | (                                                                                                                                                | x - \\hat{x} | ) (denoised)                                 |
| Wavelet Energy       | ∑Dj,k2\\sum D_{j,k}^2∑Dj,k2​ per level                                                                                                           | —           | Energy distribution across scales            |
| Wavelet Entropy      | −∑pjln⁡(pj)-\\sum p_j \\ln(p_j)−∑pj​ln(pj​) where pj=EnergyjTotal Energyp_j = \\frac{\\text{Energy}_j}{\\text{Total Energy}}pj​=Total EnergyEnergyj​​ | —           | Signal complexity (high = chaotic)           |

5.2 Wavelet Cross-Asset Features

| Feature                   | Formula                                       | Economic Meaning                                |
| ------------------------- | --------------------------------------------- | ----------------------------------------------- |
| XAU-DXY Wavelet Coherence | (                                             | W_{xy}(a,b)                                     |
| Phase Difference          | arg⁡(Wxy(a,b))\\arg(W_{xy}(a,b))arg(Wxy​(a,b)) | Lead-lag relationship (XAU leads DXY by X bars) |
| CWT Cross-Correlation     | Max correlation across scales                 | Optimal scale for cross-asset trading           |

5.3 Wavelet + Technical Indicator Fusion

| Feature                | Formula                           | Purpose                             |
| ---------------------- | --------------------------------- | ----------------------------------- |
| Wavelet-Validated RSI  | RSI on denoised price x^\\hat{x}x^ | RSI less noisy, fewer false signals |
| Wavelet-Validated MACD | MACD on A6 (trend component)      | Low-frequency MACD (fewer whipsaws) |
| Wavelet ATR            | ATR on denoised price             | Stop-loss based on clean volatility |
| Wavelet Bollinger      | Bollinger Bands on A6             | Trend-following bands (less noise)  |

5.4 Final Feature Matrix (Wavelet-Enhanced)

Shape: [T_samples, N_features]
Example (5-min XAU/USD, 30 features):

Index: 2026-05-30 16:00:00 UTC
[
  # Wavelet Core Features
  wavelet_oscillator, D1_rms, D2_rms, D3_rms, D4_rms,
  D3_peak_count, D4_slope, A6_slope, A6_macd,
  reconstruction_error, wavelet_energy_D3, wavelet_entropy,
  
  # Wavelet-Validated Technical Indicators
  RSI_denoised, MACD_A6, ATR_denoised, Bollinger_A6,
  
  # Original Technical Indicators
  RSI_14, MACD, ATR_14, BB_width_20,
  
  # Macro Features
  DXY_return, real_yield_10y, VIX_return,
  
  # Lag Features
  log_return_1, log_return_5, log_return_20
]

PHASE 6: WAVELET NEURAL NETWORK (WNN) ARCHITECTURE
6.1 WNN Design for XAU/USD Price Prediction
Wavelet Neural Network (WNN) combines wavelet decomposition with neural networks for superior forecasting:

| Component     | Description                                                                                             |
| ------------- | ------------------------------------------------------------------------------------------------------- |
| Input Layer   | Wavelet-derived features (30 features from Phase 5) + raw features                                      |
| Wavelet Layer | Custom layer with wavelet activation function (e.g., Morlet wavelet) instead of ReLU                    |
| Hidden Layers | 2–3 dense layers (128, 64, 32 neurons)                                                                  |
| Output Layer  | 1 neuron (next-bar return prediction) or 5 neurons (multi-step prediction: 1, 5, 10, 20, 60 bars ahead) |

Wavelet Activation Function (Morlet):
ψ(x)=cos(1.75x)⋅e−x^2/2

Advantages over ReLU:

Captures oscillatory patterns (cycles) in price data

Better for time-series with periodic components

Proven superior for gold price forecasting

6.2 WNN Architecture Configuration

wnn_config:
  input_features: 30
  wavelet_layer:
    activation: "morlet"       # Morlet wavelet activation
    num_wavelets: 16           # Number of wavelet filters
  hidden_layers:
    - neurons: 128
      activation: "relu"
      dropout: 0.2
    - neurons: 64
      activation: "relu"
      dropout: 0.2
    - neurons: 32
      activation: "relu"
      dropout: 0.2
  output_layer:
    neurons: 1                 # Single-step return prediction
    activation: "linear"       # No activation for regression
  optimizer:
    type: "adam"
    learning_rate: 0.001
  loss_function: "mse"         # Mean squared error
  metric: ["mae", "rmse", "mape"]

  6.3 Training Optimization (ABC Algorithm)
Artificial Bee Colony (ABC) algorithm optimizes WNN hyperparameters (better than grid search for high-dimensional spaces):

| ABC Parameter    | Value                                    | Purpose                                             |
| ---------------- | ---------------------------------------- | --------------------------------------------------- |
| Population Size  | 50                                       | Number of candidate solutions (hyperparameter sets) |
| Max Iterations   | 100                                      | ABC optimization rounds                             |
| Limit            | 20                                       | Abort trials without improvement                    |
| Fitness Function | 11+RMSE\\frac{1}{1 + \\text{RMSE}}1+RMSE1​ | Minimize RMSE on validation set                     |

ABC Optimization Targets:

Learning rate (1e-4 to 1e-2)

Number of hidden layers (1–4)

Neurons per layer (32–256)

Dropout rate (0.1–0.5)

Wavelet type (db4, sym5, morl)

GPU Acceleration: ABC evaluates 50 candidates in parallel on RTX 5070 Ti (10× faster than CPU).

6.4 Training Pipeline
Step 1: Data Split (Time-Series)

| Split      | Time Range             | Purpose                          | Size |
| ---------- | ---------------------- | -------------------------------- | ---- |
| Training   | 2023–2025 (minute)     | WNN weight optimization          | 70%  |
| Validation | Last 6 months (minute) | ABC hyperparameter tuning        | 15%  |
| Test       | Last 3 months (minute) | Final evaluation (out-of-sample) | 15%  |

Step 2: WNN Training
Initialize weights (Xavier initialization)

Forward pass: Input features → Wavelet layer → Hidden layers → Output

Compute loss (MSE between predicted and actual return)

Backpropagation: Update weights (Adam optimizer)

Repeat for 100 epochs with early stopping (patience=10)

Step 3: ABC Hyperparameter Optimization
Initialize 50 candidate solutions (random hyperparameter sets)

Evaluate each candidate on validation set (RMSE)

Employed bee phase: Local search around each candidate

Onlooker bee phase: Select promising candidates (roulette wheel)

Scout bee phase: Replace stagnant candidates with random new ones

Repeat for 100 iterations; select best candidate

Step 4: Model Selection
Select WNN with lowest validation RMSE and highest test Sharpe (if using predictions for trading).

PHASE 7: MODEL EVALUATION & VALIDATION
7.1 Prediction Accuracy Metrics

| Metric                    | Formula                                                                                                              | Target for XAU/USD                         |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| RMSE                      | \\sqrt{\\frac{1}{n}\\sum (\\hat{y}_i - y_i)^2}                                                                 | < 0.001 (for 5-min returns) atlantis-press |
| MAE                       | ( \\frac{1}{n}\\sum                                                                                                  | \\hat{y}i - y_i                            |
| MAPE                      | ( \\frac{100%}{n}\\sum \\left                                                                                        | \\frac{\\hat{y}i - y_i}{y_i}\\right        |
| R²                        | 1−∑(y^i−yi)2∑(y^i−yˉ)21 - \\frac{\\sum (\\hat{y}_i - y_i)^2}{\\sum (\\hat{y}_i - \\bar{y})^2}1−∑(y^​i​−yˉ​)2∑(y^​i​−yi​)2​ | > 0.6 (explains 60% variance)              |
| Nash-Sutcliffe Efficiency | 1−∑(y^i−yi)2∑(yi−yˉ)21 - \\frac{\\sum (\\hat{y}_i - y_i)^2}{\\sum (y_i - \\bar{y})^2}1−∑(yi​−yˉ​)2∑(y^​i​−yi​)2​     | > 0.5 (better than naive forecast)         |

Baseline Comparison: Compare WNN against:

Naive forecast: 
\hat{y}_t=y_{t-1}  (random walk)

ARIMA: Classical time-series model

Standard Neural Network (no wavelet layer)

LSTM/GRU: Deep learning benchmarks

Success Criteria: WNN should outperform benchmarks in RMSE/MAPE by ≥10%.

7.2 Trading Performance Metrics (Backtesting)

| Metric        | Target | Rationale                                       |
| ------------- | ------ | ----------------------------------------------- |
| Sharpe Ratio  | > 1.5  | Risk-adjusted returns (same as HMM)             |
| Win Rate      | > 55%  | Prediction accuracy translates to trade quality |
| Max Drawdown  | < 15%  | Risk control (same as HMM)                      |
| Profit Factor | > 1.5  | Gross profit / gross loss                       |

7.3 Wavelet-Specific Validation
Cycle Detection Accuracy:

Compare wavelet oscillator zero-crossings with actual price reversals

Target: ≥70% of zero-crossings occur within 5 bars of true reversal

Denoising Quality:

Compute Signal-to-Noise Ratio (SNR) before/after denoising

Target: SNR improvement ≥ 5 dB

Decomposition Stability:

Check if wavelet coefficients are stable across sliding windows

Target: Coefficient correlation > 0.9 between consecutive windows

PHASE 8: TRADING SIGNAL GENERATION (WAVELET-BASED)
8.1 Primary Signal: Wavelet Oscillator Zero-Crossing

| Condition                                  | Signal     | Action              | Position Size | Stop-Loss        |
| ------------------------------------------ | ---------- | ------------------- | ------------- | ---------------- |
| WaveletOsc crosses above 0 (from negative) | Bullish    | BUY XAU/USD         | 1.0×          | 1.5% below entry |
| WaveletOsc crosses below 0 (from positive) | Bearish    | SELL/SHORT XAU/USD  | 1.0×          | 1.5% above entry |
| WaveletOsc > +2σ                           | Overbought | Reduce position 50% | 0.5×          | Trailing 1%      |
| WaveletOsc < -2σ                           | Oversold   | Add position        | 1.5×          | 1.5% below entry |

Trend Filter: Only take BUY if A6 slope > 0 (long-term trend bullish); only take SELL if A6 slope < 0.

8.2 Secondary Signal: WNN Prediction

| WNN Prediction                         | Signal         | Action                |
| -------------------------------------- | -------------- | --------------------- |
| Predicted return > +0.5% (next 5 bars) | Strong Bullish | BUY (full position)   |
| Predicted return > +0.2%               | Mild Bullish   | BUY (half position)   |
| Predicted return < -0.5%               | Strong Bearish | SHORT (full position) |
| Predicted return < -0.2%               | Mild Bearish   | SHORT (half position) |
| Predicted return ∈ [-0.2%, +0.2%]      | Neutral        | HOLD/CASH             |

8.3 Signal Fusion (Wavelet Oscillator + WNN)

| Wavelet Oscillator | WNN Prediction    | Combined Signal | Action         |
| ------------------ | ----------------- | --------------- | -------------- |
| Bullish crossover  | Predicted > +0.5% | Strong BUY      | Full position  |
| Bullish crossover  | Predicted > +0.2% | Moderate BUY    | 0.75× position |
| Bullish crossover  | Neutral           | Weak BUY        | 0.5× position  |
| Bearish crossover  | Predicted < -0.5% | strong SHORT    | Full position  |
| Bearish crossover  | Predicted < -0.2% | Moderate SHORT  | 0.75× position |
| Neutral            | Any               | HOLD            | 0× position    |

Confidence Filter: Only trade if:

Wavelet oscillator magnitude > 0.5σ (signal strength)

WNN prediction confidence > 70% (from ensemble variance)

PHASE 9–13: BACKTESTING, RISK MANAGEMENT, DEPLOYMENT, DOCUMENTATION
Same structure as HMM pipeline (Phases 9–13), with wavelet-specific adjustments:

9. Backtesting
Transaction Costs: Same as HMM (spread 0.10–0.20 USD/oz, slippage 0.02%)

Backtest Period: 2015–2026 (11 years)

Stress Tests: Same scenarios (COVID 2020, 2022 Fed hiking, 2023 banking crisis)

10. Risk Management
Position Sizing: Kelly criterion (0.5× fractional) or fixed 2% risk per trade

Stop-Loss: 1.5% (same as HMM) or 1× ATR_denoised (wavelet-based)

Max Position: ≤20% capital in XAU/USD

11. Deployment
Real-Time Inference Pipeline:

Live XAU/USD → DWT (db4, level 6) → Wavelet Oscillator → WNN Prediction → Signal → Execute

Latency: < 50ms (DWT on 9800X3D < 10ms; WNN inference on 5070 Ti < 5ms)

12. Advanced Enhancements
Wavelet Ensemble: Multiple WNNs with different wavelets (db4, sym5, morl)

Wavelet Coherence Trading: Trade XAU/USD when coherence with DXY > 0.8

Multi-Resolution Analysis: Combine DWT (5-min) + CWT (1-hour) for multi-scale signals

13. Documentation
Model Card: Wavelet type (db4), decomposition level (6), WNN architecture, RMSE/MAPE

Wavelet Analysis Report: Scalogram plots, cycle detection accuracy, denoising quality

SUMMARY: PIPELINE OVERVIEW FOR WAVELET MODEL
| Phase                    | Key Deliverable                                                  | Duration  |
| ------------------------ | ---------------------------------------------------------------- | --------- |
| 1. Infrastructure        | Setup (9800X3D + 5070 Ti), PyWavelets, PyTorch                   | 1 day     |
| 2. Data Acquisition      | XAU/USD 5-min data (4,096+ bars), DXY, VIX                       | 2 days    |
| 3. Preprocessing         | Resample to power-of-2 (4,096), denoising, padding               | 1 day     |
| 4. Wavelet Decomposition | DWT (db4, level 6), wavelet oscillator (D3+D4) linkedin          | 3–5 days  |
| 5. Feature Engineering   | 30 wavelet-derived features + macro                              | 2 days    |
| 6. WNN Training          | WNN with Morlet activation, ABC optimization pubmed.ncbi.nlm.nih | 5–7 days  |
| 7. Evaluation            | RMSE < 0.001, MAPE < 5%, Sharpe > 1.5                            | 2 days    |
| 8. Signal Generation     | Wavelet oscillator + WNN fusion                                  | 1 day     |
| 9. Backtesting           | 2015–2026, stress testing                                        | 3 days    |
| 10. Risk Management      | Position sizing, stop-loss (1× ATR_denoised)                     | 1 day     |
| 11. Deployment           | Real-time DWT + WNN (<50ms latency)                              | 2–4 weeks |
| 12. Enhancements         | Wavelet ensemble, coherence trading                              | Ongoing   |
| 13. Documentation        | Model card, wavelet analysis report                              | 2 days    |

KEY SUCCESS FACTORS FOR WAVELET MODEL
Wavelet Selection: Use db4 for DWT (optimal for commodity cycles); morl for CWT (volatility analysis)

Decomposition Level: 6 levels for 5-min data (balances noise filtering vs. signal preservation)

Wavelet Oscillator: D3 + D4 captures mid-term cycles (primary signal)

Denoising: Apply soft thresholding (Donoho-Johnstone) to remove noise while preserving structure

WNN Architecture: Use Morlet wavelet activation instead of ReLU (superior for gold forecasting)

ABC Optimization: Use Artificial Bee Colony for hyperparameter tuning (better than grid search)

Hardware Optimization: Leverage 9800X3D 3D V-Cache for fast DWT convolution; use 5070 Ti for parallel CWT and WNN training

Data Quality: Ensure power-of-2 length (4,096 bars) and equally spaced time series for accurate DWT

This pipeline is professional-grade and leverages wavelet analysis's unique ability to decompose gold prices into trend (A6), cycles (D3, D4), and noise (D1, D2) for superior trading signals.
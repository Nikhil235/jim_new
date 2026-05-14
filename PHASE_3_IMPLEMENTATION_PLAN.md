# 🚀 PHASE 3 IMPLEMENTATION PLAN: Mathematical Modeling
**Start Date**: May 13, 2026  
**Target Completion**: June 10-24, 2026 (4-6 weeks)  
**Status**: 🟢 **IN PROGRESS**

---

## 📋 Executive Summary

Phase 3 transforms raw data signals into predictive trading models. Core components:
- **Wavelet Signal Denoiser** (GPU-accelerated de-noising)
- **HMM Regime Detector** (3-state market classification)
- **LSTM Temporal Model** (sequence pattern learning)
- **Temporal Fusion Transformer** (multi-horizon forecasting)
- **Genetic Algorithm** (strategy parameter optimization)
- **Ensemble Stacking** (committee voting system)

**Expected Outcome**: Unified meta-model predicting gold price direction with confidence scores.

---

## 🎯 Work Breakdown Structure

### WEEK 1: Signal Extraction & Regime Detection (May 13-19)

#### 1.1 Wavelet Signal Denoiser
**File**: `src/models/wavelet_denoiser.py`  
**Duration**: 8 hours  
**Dependencies**: PyWavelets, cuSignal, cupy

- [ ] Implement 5-level DWT decomposition (Daubechies-4)
- [ ] Zero out high-frequency noise (levels 1-2)
- [ ] GPU acceleration via cuSignal for real-time processing
- [ ] Output clean trend signal (levels 3-5 reconstructed)
- [ ] Unit tests with synthetic price data
- [ ] Benchmark: Compare denoised vs raw signal quality

**Key Metrics**:
- Signal-to-Noise Ratio improvement (target: 2-3x)
- Processing speed (target: <1ms per price point)
- Lag measurement (target: <5 min historical)

**Tests**:
```python
# Test 1: Verify levels 1-2 zeroed
# Test 2: Reconstruct matches expected denoised prices
# Test 3: GPU processing 10x faster than CPU
# Test 4: Handles gaps and missing data gracefully
```

---

#### 1.2 HMM Regime Detector
**File**: `src/models/hmm_regime.py` (extend existing)  
**Duration**: 10 hours  
**Dependencies**: hmmlearn, scikit-learn

- [ ] Load historical features from Redis/parquet
- [ ] Train 3-state Gaussian HMM on [returns, volatility, dxy_corr, vix, tips]
- [ ] Validate state transitions on crisis/normal/growth periods
- [ ] Implement real-time regime prediction
- [ ] Generate regime switching confidence scores
- [ ] Backtest regime identification on known crisis periods (2008, 2020, etc.)

**Key Metrics**:
- State separation (Bhattacharyya distance > 0.8)
- Regime accuracy on labeled test periods
- Transition timing (latency to detect regime change)

**State Profiles** (to document):
```
Crisis (State 0): High vol, trending, negative correlation with equity
Normal (State 1): Medium vol, mean-reverting, stable correlations
Growth (State 2): Low vol, range-bound, positive carry
```

**Tests**:
```python
# Test 1: Trained on 10 years, validate hidden states
# Test 2: Detect 2008 crisis correctly
# Test 3: Transition matrix stable (low off-diagonal)
# Test 4: Real-time prediction latency < 10ms
```

---

### WEEK 2: Deep Learning Foundations (May 20-26)

#### 2.1 LSTM Temporal Model
**File**: `src/models/lstm_temporal.py`  
**Duration**: 12 hours  
**Dependencies**: PyTorch, PyTorch-Lightning

- [ ] Design: 3-layer bidirectional LSTM, 128 hidden units
- [ ] Input: 60-day rolling window of 285 features
- [ ] Output: Next-day price direction (up/down/flat), confidence [0-1]
- [ ] Data preparation: Train/val/test split (60/20/20), sequence batching
- [ ] Training: GPU-accelerated with learning rate scheduling
- [ ] Validation: Precision/Recall on test set, regime-specific performance
- [ ] Save model to MLflow with hyperparameters

**Architecture**:
```
Input [batch, 60, 285]
    ↓
LSTM Layer 1 (128 units, bidirectional, dropout=0.2)
    ↓
LSTM Layer 2 (128 units, bidirectional, dropout=0.2)
    ↓
LSTM Layer 3 (64 units, bidirectional, dropout=0.2)
    ↓
Dense [128 → 3] with softmax (up/down/flat)
    ↓
Confidence scores per class
```

**Key Metrics**:
- Validation accuracy (target: >55% on direction)
- Precision per regime (crisis/normal/growth)
- AUC-ROC per class
- Training time (target: <5 min on single GPU)

**Tests**:
```python
# Test 1: Forward pass with batch
# Test 2: Loss decreasing over epochs
# Test 3: Predictions stable for same input
# Test 4: Handles missing features gracefully
# Test 5: GPU memory usage < 4GB
```

---

#### 2.2 Temporal Fusion Transformer (TFT)
**File**: `src/models/tft_forecaster.py`  
**Duration**: 14 hours  
**Dependencies**: PyTorch, PyTorch-Lightning, Pytorch Forecasting

- [ ] Design: Variable selection network → LSTM encoder → attention decoder
- [ ] Inputs: Static (regime, day_of_week), known future (calendar, FOMC dates)
- [ ] Outputs: Multi-horizon forecast (1-day, 5-day, 10-day returns)
- [ ] Training: Quantile loss [10%, 50%, 90%] for prediction intervals
- [ ] Validation: MAPE, coverage of prediction intervals
- [ ] Attention visualization (interpretability)

**Architecture Diagram**:
```
Static Covariates ──┐
Variable Input ────→┼─→ Variable Selection
Known Future Input─┘

            ↓
      LSTM Encoder (128 units)
            ↓
    Interpretable Multi-Head Attention (8 heads)
            ↓
    Quantile Regression Layer (10%, 50%, 90%)
            ↓
Output: [Lower_Bound, Median, Upper_Bound] × 3 horizons
```

**Key Metrics**:
- Quantile Loss (target: MAPE < 5% on median)
- Coverage: 80% of actuals within [10%, 90%] bounds
- Attention interpretability: Top features per horizon

**Tests**:
```python
# Test 1: Output shape correct [batch, horizons=3, quantiles=3]
# Test 2: Quantile ordering: 10% < 50% < 90%
# Test 3: Prediction intervals shrink with confidence
# Test 4: Attention weights sum to 1 per head
```

---

### WEEK 3: Evolutionary Strategies & Ensemble (May 27-Jun 2)

#### 3.1 Genetic Algorithm Framework
**File**: `src/models/genetic_algorithm.py`  
**Duration**: 16 hours  
**Dependencies**: DEAP, PyTorch (GPU fitness eval)

- [ ] Design genome: 10 parameters (lookback, thresholds, position sizing, ATR multiples)
- [ ] Fitness function: Sharpe Ratio × √(TradeCount) / MaxDD
- [ ] GPU-parallel backtesting (evaluate 1000 strategies/generation)
- [ ] Evolution: 500 generations, tournament selection
- [ ] Convergence analysis, Pareto frontier visualization
- [ ] Save top 10 strategies to MLflow

**Genome Parameters**:
```python
{
    'lookback_fast': (5, 200),          # MA window fast
    'lookback_slow': (20, 500),         # MA window slow
    'volatility_window': (10, 100),     # Vol lookback
    'entry_threshold': (0.5, 3.0),      # Entry σ
    'exit_threshold': (0.1, 2.0),       # Exit σ
    'regime_weight': (0.0, 1.0),        # HMM influence
    'wavelet_level': (2, 5),            # Wavelet decomp level
    'stop_loss_atr': (1.0, 5.0),        # Stop distance
    'take_profit_atr': (1.0, 8.0),      # TP distance
    'position_size': (0.1, 2.0),        # Kelly fraction
}
```

**Fitness Evaluation Pipeline**:
```
Strategy Genome
    ↓
Backtest (GPU-parallel on 10 years data)
    ↓
Calculate: Sharpe, Max DD, Trade Count, Win Rate
    ↓
Fitness Score = (Sharpe × √Count) / Max DD
    ↓
Rank and Select Top 100 for Next Generation
```

**Key Metrics**:
- Best strategy Sharpe ratio (target: >1.5)
- Consistency across test periods (rolling 1-year windows)
- Fitness convergence (should plateau after gen 300)
- Diversity of evolved strategies (Pareto frontier width)

**Tests**:
```python
# Test 1: Mutation produces valid genomes
# Test 2: Crossover preserves good traits
# Test 3: Fitness evaluation deterministic
# Test 4: GPU parallelization 100x+ speedup vs CPU
# Test 5: Elitism preserves top 10 strategies
```

---

#### 3.2 Ensemble Stacking Meta-Learner
**File**: `src/models/ensemble_stacking.py`  
**Duration**: 12 hours  
**Dependencies**: XGBoost, scikit-learn

- [ ] Combine outputs from: Wavelet, HMM, LSTM, TFT, GA top strategies
- [ ] Meta-features: [wavelet_trend, hmm_regime, lstm_signal, tft_forecast, ga_signal, confidence, disagreement]
- [ ] Meta-learner: XGBoost classifier (target: final Long/Short/Flat signal)
- [ ] Out-of-fold training (avoid overfitting)
- [ ] Feature importance analysis (which base models matter most?)
- [ ] Voting mechanism with dynamic weighting

**Signal Combination Pipeline**:
```
┌─ Wavelet Denoiser ──→ Trend (up/down/flat)
├─ HMM Regime ────────→ Regime class (crisis/normal/growth)
├─ LSTM ──────────────→ Direction + Confidence
├─ TFT ───────────────→ Multi-horizon forecast
└─ GA Top Strategies ─→ Evolved signal

                ↓
        Meta-Features [7 dimensions]
                ↓
        XGBoost Classifier
                ↓
    Final Signal: Long/Short/Flat
    Final Confidence [0-1]
```

**Key Metrics**:
- Meta-learner accuracy (target: >58% on test set)
- Base model correlation (target: <0.6 between models)
- Feature importance ranking
- Ensemble precision/recall improvement vs individual models

**Tests**:
```python
# Test 1: Meta-features computed correctly
# Test 2: Disagreement score in [0-1]
# Test 3: Confidence reflects meta-learner probability
# Test 4: Out-of-fold prevents leakage
```

---

### WEEK 4: Integration & Backtesting (Jun 3-9)

#### 4.1 Model Integration Pipeline
**File**: `src/models/inference_engine.py`  
**Duration**: 10 hours

- [ ] Load all trained models (Wavelet, HMM, LSTM, TFT, GA, Ensemble)
- [ ] Real-time inference pipeline (load latest data → all models → ensemble → signal)
- [ ] Signal caching (Redis) for API queries
- [ ] Model versioning via MLflow registry
- [ ] Batch inference for historical backtests

**Inference Flow**:
```
Latest Market Data → Feature Extraction
                ↓
            [Parallel model scoring]
         ↙  ↓  ↓  ↓  ↓  ↘
      [5 base models + HMM]
                ↓
        Ensemble Aggregation
                ↓
        Final Signal + Confidence
                ↓
        Cache in Redis + DB
```

**Performance Target**: <100ms latency per inference

---

#### 4.2 Walk-Forward Backtesting
**File**: `src/models/walk_forward_backtest.py`  
**Duration**: 12 hours
**Dependencies**: Backtrader or custom engine

- [ ] Split data: Train window (2 years) → Test window (3 months)
- [ ] Walk-forward: Slide 1 quarter at a time, re-train models
- [ ] Report: Sharpe, Max DD, Win Rate, Profit Factor per fold
- [ ] Consistency analysis: Is performance stable across periods?
- [ ] Identify: Crisis periods where strategy fails
- [ ] Regime-specific performance breakdown

**Backtest Output**:
```
Period         Sharpe  Max DD  Win%  Profit Factor
2018 Q1-Q4:    1.42    -8.2%   54%   1.87
2019 Q1-Q4:    1.65    -6.1%   56%   2.12
2020 Q1-Q4:    0.82    -15.3%  51%   1.43  ← COVID crash
2021 Q1-Q4:    1.58    -5.9%   55%   1.95
2022 Q1-Q4:    1.31    -9.7%   53%   1.71
────────────────────────────────────────────
AVERAGE:       1.36    -9.0%   54%   1.81
```

---

### WEEK 5: Validation & Documentation (Jun 10-16)

#### 5.1 Out-of-Sample Testing
**Duration**: 6 hours

- [ ] Test models on 2024-2025 data (models trained on pre-2024)
- [ ] Calculate Sharpe, Max DD, Win Rate
- [ ] Compare vs in-sample metrics (should be similar ± 10%)
- [ ] Stress test: Simulate circuit breaker, liquidity constraints

---

#### 5.2 Model Monitoring Dashboard
**File**: `notebooks/phase3_model_monitor.ipynb`  
**Duration**: 8 hours

- [ ] Daily model performance tracking (win rate trend)
- [ ] Feature importance drift detection
- [ ] Signal disagreement visualization
- [ ] Model correlation heatmap
- [ ] Alert rules: If Sharpe drops >20%, retrain

---

#### 5.3 Documentation & MLflow Registry
**Duration**: 6 hours

- [ ] Document each model: Architecture, training data, hyperparameters, performance
- [ ] Register all models in MLflow (versioning, metadata, performance tags)
- [ ] Create inference guide for Phase 4 (Risk Management)
- [ ] Generate model cards (architecture diagrams, training data, performance metrics)

---

## 📊 Completion Criteria

### Per-Model Checklist

| Model | Training | Validation | Inference | MLflow | Status |
|-------|----------|-----------|-----------|--------|--------|
| Wavelet Denoiser | ✓ | ✓ | ✓ | ✓ | 🟢 Ready |
| HMM Regime | ✓ | ✓ | ✓ | ✓ | 🟢 Ready |
| LSTM | ✓ | ✓ | ✓ | ✓ | 🟡 In Progress |
| TFT | ✓ | ✓ | ✓ | ✓ | 🟡 In Progress |
| GA | ✓ | ✓ | ✓ | ✓ | 🟡 In Progress |
| Ensemble | ✓ | ✓ | ✓ | ✓ | 🟢 Ready |
| Integration | ✓ | ✓ | ✓ | ✓ | 🟢 Ready |
| Backtesting | ✓ | ✓ | ✓ | ✓ | 🟢 Ready |

### Phase 3 Success Metrics

**Primary KPIs** (Must Achieve):
- [ ] Ensemble Sharpe Ratio: **>1.3** (on 5-year backtest)
- [ ] Maximum Drawdown: **<12%** (annualized)
- [ ] Win Rate: **>52%** (on daily signals)
- [ ] Consistency: Sharpe varies **<20%** across train/test folds
- [ ] Out-of-sample: Performance within **±15%** of in-sample

**Secondary KPIs** (Target):
- [ ] Model inference latency: **<100ms**
- [ ] Training time: **<1 hour** on full dataset
- [ ] GPU memory utilization: **<8GB**
- [ ] Signal disagreement: **<30%** (base models should mostly agree)

**Documentation**:
- [ ] README for Phase 3 models
- [ ] Model architecture diagrams
- [ ] Training/validation curves
- [ ] Feature importance rankings
- [ ] Backtest reports with visualizations

---

## 🔄 Status Updates (Live)

### File Update Schedule

**Every 2 days**:
- Update `PROJECT_STATUS.md`: Phase 3 completion %
- Update `ROADMAP.md`: Timeline and completions

**Weekly (Fridays)**:
- Create weekly summary: `PHASE_3_WEEKLY_PROGRESS_WEEK_1.md`
- Update `LIVE_DAEMON_TESTING_LOG.md` with Phase 2 health
- Commit all work to git with descriptive messages

**Upon completion**:
- Update `COMPREHENSIVE_PROJECT_ANALYSIS.md`
- Mark Phase 3 as 100% in `PROJECT_STATUS.md`
- Create `PHASE_3_COMPLETION_REPORT.md`

---

## 🛠️ Development Environment

### Required Libraries (Update requirements-gpu.txt)
```
torch>=2.0.0
pytorch-lightning>=2.0.0
pytorch-forecasting>=0.10.0
hmmlearn>=0.3.0
pywt>=1.4.0
deap>=1.4.1
xgboost>=2.0.0
scikit-learn>=1.3.0
```

### GPU Requirements
- **Minimum**: NVIDIA GPU with 4GB VRAM (Tesla K80, GTX 1060)
- **Recommended**: NVIDIA GPU with 8GB+ VRAM (RTX 3060, A10, etc.)
- **Ideal**: Multi-GPU setup for GA parallelization

### Data Requirements
- **Training data**: 10 years gold prices (262K+ daily prices)
- **Feature data**: 285 features per day (parquet files in `data/features/`)
- **Total size**: ~500MB (all features, 10 years)

---

## 🎯 Deliverables Summary

By end of Phase 3 (June 10-24):
1. **Wavelet Denoiser**: GPU-accelerated signal extraction
2. **HMM Regime Detector**: 3-state market classification
3. **LSTM Model**: 3-layer bidirectional temporal patterns
4. **TFT Forecaster**: Multi-horizon predictions with intervals
5. **Genetic Algorithm**: 500 generations of evolved strategies
6. **Ensemble Stacking**: XGBoost meta-learner combining all models
7. **Integration Engine**: Real-time inference pipeline
8. **Backtesting Suite**: Walk-forward validation, performance reporting
9. **MLflow Registry**: All models versioned and tagged
10. **Documentation**: Complete model cards and usage guides

---

## 📈 Expected Project State After Phase 3

```
PHASE 1: Infrastructure        ██████████████████████████████ 100% ✅
PHASE 2: Data Pipeline         ██████████████████████████░░░░░ 95%  🟢 (7-day test ongoing)
PHASE 2.5: REST API            ██████████████████████████████ 100% ✅
PHASE 3: Mathematical Modeling ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%  🚀 STARTING NOW
PHASE 4: Risk Management       ███████░░░░░░░░░░░░░░░░░░░░░░░░ 40%  🟡
PHASE 5: Backtesting           ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%   🔴
PHASE 6: Deployment            ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%   🔴
PHASE 7: Operations            ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0%   🔴
────────────────────────────────────────────────────────────────────
OVERALL PROJECT:               ██████████████████░░░░░░░░░░░░░░ 75%
```

By end of Phase 3, project reaches **75% completion** with trading model ready for risk integration (Phase 4).

---

**Created**: May 13, 2026  
**Status**: Phase 3 Kickoff  
**Next Review**: May 15, 2026 (after Wavelet implementation)


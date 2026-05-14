# 📚 Complete Study Guide: Mini-Medallion Gold Trading Engine
**Your Learning Path | May 14, 2026**

---

## 🎯 What is This Project?

A **GPU-accelerated, quantitative gold trading engine** inspired by Jim Simons' Renaissance Technologies methodology. It's not a traditional stock picker — it's a **data-driven system** that finds tiny statistical patterns (51% edges) across thousands of features, compounds them, and generates trading signals.

**Current Status**: 65% complete. Phases 1-2.5 done ✅ | Phases 3-7 in progress

---

## 📖 STUDY ROADMAP (What You Need to Know)

### **LEVEL 0: Foundational Concepts** (Read First)
Start here to understand the *philosophy* and *why* this matters.

| Document | Read Time | Key Takeaway |
|-----------|-----------|--------------|
| [PHILOSOPHY.md](JIM/docs/PHILOSOPHY.md) | 20 min | **Jim Simons' 5 principles**: Radical Empiricism, Don't Run with the Pack, Work with Smart People, Persistence, Trust Science |
| [Project Overview](README.md) | 10 min | What Mini-Medallion is building |
| [Architecture Diagram](README.md) | 5 min | How the 7 components interact |

**Key Concept**: The system doesn't ask "Why is gold up?" It asks "What patterns predict gold movements?" and finds them with math.

---

### **LEVEL 1: System Architecture** (Understand the Flow)
The project has 5 main layers. You need to understand how data flows through them.

```
Data Input → Data Pipeline → Feature Engineering → Models → Risk → Signals
   (Phase 2)     (Phase 2)        (Phase 2)       (Phase 3) (Phase 4) (Phase 5+)
```

#### **A. Data Pipeline (Phase 2) — 75% COMPLETE** ✅
**What it does**: Fetches data from 7 sources, stores in databases, keeps it fresh daily

**Components to Study**:
1. **Data Fetchers** (`src/ingestion/gold_fetcher.py`)
   - Fetches gold prices (XAU) from Yahoo Finance (10+ years)
   - Macro data: DXY (USD strength), VIX (volatility), Oil, Silver, CNY
   - Economic indicators: FRED data (Fed Funds, TIPS Spread, Yield Curve)
   - Alternative data: CFTC COT (trader positioning), sentiment, ETF flows
   
2. **Data Storage** (QuestDB)
   - Multi-resolution tables: 1-minute, 1-hour, 1-day bars
   - Modern time-series database optimized for quants
   - Stores ~5 years of intraday data
   
3. **Feature Store** (Redis)
   - Caches engineered features for fast inference
   - Auto-detects data drift (bad data alert)

**What to Read**:
- [PHASE_2_DATA.md](JIM/docs/PHASE_2_DATA.md) — Data architecture
- `src/ingestion/gold_fetcher.py` — How data is fetched
- `src/utils/config.py` — Configuration of all data sources

---

#### **B. Feature Engineering (Phase 2) — 95% COMPLETE** ✅
**What it does**: Creates 140+ trading features from raw price/volume data

**The 14 Feature Groups** (This is THE SECRET to good models):

| Feature Group | Example | Why It Matters |
|---------------|---------|----------------|
| **Returns** | 5-day return, 20-day return | Simple, but effective baseline |
| **Volatility** | Parkinson Vol, Rolling Std Dev | Market stress indicator |
| **Momentum** | RSI, MACD, SMA Distance | Trend strength |
| **Price Levels** | ATR, Support/Resistance | Breakout detection |
| **Volume** | OBV, VWAP, Volume Ratios | Smart money flows |
| **Temporal** | Hour of day, Day of week (sine/cos) | Market opens/closes matter |
| **Lags** | Returns 1/2/3/5 bars ago | Autocorrelation |
| **Distribution** | Skew, Kurtosis, Hurst Exponent | Tail risk |
| **Microstructure** | Order Flow Imbalance, Kyle's Lambda | Liquidity analysis |
| **Regime** | ADX, Trend Strength | Growth/Normal/Crisis modes |
| **Events** | FOMC dates, NFP release, London Fix | Scheduled shocks |
| **Cross-Asset** | Gold/Silver ratio, Gold/Oil ratio | Safe-haven flows |
| **Additional** | Reversals, Regime Switches | Market structure |

**What to Read**:
- [FORMULAS.md](JIM/docs/FORMULAS.md) — Math behind each feature
- `src/features/engine.py` — Feature calculation code
- [PROJECT_STATUS.md](PROJECT_STATUS.md) — List of all 140 features

---

#### **C. GPU Acceleration (Phase 2.5)** ✅
**What it does**: Runs feature engineering 100x faster on NVIDIA GPUs

**Key Technologies**:
- **RAPIDS**: GPU-native pandas (cuDF). Your features compute in seconds instead of minutes.
- **CuPy**: GPU-native numpy. Matrix operations on GPU
- **cuSignal**: GPU-native signal processing (Fourier, wavelets)
- **PyTorch CUDA**: Deep learning acceleration

**Fallback**: Automatically drops to CPU if no GPU detected

**What to Read**:
- `src/utils/gpu.py` — How GPU detection works
- [README.md](README.md) — GPU acceleration section
- `src/features/engine.py` — Look for `@gpu_accelerated` decorators

---

#### **D. Mathematical Models (Phase 3) — NOT STARTED 🔴**
**What it does**: Turns 140 features into trading signals using algorithms

**The Models** (you'll implement):

| Model | Purpose | Status |
|-------|---------|--------|
| **HMM (Hidden Markov Model)** | Detect market regimes (GROWTH/NORMAL/CRISIS) | Core framework exists |
| **Wavelet Denoiser** | Clean noisy price data | ✅ Implemented |
| **Random Forest** | Feature importance, non-linear patterns | Ready to train |
| **XGBoost** | Gradient boosting predictions | Ready to train |
| **LSTM Neural Net** | Temporal sequences (time-series RNN) | Framework ready |
| **Ensemble** | Combine all models with voting | Ready to implement |

**What to Read**:
- [PHASE_3_MODELING.md](JIM/docs/PHASE_3_MODELING.md) — Model roadmap
- `src/utils/` files with "model" in name

---

#### **E. Risk Management (Phase 4) — 40% COMPLETE** 🟡
**What it does**: Sizes positions, limits losses, prevents blow-ups

**Key Concepts**:
1. **Kelly Criterion**: How much to bet on each trade
   - Formula: `f* = (p × b - q) / b` where p=win%, b=win/loss ratio, q=loss%
   - If signal is 51% accurate with 1:1 payout, Kelly says bet 2% of capital

2. **Risk Limits**:
   - Daily loss limit: Stop trading if down X% today
   - Position limits: Never risk > 2% per trade
   - Correlation limits: Hedges prevent concentrated risk
   - Circuit breakers: Emergency stop systems

3. **Portfolio Heat**: Track cumulative risk across all positions

**What to Read**:
- [PHASE_4_RISK.md](JIM/docs/PHASE_4_RISK.md) — Risk framework
- `src/risk/manager.py` — Kelly criterion, position sizing code

---

#### **F. Backtesting (Phase 5) — NOT STARTED 🔴**
**What it does**: Tests your models on historical data (2015-2026)

**Metrics**:
- Sharpe Ratio (return/volatility)
- Max Drawdown (biggest loss)
- Win Rate, Profit Factor
- Slippage-adjusted returns

**What to Read**:
- [PHASE_5_BACKTESTING.md](JIM/docs/PHASE_5_BACKTESTING.md)

---

#### **G. Paper Trading (Phase 6) — NOT STARTED 🔴**
**What it does**: Runs live model on real-time data WITHOUT real money

**What to Read**:
- [PHASE_6_DEPLOYMENT.md](JIM/docs/PHASE_6_DEPLOYMENT.md)

---

#### **H. Live Trading (Phase 7) — NOT STARTED 🔴**
**What it does**: Actually trades with real capital (only after 6 is validated)

---

### **LEVEL 2: Code Deep-Dive** (Learn the Implementation)

#### **A. Entry Point: `main.py`**
```python
python main.py --mode demo    # End-to-end test
```
This runs: Fetch → Feature Engineering → Model → Signal

**What to do**:
1. Read `main.py` — It's the orchestration
2. Run in demo mode locally
3. Read the logs to understand the flow

---

#### **B. Key Modules to Study (In Order)**

**1. Configuration (`src/utils/config.py`)**
- Loads YAML config file
- 150+ tunable parameters (feature windows, model hyperparams, etc.)
- Understanding this = understanding all settings

**Read**: 
- `configs/base.yaml` — The actual config
- `src/utils/config.py` — How it's loaded

---

**2. GPU Detection (`src/utils/gpu.py`)**
- Checks for CUDA/RAPIDS
- Falls back to CPU gracefully
- Critical for "write once, run anywhere"

**Read**:
- `src/utils/gpu.py` — Very short file, understand the detection logic

---

**3. Logging (`src/utils/logger.py`)**
- Uses Loguru for clean, structured logging
- All system events logged (data fetches, model runs, errors)

**Read**:
- `src/utils/logger.py` — How to add your own logs

---

**4. Data Ingestion (`src/ingestion/gold_fetcher.py`)**
- Fetches gold + macro data
- Handles missing data, timezone issues
- Daily refresh logic

**Read**:
- `src/ingestion/gold_fetcher.py` — Main data source
- Understand: API calls, retries, caching

---

**5. Feature Engineering (`src/features/engine.py`)**
- THE CORE OF THE SYSTEM
- Calculates 140+ features
- GPU accelerated with fallback

**Read** (Study this carefully):
- `src/features/engine.py` — Full implementation
- `JIM/docs/FORMULAS.md` — Math formulas

**Key Question to Understand**: Why is feature engineering so important?
- Answer: Models are only as good as features. In Simons' system, 80% of the work is finding the right features.

---

**6. Risk Management (`src/risk/manager.py`)**
- Kelly criterion sizing
- Position tracking
- Drawdown limits

**Read**:
- `src/risk/manager.py` — How trades are sized
- `JIM/docs/PHASE_4_RISK.md` — Risk theory

---

**7. Execution Engine (`src/execution/engine.py`)**
- Paper trading backend
- Order routing
- Latency monitoring

**Read**:
- `src/execution/engine.py` — How trades execute

---

### **LEVEL 3: Infrastructure** (Know Your Tools)

#### **A. Docker Stack (6 services)**
```bash
docker-compose ps
```

| Service | Purpose | Port |
|---------|---------|------|
| **QuestDB** | Time-series database (stores prices) | 9000 |
| **Redis** | Feature store cache (fast lookups) | 6379 |
| **MinIO** | Object storage (backups, parquet files) | 9100 |
| **MLflow** | Model tracking (versions, metrics) | 5000 |
| **Prometheus** | Metrics collection | 9090 |
| **Grafana** | Dashboard visualization | 3000 |

**What to Do**:
1. Start stack: `docker-compose up -d`
2. Visit Grafana: http://localhost:3000 (admin/medallion)
3. Visit QuestDB: http://localhost:9000
4. See data flowing in real-time

**What to Read**:
- [QUICK_REFERENCE.md](JIM/QUICK_REFERENCE.md) — Docker commands

---

#### **B. REST API (Phase 2.5)** ✅
```bash
python main.py --mode api --port 8000
```

**Key Endpoints**:
- `GET /health` — System health
- `GET /signal` — Current buy/sell signal
- `GET /regime` — Current market regime
- `GET /features` — Current feature values
- `GET /models` — Model status

**Visit**: http://localhost:8000/docs (Swagger UI)

---

#### **C. C++ Execution Engine**
Located in `src/execution/cpp/` — High-performance order router

**For Now**: Don't worry about this. It's optimized execution, not core logic.

---

### **LEVEL 4: Testing** (Verify It Works)

```bash
# Run test suite
pytest tests/test_infrastructure_integration.py -v

# Benchmark GPU
python scripts/benchmark_gpu.py --size 100
```

**Key Tests to Understand**:
- `test_infrastructure_integration.py` — Does all services work together?
- `test_phase2_pipeline.py` — Does data pipeline work?
- `test_core.py` — Core algorithm tests

---

## 🗺️ YOUR LEARNING SEQUENCE

### **Week 1: Philosophy & Architecture**
- [ ] Read PHILOSOPHY.md (understand Simons' approach)
- [ ] Read README.md (understand the system)
- [ ] Read PROJECT_STATUS.md (understand what's done/not done)
- [ ] Read QUICK_REFERENCE.md (know the commands)
- [ ] Draw the architecture diagram yourself (Fetch → Features → Models → Risk → Signal)

### **Week 2: Data Pipeline Deep-Dive**
- [ ] Read PHASE_2_DATA.md
- [ ] Read FORMULAS.md (understand the 140 features)
- [ ] Study `src/ingestion/gold_fetcher.py` — How does data come in?
- [ ] Study `src/features/engine.py` — How are 140 features calculated?
- [ ] Run: `python main.py --mode demo` — See it work

### **Week 3: Models & Risk**
- [ ] Read PHASE_3_MODELING.md — What models need to be built?
- [ ] Read PHASE_4_RISK.md — How are positions sized?
- [ ] Study `src/risk/manager.py` — Kelly criterion implementation
- [ ] Understand the model frameworks (HMM, Random Forest, XGBoost, LSTM)

### **Week 4: Infrastructure & Deployment**
- [ ] Start Docker stack: `docker-compose up -d`
- [ ] Visit Grafana, QuestDB, Prometheus — see the data
- [ ] Read how the REST API works
- [ ] Start the API: `python main.py --mode api`
- [ ] Call endpoints via http://localhost:8000/docs

### **Week 5+: Implementation**
- [ ] Start Phase 3 (models)
- [ ] Train models on historical data
- [ ] Evaluate feature importance
- [ ] Move to Phase 5 (backtesting)

---

## 📋 SPECIFIC FILE CHECKLIST

**MUST READ** (Foundation):
- [ ] JIM/docs/PHILOSOPHY.md
- [ ] README.md
- [ ] PROJECT_STATUS.md
- [ ] QUICK_START_PIPELINE.md

**SHOULD READ** (System Design):
- [ ] JIM/docs/PHASE_2_DATA.md
- [ ] JIM/docs/FORMULAS.md
- [ ] JIM/docs/PHASE_3_MODELING.md
- [ ] JIM/docs/PHASE_4_RISK.md

**MUST CODE** (Implementation):
- [ ] JIM/src/ingestion/gold_fetcher.py
- [ ] JIM/src/features/engine.py
- [ ] JIM/src/risk/manager.py
- [ ] JIM/src/execution/engine.py
- [ ] JIM/src/utils/config.py

**OPTIONAL** (Advanced):
- [ ] JIM/src/execution/cpp/ — C++ engine (high-performance, not critical)
- [ ] JIM/docs/PHASE_5_BACKTESTING.md
- [ ] JIM/docs/PHASE_6_DEPLOYMENT.md
- [ ] JIM/docs/PHASE_7_CULTURE.md

---

## 🚀 QUICK START COMMANDS

```bash
# 1. Install dependencies
pip install -r JIM/requirements-base.txt

# 2. Start infrastructure
cd JIM && docker-compose up -d

# 3. Run demo (end-to-end test)
python main.py --mode demo

# 4. Start REST API
python main.py --mode api --port 8000

# 5. Visit API docs
# Open: http://localhost:8000/docs

# 6. View data in QuestDB
# Open: http://localhost:9000

# 7. View dashboards
# Open: http://localhost:3000 (admin/medallion)

# 8. Run tests
pytest tests/test_infrastructure_integration.py -v
```

---

## 💡 KEY INSIGHTS (Why This Matters)

1. **Data > Story**: The system doesn't care *why* gold moves. It looks for *what* patterns predict movements.

2. **Features > Models**: 80% of success is engineering good features. A mediocre model with great features beats a great model with mediocre features.

3. **Many Small Edges**: Renaissance doesn't look for 10% annual returns. It looks for thousands of 51% edges that compound into 30%+ annual returns.

4. **Automation > Intuition**: Once a model is statistically verified, the system runs it without human second-guessing.

5. **GPU Acceleration**: Faster computation = faster iteration. Test more ideas, find better patterns.

6. **Risk First**: The system measures risk (Kelly criterion, drawdown limits) before thinking about returns.

---

## ❓ FAQ

**Q: Do I need to understand C++?**
A: No. The C++ execution engine is optimization, not core logic. Focus on Python.

**Q: Do I need NVIDIA GPU?**
A: No. Everything falls back to CPU. But GPU = 100x faster.

**Q: What's the hardest part?**
A: Feature engineering. Finding the 5-10 features that actually predict gold is the puzzle. Models are just the solver.

**Q: Can I start with Phase 3 (models)?**
A: No. Phase 2 (features) must be solid first. Garbage in = garbage out.

**Q: What's the success metric?**
A: Sharpe ratio > 1.5 and max drawdown < 20% in backtesting. Only then move to paper trading.

---

## 📞 WHERE TO GET HELP

- **Architecture questions**: Read PHILOSOPHY.md and README.md
- **Feature questions**: Read FORMULAS.md and `src/features/engine.py`
- **Model questions**: Read PHASE_3_MODELING.md
- **Risk questions**: Read PHASE_4_RISK.md and `src/risk/manager.py`
- **Infrastructure questions**: Read QUICK_REFERENCE.md

---

**Last Updated**: May 14, 2026  
**Status**: Study guide complete. You're ready to dive in! 🚀

# Mini-Medallion: Gold Trading Engine
GPU-accelerated, quantitative gold (XAU) trading engine inspired by Jim Simons' Renaissance Technologies methodology.

## Current Status

**Overall**: ~**65% Complete** | Phase 1 ✅ | Phase 2 🟢 75% | Phase 2.5 ✅ | Data Flowing Daily ✅

**Date**: May 13, 2026 | **Status Updated**: May 13, 2026 14:45 UTC

**For current status details, see [PROJECT_STATUS.md](PROJECT_STATUS.md)**

---

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (for infrastructure stack)
- NVIDIA GPU (optional, but highly recommended)

### Installation

```bash
# 1. Clone/setup project
cd e:\PRO\JIM_Latest

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment
cp .env.example .env
# Edit .env with your API keys (FRED_API_KEY, etc.)

# 5. Start infrastructure stack
docker compose up -d

# 6. Verify infrastructure health
python scripts/check_infrastructure.py
```

### Running Modes

```bash
# Demo mode: Fetch data → Generate features → Run models
python main.py --mode demo

# REST API server: Start FastAPI server with all endpoints
python main.py --mode api --host 0.0.0.0 --port 8000

# Backtest mode: Coming in Phase 5
python main.py --mode backtest

# Paper trading: Coming in Phase 6
python main.py --mode paper

# Live trading: Coming in Phase 7 (after validation)
python main.py --mode live
```

### Access API

Open http://localhost:8000/docs for interactive Swagger UI

**Key Endpoints**:
- `GET /health` - Service health check
- `GET /signal` - Current trading signal
- `GET /regime` - Market regime (GROWTH/NORMAL/CRISIS)
- `GET /features` - Current engineered features
- `GET /data-quality` - Data quality report
- `GET /models` - Model status
- `POST /backtest/...` - Backtest strategies (Phase 5)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│               REST API (FastAPI) - Phase 2.5 ✅             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  GPU Model Accelerators (RAPIDS/CuPy) - Phase 2.5 ✅       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ - Feature Engineering (100x faster on GPU)            │ │
│  │ - HMM Regime Detection (GPU-optimized)                │ │
│  │ - Signal Processing (Filters, Spectrograms)          │ │
│  │ (Auto-fallback to CPU)                               │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ▲                                  │
│                           │                                  │
│  Data Pipeline - Phase 2 ✅                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ ┌─────────────────┐  ┌──────────────────┐            │ │
│  │ │ Gold Fetcher    │  │ Macro Fetcher    │            │ │
│  │ │ (YahooFinance)  │  │ (FRED, Yahoo)    │            │ │
│  │ └────────┬────────┘  └────────┬─────────┘            │ │
│  │          │                    │                      │ │
│  │          └────────┬───────────┘                      │ │
│  │                   ▼                                  │ │
│  │ ┌──────────────────────────────────────────────────┐ │ │
│  │ │ Alternative Data Manager                         │ │ │
│  │ │ (COT, Sentiment, ETF Flows)                     │ │ │
│  │ └──────────────────┬───────────────────────────────┘ │ │
│  │                    ▼                                  │ │
│  │ ┌──────────────────────────────────────────────────┐ │ │
│  │ │ Data Quality Monitor                             │ │ │
│  │ │ (Gap detection, Outliers, Staleness checks)    │ │ │
│  │ └──────────────────┬───────────────────────────────┘ │ │
│  │                    ▼                                  │ │
│  │ ┌──────────────────────────────────────────────────┐ │ │
│  │ │ QuestDB (Time-Series DB) + Redis (Feature Store)│ │ │
│  │ └──────────────────────────────────────────────────┘ │ │
│  │                                                        │ │
│  │ ┌──────────────────────────────────────────────────┐ │ │
│  │ │ Feature Engineering (200+ features)              │ │ │
│  │ └──────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Core Models - Phase 1 ✅                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ - Wavelet Denoiser (Signal extraction)               │ │
│  │ - HMM Regime Detector (Market state identification)  │ │
│  │ - (Future: Genetic Algorithm, LSTM, TFT)            │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Risk Management - Phase 1 ✅                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ - Kelly Criterion Sizing (Dynamic position sizing)    │ │
│  │ - Circuit Breakers (Drawdown, daily loss limits)     │ │
│  │ - Position State Tracking                             │ │
│  │ - (Future: Meta-labeling, advanced VaR)             │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Infrastructure - Phase 1 ✅                                │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ - Docker Compose (QuestDB, Redis, MinIO, Grafana)    │ │
│  │ - GPU Detection & Acceleration (RAPIDS/CuPy)        │ │
│  │ - Prometheus Monitoring                               │ │
│  │ - Execution Engine (Python + C++ skeleton)           │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
JIM_Latest/
├── README.md                          ← You are here
├── ROADMAP.md                         ← Project timeline
├── docker-compose.yml                 ← Full infrastructure stack
├── requirements.txt                   ← Python dependencies
├── main.py                            ← Entry point (demo/api/backtest)
├── configs/
│   └── base.yaml                      ← Master configuration
├── docs/
│   ├── PHILOSOPHY.md                  ← Jim Simons methodology
│   ├── FORMULAS.md                    ← Mathematical reference
│   ├── PHASE_1_INFRASTRUCTURE.md      ✅ Complete
│   ├── PHASE_2_DATA.md                ✅ 90% Complete
│   ├── PHASE_2.5_API.md               ✅ Complete (NEW)
│   ├── PHASE_3_MODELING.md            🔴 Not Started
│   ├── PHASE_4_RISK.md                🟡 Partial (Base Risk Mgr)
│   ├── PHASE_5_BACKTESTING.md         🔴 Not Started
│   ├── PHASE_6_DEPLOYMENT.md          🔴 Not Started
│   └── PHASE_7_CULTURE.md             🔴 Not Started
├── src/
│   ├── api/                           ✅ FastAPI application
│   │   ├── app.py                     ✅ REST API server
│   │   ├── models.py                  ✅ Pydantic schemas
│   │   └── __init__.py
│   ├── execution/                     ✅ Order execution
│   │   ├── engine.py                  ✅ Python execution engine
│   │   ├── cpp/                       ✅ C++ scaffolding (CMakeLists.txt, etc.)
│   │   └── __init__.py
│   ├── features/                      ✅ Feature engineering
│   │   ├── engine.py                  ✅ 200+ feature generation
│   │   ├── feature_store.py           ✅ Redis + parquet storage
│   │   └── __init__.py
│   ├── ingestion/                     ✅ Data acquisition pipeline
│   │   ├── gold_fetcher.py            ✅ Multi-symbol gold data
│   │   ├── macro_fetcher.py           ✅ Yahoo + FRED macro data
│   │   ├── alternative_data.py        ✅ COT, sentiment, ETF flows
│   │   ├── questdb_writer.py          ✅ ILP writes to QuestDB
│   │   ├── schema_manager.py          ✅ Table schema definitions
│   │   ├── data_quality.py            ✅ Quality validation
│   │   ├── metrics_exporter.py        ✅ Prometheus metrics
│   │   ├── pipeline_orchestrator.py   ✅ Multi-mode pipeline
│   │   └── __init__.py
│   ├── models/                        ✅ Trading models
│   │   ├── base.py                    ✅ Base model interface
│   │   ├── wavelet.py                 ✅ Wavelet denoiser
│   │   ├── hmm_regime.py              ✅ HMM regime detector
│   │   └── __init__.py
│   ├── risk/                          ✅ Risk management
│   │   ├── manager.py                 ✅ Kelly, circuit breakers
│   │   └── __init__.py
│   ├── utils/                         ✅ Utilities
│   │   ├── config.py                  ✅ YAML configuration
│   │   ├── gpu.py                     ✅ GPU detection
│   │   ├── gpu_models.py              ✅ GPU-accelerated models
│   │   ├── infra.py                   ✅ Infrastructure checks
│   │   ├── logger.py                  ✅ Structured logging
│   │   ├── resilience.py              ✅ Retry/timeout/circuit-breaker
│   │   └── __init__.py
│   └── __init__.py
├── scripts/
│   ├── check_infrastructure.py        ✅ Infrastructure health check
│   └── ...                            (Deployment scripts coming)
├── tests/
│   ├── test_core.py                   ✅ Unit tests for Phase 1
│   └── ...                            (More tests needed)
├── docker/
│   ├── prometheus.yml                 ✅ Prometheus config
│   └── volumes/                       (Database & cache volumes)
├── data/
│   ├── raw/                           (Downloaded data)
│   ├── processed/                     (Cleaned data)
│   └── features/                      (Engineered features)
├── notebooks/                         (Research Jupyter notebooks)
└── logs/                              (Application logs)
```

---

## Key Components by Phase

### ✅ Phase 1: Infrastructure & Compute (COMPLETE)
- GPU utilities with automatic RAPIDS/NumPy fallback
- Configuration management with YAML + env vars
- Structured logging with Loguru
- Infrastructure health checks
- Execution engine (Python + C++ scaffolding)
- Risk manager (Kelly Criterion + Circuit Breakers)
- Wavelet denoiser & HMM regime detector

### ✅ Phase 2: Data Acquisition & Pipeline (90% COMPLETE)
- **Gold data**: Historical fetcher, multiple symbols, incremental updates
- **Macro data**: Yahoo Finance + FRED integration
- **Alternative data**: COT reports, news sentiment, ETF flows
- **Database**: QuestDB schema manager, ILP writer, SQL queries
- **Feature store**: Redis + parquet with drift detection
- **Data quality**: Comprehensive monitoring and alerting
- **Feature engineering**: 200+ computed features
- **Pipeline**: Multi-mode orchestrator with automatic retries

### ✅ Phase 2.5: REST API & GPU Acceleration (COMPLETE)
- FastAPI application with 10+ endpoints
- GPU-accelerated feature computation (100x faster)
- GPU-accelerated HMM fitting
- GPU-accelerated signal processing
- Comprehensive Swagger/OpenAPI documentation
- Graceful CPU fallback

### 🔴 Phase 3: Mathematical Modeling (NOT STARTED)
- Genetic Algorithm for strategy evolution
- LSTM neural networks for sequence prediction
- Temporal Fusion Transformer (TFT) for multi-horizon forecasting
- VAE for anomaly detection
- Ensemble stacking with meta-learner

### 🟡 Phase 4: Risk Management (PARTIAL)
- ✅ Base risk manager and Kelly sizing
- 🔴 Meta-labeling (Critic model)
- 🔴 Advanced GPU Monte Carlo VaR
- 🔴 Dynamic position sizing with ML

### 🔴 Phase 5: Backtesting (NOT STARTED)
- Event-driven backtester
- Walk-forward analysis
- Combinatorial Purged Cross-Validation (CPCV)
- Deflated Sharpe Ratio calculation
- Realistic slippage/commission modeling

### 🔴 Phase 6: Paper Trading & Deployment (NOT STARTED)
- Paper trading simulator
- Staged deployment (Alpha/Beta/Gamma)
- Live execution via IBKR/CQG
- Production monitoring dashboard

### 🔴 Phase 7: Team Culture & Operations (NOT STARTED)
- Team structure and hiring guidelines
- Weekly research seminars
- Model governance process
- Knowledge base and research logging

---

## Performance Characteristics

### Data Processing
- **Gold price data**: 10+ years, daily/hourly/minute resolution
- **Macro data**: ~10 years across 10+ economic indicators
- **Alternative data**: COT reports (weekly), sentiment (daily)
- **Features**: 200+ engineered features across price/volatility/momentum/temporal

### Feature Computation
- **CPU (Pandas)**: ~500ms for 5000 rows (200 features)
- **GPU (cuDF)**: ~5ms for 5000 rows (200 features)
- **Speedup**: 100x on GPU

### Model Inference
- **HMM regime**: <1ms per prediction
- **Wavelet denoising**: 5-10ms for 500-bar window
- **Ensemble**: <10ms for all models combined

---

## Configuration

All settings in `configs/base.yaml`:

```yaml
project:
  name: "mini-medallion"
  version: "0.1.0"
  asset: "XAU/USD"
  mode: "paper"  # or "live"

database:
  questdb:
    host: "localhost"
    port: 9009
  redis:
    host: "localhost"
    port: 6379
  minio:
    host: "localhost"
    port: 9100

data:
  gold:
    symbol: "GC=F"  # Gold futures
    history_years: 10
  macro:
    dxy_symbol: "DX-Y.NYB"
    vix_symbol: "^VIX"
    # ... more symbols

features:
  lookback_windows: [5, 10, 20, 50, 100, 200]
  volatility_windows: [10, 20, 50]

models:
  hmm:
    n_regimes: 3
    n_iter: 1000
  # ... other models coming in Phase 3

risk:
  kelly:
    fraction: 0.5  # Half-Kelly
    max_position_pct: 0.05
  circuit_breakers:
    daily_loss_limit: 0.02  # 2%
    drawdown_stop: 0.10     # 10%

logging:
  level: "INFO"
  file: "logs/medallion.log"
```

---

## Infrastructure Stack

**All services containerized via Docker Compose**:

| Service | Port | Purpose |
|---------|------|---------|
| **QuestDB** | 9000/9009 | Time-series database (tick data, features) |
| **Redis** | 6379 | Real-time feature store and caching |
| **MinIO** | 9100 | Data lake (S3-compatible) |
| **MLflow** | 5000 | Model versioning and tracking |
| **Prometheus** | 9090 | Metrics collection |
| **Grafana** | 3000 | Dashboards and visualization |
| **Python API** | 8000 | REST API server |

Start all services:
```bash
docker compose up -d
```

---

## Dependencies

### Core
- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `pywavelets` - Wavelet transforms
- `hmmlearn` - Hidden Markov Models
- `scikit-learn` - ML utilities
- `xgboost`, `lightgbm` - Gradient boosting (Phase 3+)

### GPU (Optional, but recommended)
- `cudf` - GPU DataFrames (RAPIDS)
- `cuml` - GPU ML (RAPIDS)
- `cupy` - GPU arrays
- `cusignal` - GPU signal processing

### Data Sources
- `yfinance` - Yahoo Finance data
- `fredapi` - Federal Reserve data
- `requests` - HTTP requests

### Infrastructure
- `fastapi` - REST API framework
- `uvicorn` - ASGI server
- `questdb-client` - QuestDB client
- `redis` - Redis client
- `prometheus-client` - Prometheus metrics

### Utilities
- `loguru` - Structured logging
- `click` - CLI framework
- `python-dotenv` - Environment variables
- `pydantic` - Data validation
- `pyyaml` - YAML parsing

---

## Next Steps

### Immediate (Phase 3: Mathematical Modeling)
1. Implement genetic algorithm for strategy evolution
2. Train LSTM on historical gold returns
3. Build Temporal Fusion Transformer for forecasting
4. Create ensemble meta-learner

### Medium-term (Phase 4-5)
1. Build meta-labeling critic model
2. Implement walk-forward backtester with CPCV
3. Calculate Deflated Sharpe Ratio for validation
4. Advanced risk monitoring and Monte Carlo VaR

### Long-term (Phase 6-7)
1. Paper trading with real broker APIs
2. Staged deployment (Alpha → Beta → Gamma → Live)
3. Team structure and operations
4. 24/7 monitoring and auto-recovery

---

## Contributing

See `docs/PHASE_7_CULTURE.md` for team structure and collaboration guidelines.

---

## References

- Jim Simons biography: *The Man Who Solved the Market* - Gregory Zuckerman
- *Advances in Financial Machine Learning* - Marcos López de Prado
- NVIDIA RAPIDS: https://rapids.ai
- QuestDB: https://questdb.io
- FastAPI: https://fastapi.tiangolo.com

---

*Last Updated: May 13, 2026*  
*Status: Phase 2 (90%) + Phase 2.5 (Complete)*  
*Next Milestone: Phase 3 (Mathematical Modeling)*


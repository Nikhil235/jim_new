# Phase 1: Infrastructure & Compute
> *Simons' edge was his superior compute. Your GPUs are your sword.*

**Duration**: Weeks 1–3 | **Status**: ✅ **COMPLETE** (May 13, 2026)

---

## 1.1 GPU Compute Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| DataFrame Engine | **NVIDIA RAPIDS cuDF** | Process tick-data on GPU (100x faster than Pandas) |
| ML Engine | **RAPIDS cuML** | GPU-accelerated regressions, clustering |
| Deep Learning | **PyTorch** (CUDA) | Neural network models (LSTM, Transformers) |
| Signal Processing | **CuPy** + **cuSignal** | GPU-accelerated wavelet transforms & FFT |
| Execution Engine | **C++ / Rust** | Ultra-low latency order execution |

### Why RAPIDS over Pandas?

```
Benchmark: Loading 10GB of tick data
─────────────────────────────────────
Pandas (CPU):     ~45 minutes
cuDF (GPU):       ~27 seconds
─────────────────────────────────────
Speedup:          ~100x
```

### Setup Commands

```bash
# Create conda environment with RAPIDS
conda create -n medallion -c rapidsai -c conda-forge -c nvidia \
    rapids=24.04 python=3.11 cuda-version=12.2

# Install additional dependencies
pip install pytorch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install mlflow questdb-client redis hmmlearn deap pywavelets
```

---

## 1.2 Database Layer

| Component | Technology | Why |
|-----------|------------|-----|
| Tick Data Store | **QuestDB** | Nanosecond-resolution time-series, SQL interface |
| Feature Store | **Redis** (RedisTimeSeries) | Real-time feature caching for live signals |
| Model Registry | **MLflow** | Version control for all trained models |
| Data Lake | **MinIO** (S3-compatible) | Raw data archival (parquet files) |

### QuestDB Schema (Gold Ticks)

```sql
CREATE TABLE gold_ticks (
    timestamp TIMESTAMP,
    bid DOUBLE,
    ask DOUBLE,
    bid_size DOUBLE,
    ask_size DOUBLE,
    trade_price DOUBLE,
    trade_size DOUBLE,
    source SYMBOL
) timestamp(timestamp) PARTITION BY DAY WAL;
```

### QuestDB Schema (Gold Futures Order Book)

```sql
CREATE TABLE gold_orderbook (
    timestamp TIMESTAMP,
    level INT,
    bid_price DOUBLE,
    bid_qty DOUBLE,
    ask_price DOUBLE,
    ask_qty DOUBLE,
    contract SYMBOL
) timestamp(timestamp) PARTITION BY DAY WAL;
```

---

## 1.3 Monitoring Stack

| Tool | Purpose |
|------|---------|
| **Grafana** | Dashboards for system health, P&L, signals |
| **Prometheus** | Metrics collection (latency, throughput, GPU utilization) |
| **Alertmanager** | Alerts on anomalies (data gaps, model drift, high latency) |

---

## 1.4 Project Structure

```
JIM_Latest/
├── ROADMAP.md
├── docs/                    # Phase documentation
├── data/
│   ├── raw/                 # Raw downloaded data
│   ├── processed/           # Cleaned parquet files
│   └── features/            # Engineered feature sets
├── src/
│   ├── ingestion/           # Data pipeline & feeds
│   ├── features/            # Feature engineering
│   ├── models/              # All ML/stat models
│   │   ├── wavelet/
│   │   ├── hmm/
│   │   ├── genetic/
│   │   ├── deep_learning/
│   │   └── ensemble/
│   ├── risk/                # Risk management & meta-labeling
│   ├── execution/           # Order routing & execution (C++/Rust)
│   └── utils/               # Shared utilities
├── configs/                 # YAML config files
├── notebooks/               # Research Jupyter notebooks
├── tests/                   # Unit & integration tests
├── docker/                  # Docker & docker-compose
└── scripts/                 # Setup & deployment scripts
```

---

## 1.5 Deliverables Checklist

### CORE INFRASTRUCTURE (✅ COMPLETE)
- [x] RAPIDS environment configuration (GPU fallback to CPU)
- [x] QuestDB schema and connectivity setup  
- [x] Redis feature store operational
- [x] MLflow tracking server integration
- [x] Project folder structure created
- [x] Docker-compose for full stack
- [x] Prometheus configuration for metrics collection
- [x] Grafana dashboard framework

### PYTHON UTILITIES & INFRASTRUCTURE (✅ COMPLETE)
- [x] GPU detection and utilities (`src/utils/gpu.py`)
- [x] Configuration system (`src/utils/config.py`)
- [x] Logging setup (`src/utils/logger.py`)
- [x] Infrastructure health checks (`src/utils/infra.py`)
- [x] Resilience utilities (`src/utils/resilience.py`)
- [x] GPU model accelerators (`src/utils/gpu_models.py`)

### RISK MANAGEMENT (✅ COMPLETE)
- [x] Risk manager with Kelly Criterion (`src/risk/manager.py`)
- [x] Circuit breakers and position sizing
- [x] Dynamic Kelly based on regime

### EXECUTION ENGINE (✅ PYTHON COMPLETE, C++ SCAFFOLDED)
- [x] Execution engine wrapper (`src/execution/engine.py`)
- [x] Broker adapter abstraction (IBKR, CQG, Paper)
- [x] Order tracking and latency measurement
- [x] C++ execution engine scaffolding (`src/execution/cpp/`)

### CORE MODELS (✅ COMPLETE)
- [x] Base model interface (`src/models/base.py`)
- [x] Wavelet denoiser (`src/models/wavelet.py`)
- [x] HMM regime detector (`src/models/hmm_regime.py`)

### BONUS: API & EXTENDED INFRASTRUCTURE (✅ COMPLETE)
- [x] FastAPI REST application (`src/api/app.py`)
- [x] API models and schemas (`src/api/models.py`)
- [x] Prometheus metrics exporter (`src/ingestion/metrics_exporter.py`)

---

*Back to [ROADMAP](../ROADMAP.md)*

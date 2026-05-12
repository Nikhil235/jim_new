# Phase 1: Infrastructure & Compute
> *Simons' edge was his superior compute. Your GPUs are your sword.*

**Duration**: Weeks 1–3 | **Status**: � In Progress

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

## 1.5 Deployment Guide

### Option A: Automated Deployment (Recommended)

**Linux/macOS:**
```bash
bash scripts/deploy.sh
```

**Windows (PowerShell):**
```powershell
.\scripts\deploy.bat
```

### Option B: Manual Deployment

#### Step 1: Start Docker Stack
```bash
docker-compose up -d
```

Verify all services are running:
```bash
docker-compose ps
```

Expected output (6 services):
```
NAME                 STATUS              PORTS
medallion-questdb    Up (healthy)        9000, 9009, 8812
medallion-redis      Up                  6379
medallion-minio      Up                  9100, 9001
medallion-mlflow     Up                  5000
medallion-prometheus Up                  9090
medallion-grafana    Up                  3000
```

#### Step 2: Initialize QuestDB Tables

Connect to QuestDB SQL interface (port 8812 — PostgreSQL wire protocol):
```bash
psql -h localhost -p 8812 -d qdb -U admin -c "
CREATE TABLE IF NOT EXISTS gold_ticks (
    timestamp TIMESTAMP,
    bid DOUBLE,
    ask DOUBLE,
    bid_size DOUBLE,
    ask_size DOUBLE,
    trade_price DOUBLE,
    trade_size DOUBLE,
    source SYMBOL
) timestamp(timestamp) PARTITION BY DAY WAL;
"
```

Or via HTTP (REST API):
```bash
curl -X POST \
  -d 'CREATE TABLE gold_ticks (timestamp TIMESTAMP, bid DOUBLE, ask DOUBLE, bid_size DOUBLE, ask_size DOUBLE, trade_price DOUBLE, trade_size DOUBLE, source SYMBOL) timestamp(timestamp) PARTITION BY DAY WAL;' \
  http://localhost:9000/exec
```

#### Step 3: Create MinIO Bucket
```bash
docker-compose exec minio mc mb minio/medallion-data
```

#### Step 4: Verify Connectivity
```bash
python scripts/check_infrastructure.py
```

---

### Service URLs

| Service | URL | Default Creds |
|---------|-----|---|
| **QuestDB** | http://localhost:9000 | admin / quest |
| **QuestDB SQL** | localhost:8812 (PgSQL) | admin / quest |
| **Redis** | localhost:6379 | (no auth) |
| **MinIO** | http://localhost:9100 | minioadmin / minioadmin |
| **MLflow** | http://localhost:5000 | (no auth) |
| **Prometheus** | http://localhost:9090 | (no auth) |
| **Grafana** | http://localhost:3000 | admin / medallion |

---

## 1.6 Troubleshooting

### Docker Issues

**Error: "Cannot connect to Docker daemon"**
- Ensure Docker Desktop is running (Windows/macOS)
- On Linux, verify `sudo usermod -aG docker $USER` (then log out/in)
- Check Docker context: `docker context ls`

**Error: "Ports already in use"**
- Find process using port: `lsof -i :PORT` (macOS/Linux) or `netstat -ano | findstr :PORT` (Windows)
- Override ports in `docker-compose.override.yml`:
  ```yaml
  services:
    questdb:
      ports:
        - "9001:9000"  # External:Internal
  ```

**Error: "Out of memory"**
- Increase Docker memory allocation in Settings
- Reduce Redis memory: `docker-compose exec redis redis-cli CONFIG SET maxmemory 1gb`

### Connectivity Issues

**Redis connection fails**
- Verify Redis is running: `docker-compose ps | grep redis`
- Test connectivity: `redis-cli ping`

**QuestDB connection fails**
- Check HTTP API: `curl http://localhost:9000/status`
- Check SQL port (8812): `psql -h localhost -p 8812 -d qdb -U admin -c "SELECT 1"`

**MinIO access denied**
- Verify credentials in `docker-compose.yml`
- Check bucket exists: `docker-compose exec minio mc ls minio`

### Performance Issues

**GPU not detected**
- Verify NVIDIA driver: `nvidia-smi`
- Check CUDA installation: `nvcc --version`
- Rebuild PyTorch for CUDA: `pip install torch --index-url https://download.pytorch.org/whl/cu121 --force-reinstall`

**CPU-only mode**
- Use `requirements-cpu.txt`: `pip install -r requirements-base.txt -r requirements-cpu.txt`
- Benchmark with `python scripts/benchmark_gpu.py --gpu-only` to compare

---

## 1.7 Monitoring Dashboards

### Prometheus Metrics
Access: http://localhost:9090/targets

Key metrics to scrape:
- `questdb_rows_ingested_total` — ticks inserted
- `questdb_query_latency_ms` — query response time
- `redis_connected_clients` — active Redis connections
- `container_cpu_usage_seconds_total` — Docker container CPU

### Grafana Dashboards
Access: http://localhost:3000

Pre-built dashboards available in `docker/grafana/dashboards/`:
- `system_health.json` — CPU, memory, disk
- `questdb_performance.json` — database metrics
- `trading_signals.json` — signal generation latency

Import via Grafana UI: Configuration → Data Sources → Add QuestDB/Prometheus → Create Dashboard

---

## 1.8 Deliverables Checklist

- [x] RAPIDS environment setup scripts (requirements-gpu.txt + setup docs)
- [x] QuestDB instance deployed and schema defined
- [x] Redis feature store operational
- [x] MLflow tracking server running
- [x] C++ execution engine skeleton (order_router, order_book, latency_monitor)
- [x] Build system (CMakeLists.txt + build scripts for Windows/Linux)
- [x] Automated deployment scripts (deploy.sh, deploy.bat)
- [x] Infrastructure health check script (check_infrastructure.py)
- [x] Integration tests (test_infrastructure_integration.py)
- [x] GPU detection & benchmark tools (benchmark_gpu.py)
- [x] Monitoring foundation (Prometheus + Grafana containers)
- [x] Project folder structure created
- [x] Docker-compose for full stack
- [ ] RAPIDS environment running on all GPUs *(pending: conda install)*
- [ ] CI/CD pipeline for model deployment *(Phase 2)*
- [ ] Live monitoring dashboard *(Phase 2)*

---

## 1.9 Next Steps

1. **Build C++ Execution Engine**
   ```bash
   # Linux/macOS
   bash scripts/build_execution_engine.sh
   
   # Windows (requires Visual Studio or MinGW)
   scripts\build_execution_engine.bat
   ```

2. **Run GPU Benchmark** (if CUDA available)
   ```bash
   python scripts/benchmark_gpu.py --size 100 --iterations 3
   ```

3. **Run Integration Tests**
   ```bash
   pytest tests/test_infrastructure_integration.py -v
   ```

4. **Proceed to Phase 2: Data Ingestion Pipeline**
   - Implement `src/ingestion/gold_fetcher.py` to download tick data
   - Create data validation pipeline
   - Set up automated feeds from data providers

---

*Back to [ROADMAP](../ROADMAP.md)*


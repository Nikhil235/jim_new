# QUICK REFERENCE: Mini-Medallion Commands
**Mini-Medallion Gold Trading Engine**  
**Last Updated**: May 13, 2026

🔗 **For complete status, see [PROJECT_STATUS.md](PROJECT_STATUS.md)**

---

## 🚀 QUICK START (5 minutes)

### 1. Deploy Docker Stack
```powershell
.\scripts\deploy.bat                           # Windows
# OR
bash scripts/deploy.sh                         # Linux/macOS
```

### 2. Build C++ Engine
```powershell
.\scripts\build_execution_engine.bat           # Windows
# OR
bash scripts/build_execution_engine.sh         # Linux/macOS
```

### 3. Run Tests
```bash
pytest tests/test_infrastructure_integration.py -v
```

### 4. Benchmark GPU
```bash
python scripts/benchmark_gpu.py --size 100
```

---

## 🔗 SERVICE ENDPOINTS

| Service | URL | Credentials |
|---------|-----|---|
| **QuestDB** | http://localhost:9000 | admin / quest |
| **Redis** | localhost:6379 | (none) |
| **MinIO** | http://localhost:9100 | minioadmin / minioadmin |
| **MLflow** | http://localhost:5000 | (none) |
| **Prometheus** | http://localhost:9090 | (none) |
| **Grafana** | http://localhost:3000 | admin / medallion |

---

## 📋 DEPENDENCY INSTALLATION

### CPU Only
```bash
pip install -r requirements-base.txt -r requirements-cpu.txt
```

### GPU (Requires CUDA 12.x)
```bash
# Option 1: conda (recommended for RAPIDS)
conda create -n medallion -c rapidsai -c conda-forge -c nvidia rapids=24.04 python=3.11
conda activate medallion

# Option 2: pip (PyTorch only)
pip install -r requirements-base.txt -r requirements-gpu.txt
```

---

## 🛠️ BUILD COMMANDS

### C++ Execution Engine
```bash
# Auto-detect compiler & CUDA
bash scripts/build_execution_engine.sh     # Unix
.\scripts\build_execution_engine.bat       # Windows

# Manual CMake
cd src/execution/cpp
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release -DENABLE_CUDA=ON ..
make  # or cmake --build . --config Release
./order_router_demo
```

---

## 📊 DOCKER COMMANDS

### Start/Stop Stack
```bash
docker-compose up -d                       # Start all services
docker-compose down                        # Stop all services
docker-compose ps                          # Show status
docker-compose logs -f [service]           # View logs

# Services: questdb, redis, minio, mlflow, prometheus, grafana
```

### Restart Specific Service
```bash
docker-compose restart redis
docker-compose up -d questdb               # Just QuestDB
```

### View Service Logs
```bash
docker-compose logs questdb                # All logs
docker-compose logs -f grafana --tail=50   # Last 50 lines, follow
```

---

## 🔍 VERIFICATION COMMANDS

### Check Infrastructure Health
```bash
python scripts/check_infrastructure.py
```

### Verify GPU
```bash
python -c "import torch; print('GPU:', torch.cuda.is_available()); print('Devices:', torch.cuda.device_count())"
```

### Verify RAPIDS
```bash
python -c "import cudf; print('cuDF available:', cudf.__version__)"
```

### Test Redis Connection
```bash
redis-cli ping                              # Should return: PONG
```

### Test QuestDB Connection
```bash
curl http://localhost:9000/status           # HTTP health check
psql -h localhost -p 8812 -d qdb -U admin   # SQL connection (if psql installed)
```

---

## ⚠️ TROUBLESHOOTING

### Docker not running
```powershell
# Check Docker status
docker --version
docker ps

# Restart Docker daemon
docker context use desktop-linux
docker-compose up -d
```

### Port already in use
```bash
# Find process using port (example: 9000)
# Windows:
netstat -ano | findstr :9000

# Linux/macOS:
lsof -i :9000
```

### Python import errors
```bash
# Add project to PYTHONPATH
set PYTHONPATH=%PYTHONPATH%;e:\PRO\JIM_Latest        # Windows
export PYTHONPATH=$PYTHONPATH:/path/to/JIM_Latest    # Unix

# Or install as editable package
pip install -e .
```

### GPU not detected
```bash
# Verify NVIDIA driver
nvidia-smi

# Check PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Reinstall PyTorch for CUDA
pip install torch --index-url https://download.pytorch.org/whl/cu121 --force-reinstall
```

---

## 📁 KEY FILES

```
Phase 1 Infrastructure Files:
├── docker-compose.yml              ← Start here: docker-compose up -d
├── scripts/
│   ├── deploy.sh/.bat              ← Automated deployment
│   ├── build_execution_engine.sh/.bat ← Build C++ engine
│   └── benchmark_gpu.py            ← GPU performance test
├── src/execution/cpp/
│   ├── CMakeLists.txt              ← Build configuration
│   └── src/main.cpp                ← Demo program
├── tests/
│   └── test_infrastructure_integration.py ← Run: pytest
└── docs/
    └── PHASE_1_INFRASTRUCTURE.md   ← Full documentation
```

---

## 🎯 PHASE 1 CHECKLIST

- [x] Docker stack configured (6 services)
- [x] GPU detection implemented
- [x] C++ execution engine skeleton built
- [x] Deployment scripts created
- [x] Integration tests written
- [x] Documentation completed
- [ ] Docker daemon started (manual: open Docker Desktop)
- [ ] C++ code compiled (`build_execution_engine.bat`)
- [ ] Integration tests passing (`pytest`)
- [ ] GPU benchmark completed (`benchmark_gpu.py`)

---

## 🔗 NEXT: PHASE 2 DATA INGESTION

After Phase 1 is verified:
1. Implement `src/ingestion/gold_fetcher.py`
2. Create data validation pipeline
3. Set up automated data feeds
4. See: `docs/PHASE_2_DATA.md`

---

**Last Update**: May 11, 2026  
**Status**: Phase 1 Complete ✅ (awaiting Docker daemon verification)

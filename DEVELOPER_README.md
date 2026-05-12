DEVELOPER QUICK START — Mini‑Medallion
=====================================

Purpose
-------
One-page developer guide: quick commands, where to edit core components, and next steps.

Quick environment & run
-----------------------
(Assumes Windows / PowerShell; adapt for Unix shells)

Create venv and install:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # PowerShell
python -m pip install -r requirements.txt
```

Optional GPU extras (if using CUDA/cu12):

```bash
python -m pip install -e .[gpu]
```

Start infrastructure (Docker Compose):

```bash
docker compose up -d
```

Health check & demo

```bash
python scripts/check_infrastructure.py
python main.py --mode demo
```

Run tests

```bash
pytest -q
```

Where to change things (map)
----------------------------
- Config: `src/utils/config.py` and `configs/base.yaml` — central configuration and env var substitution.
- Ingestion: `src/ingestion/gold_fetcher.py` — change data sources, intervals, or add API keys.
- Feature engineering: `src/features/engine.py` — add/modify engineered features and feature pipeline order.
- Models:
  - Base interface: `src/models/base.py` — training/predict/save/load contract.
  - Wavelet: `src/models/wavelet.py` — denoising/transform logic.
  - HMM: `src/models/hmm_regime.py` — regime detection hyperparams.
- Risk: `src/risk/manager.py` — Kelly sizing, circuit breaker rules, portfolio checks.
- Execution: `src/execution/engine.py` — broker adapters and order submission flow (placeholder for live integrations).
- Utilities:
  - Logging: `src/utils/logger.py` — log format/rotation.
  - GPU detection: `src/utils/gpu.py` — detection and RAPIDS fallback logic.

Where the pipeline is wired
--------------------------
- Entry point: `main.py` — selects mode and runs the demo pipeline (fetch → features → models → risk → execution).

Important files
---------------
- Dependency list: `requirements.txt` and `pyproject.toml` (gpu extras).
- Docker services: `docker-compose.yml` (QuestDB, Redis, MinIO, MLflow, Prometheus, Grafana).

Quick development tips
----------------------
- Use small sample data in `notebooks/` or generate synthetic data (demo path does this automatically on fetch failure).
- If iterating on models, implement `save()`/`load()` to facilitate `mlflow` artifact tracking.
- For execution testing, use `ExecutionEngine`'s simulated flows before wiring a broker.

Next suggested actions
----------------------
- Run `pytest` and address failing tests (if any).
- Pick one component to extend (e.g., add a new feature in `src/features/engine.py`).
- Harden config/secret handling for non-local deployments.

Contact
-------
If you want, I can:
- Run the test suite and report results.
- Create a developer checklist file with Git hooks and recommended pre-commit settings.
- Scaffold a `CONTRIBUTING.md` with coding standards and PR checklist.


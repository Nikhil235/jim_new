# Mini-Medallion

GPU-accelerated Gold (XAU) Trading Engine inspired by Jim Simons.

## Phase 1: Infrastructure & Compute

This project is building the Phase 1 infrastructure stack:
- Docker Compose for QuestDB, Redis, MinIO, MLflow, Prometheus, Grafana
- YAML-based configuration with environment variable substitution
- GPU detection and RAPIDS-aware fallback
- Core data ingestion, feature engine, model skeletons, and risk manager
- Execution engine skeleton for future order routing
- Infrastructure health check script

## Quick Start

1. Install Python 3.11+.
2. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
python -m pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and populate secret values.
4. Start the infrastructure stack:

```bash
docker compose up -d
```

5. Run the infrastructure health check:

```bash
python scripts/check_infrastructure.py
```

6. Run the demo pipeline:

```bash
python main.py --mode demo
```

## Notes

- The project is currently in Phase 1 infrastructure development.
- Production trading paths are placeholders and not yet live.
- See `docs/PHASE_1_INFRASTRUCTURE.md` for detailed Phase 1 deliverables.

# 🏆 Mini-Medallion: Gold (XAU) Trading Engine

> *"We are right 50.75% of the time, but we are 100% right 50.75% of the time."*
> 
> — Inspired by Jim Simons' Renaissance Technologies

**Mini-Medallion** is a production-grade, highly autonomous algorithmic trading engine designed specifically to trade Gold (XAU/USD). Built on a "Radical Empiricism" philosophy (trusting data over narrative and finding non-obvious invariants), the system utilizes a multi-model machine learning ensemble architecture operating 24/7.

---

## 🏗️ Architecture Overview

The system runs on a 7-model machine learning ensemble aggregated via a Stacking Meta-Learner to produce `LONG/SHORT/HOLD` signals. 

### Core Components
- **Data Ingestion & Features:** Automates fetching of tick data, macro indicators (DXY, US10Y, Silver), and sentiment analysis.
- **Ensemble Engine:** Incorporates 7 diverse models including **WaveletPro** (frequency-domain analysis), **HMM Pro** (temporal regime detection), LSTM, Temporal Fusion Transformers (TFT), Genetic Algorithms, and NLP.
- **Risk Management (The "Shield"):** Validates trades using a Meta-Label Critic (must be > 65% confident), sizes positions via Dynamic Kelly / Half-Kelly Criterion, and enforces circuit breakers (e.g., Max Drawdown 10%). GPU Monte Carlo VaR simulations run continuously.
- **Execution:** Paper Trading Engine with realistic slippage/commission models, and a low-latency C++ order router slated for Interactive Brokers.

### Advanced Modeling
1. **WaveletPro**: Uses a 6-level DWT (db4 wavelet) for decomposition, extracting a Wavelet Oscillator for mid-term cycles. Applies soft thresholding for denoising and Morlet CWT for volatility. Generates 36 features with ~10-15ms inference latency.
2. **HMM Pro**: GMMHMM tracking 4 market regimes (Bullish, Neutral, Bearish, Reversal). Integrates macro data with automatic feature dimension padding. ~19ms inference latency.

---

## 🛠️ Technology Stack

- **Compute & Deep Learning:** PyTorch (CUDA), NVIDIA RAPIDS (cuDF, cuML), CuPy, cuSignal.
- **Data Storage & Pipeline:** QuestDB (Tick Data), Redis (Feature Store), MinIO (Data Lake), Kafka.
- **MLOps & Monitoring:** MLflow (Model Registry), Prometheus, Grafana.
- **Execution:** Python (Research/Paper Trading), C++ (Live Order Router).
- **Deployment:** Docker Compose stack.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- Docker & Docker Compose
- NVIDIA GPU (Recommended) with CUDA toolkit installed

### 2. Installation
```bash
# Clone the repository
git clone <repository-url>
cd jim_new

# Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
python -m pip install -r requirements.txt
```

### 3. Launching the Infrastructure
Copy `.env.example` to `.env` and populate any required secret values. Then start the infrastructure stack:
```bash
docker compose up -d
```
You can run the infrastructure health check to verify the services:
```bash
python scripts/check_infrastructure.py
```

### 4. Running the Pipeline
To run a demo of the current trading pipeline:
```bash
python main.py --mode demo
```

---

## 🗺️ Project Roadmap (7 Phases)

The project follows a strict 7-phase roadmap, ensuring robust infrastructure before live capital deployment.

- [x] **Phase 1:** Infrastructure & Compute 
- [ ] **Phase 2:** Data Acquisition & Pipeline
- [ ] **Phase 3:** Mathematical Modeling
- [ ] **Phase 4:** Risk Management & Meta-Labeling
- [ ] **Phase 5:** Backtesting & Validation (CPCV & Deflated Sharpe Ratio)
- [ ] **Phase 6:** Paper Trading & Live Deployment (Staged from Alpha to Production)
- [ ] **Phase 7:** Team Culture & Operations (No Silos, Shared Destiny)

*(Currently, Phase 1 is in progress with WaveletPro and HMM Pro fully integrated and verified).*

---

## 📚 Documentation
All extensive project documentation has been consolidated and can be explored via the [Graphify Report](./graphify-out/GRAPH_REPORT.md). The `GRAPH_REPORT.md` file contains a detailed topology of the codebase and includes a full system architecture and technical consolidation summary at the end of the file. 

---

## ⚠️ Disclaimer
**For Research Purposes Only.** This software is provided as-is, and the creators are not responsible for any financial losses incurred from using this trading engine. Always backtest strategies thoroughly and use paper trading before committing live capital.

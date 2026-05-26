# Mini-Medallion: Project Summary & Architecture
**Last Updated:** May 26, 2026
**Asset Class:** XAU/USD (Gold)
**Mode:** Live Autonomous Paper Trading

## 1. Project Overview
Mini-Medallion is a production-grade, highly autonomous algorithmic trading engine designed to trade Gold (XAU/USD). It utilizes a multi-model machine learning ensemble architecture inspired by institutional quantitative hedge funds. The system operates 24/7, fetching data, computing features, running 7 distinct models, aggregating predictions via a Meta-Learner, applying strict risk management, and executing trades.

---

## 2. Core Architecture
The system is divided into highly decoupled, microservice-like modules:

### A. Data Ingestion & Feature Engineering
- **Live Data:** Fetches real-time spot prices and macro indicators (DXY, US10Y, Silver) using `yfinance` and `Gold-API.com` / `MetalPriceAPI`.
- **Feature Store:** Implements a high-performance pipeline using Parquet and Redis for caching.
- **Transformations:** Computes over 25 features including ATR, ADX, rolling statistics, wavelet transforms, and custom indicators like `real_yield_proxy`.

### B. The 7-Model Ensemble (The "Brain")
The system does not rely on a single algorithm; it aggregates 6 diverse base models:
1. **HMM (Hidden Markov Model):** Determines the market regime (`GROWTH`, `NORMAL`, `CRISIS`).
2. **Wavelet Transform:** De-noises high-frequency price action to find the true underlying trend.
3. **LSTM:** Temporal deep learning model for sequence prediction.
4. **TFT (Temporal Fusion Transformer):** State-of-the-art transformer for multi-horizon quantile forecasting.
5. **Genetic Algorithm:** Evaluates raw technical indicator rules using evolutionary computing.
6. **NLP / Sentiment:** Fundamental proxy model (currently slated for a massive RAG upgrade).
7. **The Meta-Learner (RandomForest):** The final arbiter. It takes the outputs of models 1-6 + the current HMM Regime + Macro Data, and predicts the final trade direction (`LONG/SHORT/HOLD`) and outputs a `Confidence Score`.

### C. Risk Management (The "Shield")
Before any trade is executed, it must pass through `manager.py`:
- **Confidence Gate:** The Meta-Learner must have a confidence `> 55%`.
- **Kelly Criterion:** Dynamic position sizing based on the current HMM regime (e.g., risking less capital during a `CRISIS`).
- **Circuit Breakers:** Hard-coded limits that instantly halt trading to protect capital:
  - Max Drawdown Limit (10%)
  - Max Daily Loss (2%)
  - Consecutive Loss Cooldown

### D. Live Trading & Execution
- **`live_trader.py`:** The continuous daemon running a 60-second execution loop.
- **Paper Trading Engine:** Simulates real-world execution by artificially penalizing entry/exit prices with realistic Spread & Slippage (e.g., higher spread during volatile news windows).

### E. Frontend Dashboard
- **React UI:** A beautifully designed, real-time dashboard (`http://localhost:5173/live-trading`).
- **Features:** Displays live pulse indicators, equity curves, active circuit breakers, a 7-model signal matrix, and real-time P&L KPIs.

---

## 3. Recent Milestones & Solved Blockers
- **Live Trader Deployed:** Successfully transitioned from historical backtesting/simulations to a real-time ticking `live_trader.py` daemon.
- **Meta-Learner Trained:** `meta_learner.joblib` was successfully compiled and integrated.
- **GPU Architecture Fixed:** Resolved PyTorch CUDA fallback warnings and optimized the `detect_gpu` initialization flow.
- **Unblocking the Engine:** Solved issues where the Risk Manager was incorrectly blocking trades by:
  1. Lowering the `min_confidence` threshold to `0.55`.
  2. Relaxing the regime filter to allow trading during `CRISIS` and `GROWTH` regimes, not just `NORMAL`.
- **First Successful Trades:** The system has officially begun taking risk-managed `LONG/SHORT` trades in the live paper environment!

---

## 4. Immediate Roadmap (Next Steps)
1. **RAG Integration (Fundamental Macro Analysis)**
   - *Plan:* Replace the static NLP model with a local Retrieval-Augmented Generation (RAG) pipeline.
   - *Tech Stack:* Ollama (`llama3.1` 8B for reasoning, `mxbai-embed-large` for embeddings) + LangChain + FAISS/ChromaDB.
   - *Goal:* Ingest daily Fed reports and Reuters news to give the Meta-Learner real-time macroeconomic fundamental context.
2. **Broker Integration**
   - *Plan:* Swap the `PaperTradingEngine` with an `IBKR` (Interactive Brokers) API adapter to route live orders to a real brokerage account.
3. **Continuous Training Daemon**
   - *Plan:* Finalize the background script that re-trains the models (LSTM, TFT, HMM) automatically every weekend using the latest market data to prevent model decay.

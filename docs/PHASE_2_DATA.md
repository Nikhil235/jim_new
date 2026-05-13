# Phase 2: Data Acquisition & Pipeline
> *Simons searched for "invariants" — patterns that persist regardless of the news.*

**Duration**: Weeks 2–5 | **Status**: ✅ **75% Complete** (May 13, 2026 Updated)

**Completed Core Pipeline**: ✅ Gold fetcher, Macro fetcher, QuestDB integration, Feature store, Data quality monitoring, Pipeline orchestration, **Daily Scheduler**

---

## 2.1 Core Price Data

| Data Type | Source | Resolution | Priority |
|-----------|--------|------------|----------|
| XAU/USD Spot | LBMA, Refinitiv | Tick (L1/L2) | 🔴 Critical |
| Gold Futures (GC) | CME via CQG/Rithmic | Tick + L3 Order Book | 🔴 Critical |
| Gold Options | CME Group | Daily chain snapshots | 🟡 High |
| Physical Gold Premiums | Shanghai Gold Exchange | Daily | 🟡 High |

---

## 2.2 Macro-Correlate Feeds

| Data | Source | Why It Matters |
|------|--------|----------------|
| **DXY** (USD Index) | ICE / FRED | Gold's primary inverse correlate |
| **TIPS Spreads** (Real Yields) | US Treasury / FRED | The "true" driver of gold prices |
| **Fed Funds Rate** | Federal Reserve | Opportunity cost of holding gold |
| **Central Bank Purchases** | IMF / World Gold Council | Structural demand shifts |
| **VIX** | CBOE | "Fear gauge" — gold = safe haven |
| **10Y UST Yields** | US Treasury | Nominal yield pressure |
| **CNY/USD** | PBOC / Refinitiv | China = largest gold consumer |

---

## 2.3 Alternative Data

| Data | Source | Signal Type |
|------|--------|-------------|
| News Sentiment ("Safe Haven" keywords) | GDELT / NewsAPI / Custom NLP | Fear/flight-to-safety |
| Google Trends ("buy gold") | Google Trends API | Retail sentiment proxy |
| COT Reports | CFTC | Institutional positioning |
| ETF Flows (GLD, IAU) | Bloomberg / ETF providers | Demand proxy |
| Mining Production Data | Company filings | Supply-side pressure |

---

## 2.4 Data Pipeline Architecture

```
[Raw Sources]
     │
     ▼
[Kafka / Redis Streams]  ← Ingestion Layer
     │
     ▼
[Data Lake (MinIO)]       ← Raw parquet archival
     │
     ▼
[Cleaning & Normalization]
     │
     ▼
[Feature Engineering]     ← 200+ features generated
     │
     ▼
[Feature Store (Redis)]   ← Real-time serving
     │
     ▼
[Model Input Ready]
```

---

## 2.5 Feature Engineering (200+ Features)

### Price-Based Features
- Returns (1m, 5m, 15m, 1h, 4h, 1d)
- Realized volatility (multiple windows)
- Bid-ask spread dynamics
- VWAP deviations
- Order flow imbalance

### Cross-Asset Features
- Gold/DXY rolling correlation
- Gold/VIX rolling correlation
- Gold vs Real Yields spread
- Gold/Silver ratio (GSR)
- Gold/Oil ratio

### Microstructure Features
- Order book imbalance (L1–L5)
- Trade arrival rate
- Kyle's Lambda (price impact)
- Amihud illiquidity measure

### Temporal Features
- Hour of day, day of week (cyclical encoding)
- London Fix timing effects
- FOMC/NFP proximity flags
- Options expiry proximity

---

## 2.6 Deliverables Checklist

### DATA SOURCES (✅ COMPLETE)
- [x] Gold data fetcher (`src/ingestion/gold_fetcher.py`)
  - Historical data fetching (10+ years)
  - Multiple symbol support with parallel fetching
  - Incremental fetch capability (new data only)
  - Parquet storage and loading
  - Data summary reporting
- [x] Macro-correlate fetcher (`src/ingestion/macro_fetcher.py`)
  - Yahoo Finance sources (DXY, VIX, TLT, TIP, Silver, Oil, CNY)
  - FRED API integration (Fed Funds, TIPS, Yield Curve, Trade-Weighted USD)
  - Google Trends data fetching capability
  - Automatic timeseries alignment and ratio computation
  - Parquet persistence with load/save methods
- [x] Alternative data manager (`src/ingestion/alternative_data.py`)
  - CFTC COT report parser (historical + current)
  - News sentiment scoring (NewsAPI integration)
  - ETF flow tracking (GLD, IAU)
  - Synthetic data fallback for development

### DATABASE INTEGRATION (✅ COMPLETE)
- [x] QuestDB schema manager (`src/ingestion/schema_manager.py`)
  - Multi-resolution gold data (1m, 1h, 1d)
  - Macro-correlate daily table
  - FRED economic series table
  - COT weekly table
  - Sentiment daily table
  - Feature tables (daily and hourly)
  - Gold ticks table for L1/L2 order book
  - Automatic deduplication via UPSERT keys
- [x] QuestDB writer (`src/ingestion/questdb_writer.py`)
  - ILP (Influx Line Protocol) batch writes
  - REST SQL API queries
  - Graceful fallback to parquet if QuestDB unavailable
  - Availability checking and health monitoring
  - Batch-size optimization

### FEATURE ENGINEERING & STORAGE (✅ COMPLETE)
- [x] Feature store (`src/features/feature_store.py`)
  - Redis-backed real-time feature serving
  - Parquet fallback for development/offline
  - Batch-optimized storage (chunked writes)
  - Feature drift detection and reporting
  - Latest feature retrieval
  - Historical feature retrieval with lookback
  - TTL and archival policies
- [x] Feature engineering (existing from Phase 1, `src/features/engine.py`)
  - 200+ engineered features
  - Return features (multi-horizon)
  - Volatility features (Parkinson, rolling std)
  - Momentum features (RSI, MACD, SMA/EMA distance)
  - Price level features (ATR, support/resistance)
  - Temporal features (cyclical encoding)
  - Cross-asset correlation features

### DATA QUALITY & MONITORING (✅ COMPLETE)
- [x] Data quality monitor (`src/ingestion/data_quality.py`)
  - Completeness checks (row counts, date ranges)
  - Gap detection (missing bars)
  - Outlier detection (z-score based)
  - OHLC sanity checks (open/high/low/close relationships)
  - Null value checking
  - Staleness monitoring (last update timestamps)
  - Cross-source alignment validation
  - Correlation break detection
  - Prometheus metrics exposure
- [x] Metrics exporter (`src/ingestion/metrics_exporter.py`)
  - Data row count metrics per source
  - Data staleness metrics
  - Data quality alert counts
  - Pipeline duration metrics
  - Pipeline status metrics
  - Feature count and drift metrics
  - Prometheus HTTP server for scraping

### PIPELINE ORCHESTRATION (✅ COMPLETE)
- [x] Pipeline orchestrator (`src/ingestion/pipeline_orchestrator.py`)
  - Multiple execution modes:
    - `full` - All steps (gold + macro + alt + features)
    - `gold-only` - Only gold price data
    - `macro-only` - Only macro + FRED data
    - `features-only` - Regenerate features from existing data
    - `incremental` - Only new data since last run
  - Automatic retries with exponential backoff
  - Step-by-step failure tracking and recovery
  - Comprehensive reporting with timing and row counts
  - Data quality validation after ingestion
  - Feature generation and storage in pipeline

### DEPENDENCIES & UTILITIES (✅ COMPLETE)
- [x] Resilience utilities (`src/utils/resilience.py`)
  - `@retry` decorator with configurable backoff
  - `@timeout` decorator for long operations
  - `CircuitBreaker` class for fault tolerance
  - Applied to all data fetchers for robustness

### TODO - NOT YET COMPLETE
- [ ] Streaming data ingestion (Kafka/Redis Streams) - Current: batch fetching only
- [ ] Production-scale L2/L3 order book data - Current: OHLCV only
- [ ] Live tick-by-tick data feeds - Current: Daily/hourly data
- [ ] Advanced NLP sentiment analysis - Current: Basic keyword scoring
- [ ] Mining production data integration - Current: Not implemented
- [ ] Options chain data integration - Current: Not implemented

---

*Back to [ROADMAP](../ROADMAP.md) | Next: [Phase 3](PHASE_3_MODELING.md)*

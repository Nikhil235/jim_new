# Phase 2: Data Acquisition & Pipeline
> *Simons searched for "invariants" — patterns that persist regardless of the news.*

**Duration**: Weeks 2–5 | **Status**: 🔴 Not Started

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

- [ ] Historical XAU tick data loaded (minimum 10 years)
- [ ] Gold Futures L2/L3 data feed operational
- [ ] All macro-correlate feeds ingesting into QuestDB
- [ ] News sentiment NLP pipeline running
- [ ] COT report auto-parser built
- [ ] Feature engineering pipeline producing 200+ features
- [ ] Data quality monitoring alerts configured
- [ ] Kafka/Redis streaming pipeline tested

---

*Back to [ROADMAP](../ROADMAP.md) | Next: [Phase 3](PHASE_3_MODELING.md)*

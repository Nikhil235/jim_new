"""
Alternative Data Sources
========================
Non-traditional data for gold trading signals:
  - CFTC COT Reports (institutional positioning) — real parser
  - News Sentiment (NewsAPI-powered keyword scoring)
  - ETF Flows (GLD/IAU as demand proxy)

API Keys (from .env):
  - NEWSAPI_KEY for news sentiment
  - COT data is free/public (no key needed)
"""

import io
import zipfile
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pathlib import Path
from loguru import logger

from src.utils.config import get_config, PROJECT_ROOT


# ──────────────────────────────────────────────────────────
# COT Parser — Real CFTC Data
# ──────────────────────────────────────────────────────────

class COTParser:
    """Parse CFTC Commitments of Traders reports for gold futures.

    Downloads the weekly COT report (futures-only, short format)
    from CFTC's public website and extracts gold-specific rows.

    The COT report is a fixed-width text file with columns for
    commercial/non-commercial long/short/spread positions.
    """

    # CFTC URLs for COT data
    CURRENT_YEAR_URL = "https://www.cftc.gov/dea/newcot/deafut.txt"
    HISTORICAL_URL = "https://www.cftc.gov/files/dea/history/deacot{year}.zip"

    # Gold commodity codes in CFTC data
    GOLD_SEARCH_TERMS = ["GOLD", "088691"]

    def __init__(self):
        self.raw_dir = PROJECT_ROOT / "data" / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def fetch_cot_data(self, years: int = 3) -> Optional[pd.DataFrame]:
        """Fetch COT data from CFTC website.

        Tries current year first, then falls back to historical zips,
        then to synthetic data if all else fails.
        """
        all_dfs = []

        # 1. Try current year text file
        try:
            logger.info("  Downloading current year COT report...")
            df = self._download_and_parse_txt(self.CURRENT_YEAR_URL)
            if df is not None and not df.empty:
                all_dfs.append(df)
                logger.info(f"  ✅ Current year COT: {len(df)} reports")
        except Exception as e:
            logger.warning(f"  Current year COT failed: {e}")

        # 2. Try historical zip files
        current_year = datetime.now().year
        for year in range(current_year - 1, current_year - years - 1, -1):
            try:
                url = self.HISTORICAL_URL.format(year=year)
                logger.info(f"  Downloading COT history for {year}...")
                df = self._download_and_parse_zip(url)
                if df is not None and not df.empty:
                    all_dfs.append(df)
                    logger.info(f"  ✅ {year} COT: {len(df)} reports")
            except Exception as e:
                logger.warning(f"  {year} COT failed: {e}")

        # 3. Combine results
        if all_dfs:
            combined = pd.concat(all_dfs, ignore_index=True)
            combined = combined.sort_values("timestamp").drop_duplicates(
                subset=["timestamp"], keep="last"
            )
            combined = combined.set_index("timestamp")
            logger.info(f"COT total: {len(combined)} weekly reports")
            return combined

        # 4. Fallback to synthetic
        logger.warning("No real COT data fetched — using synthetic fallback")
        return self._generate_synthetic_cot()

    def _download_and_parse_txt(self, url: str) -> Optional[pd.DataFrame]:
        """Download and parse a CFTC plain text COT file."""
        import urllib.request
        with urllib.request.urlopen(url, timeout=30) as resp:
            content = resp.read().decode("utf-8", errors="replace")
        return self._parse_cot_content(content)

    def _download_and_parse_zip(self, url: str) -> Optional[pd.DataFrame]:
        """Download and parse a CFTC zip archive COT file."""
        import urllib.request
        with urllib.request.urlopen(url, timeout=60) as resp:
            zip_data = resp.read()
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            # Find the futures-only file inside the zip
            txt_files = [n for n in zf.namelist() if n.endswith(".txt")]
            if not txt_files:
                return None
            content = zf.read(txt_files[0]).decode("utf-8", errors="replace")
        return self._parse_cot_content(content)

    def _parse_cot_content(self, content: str) -> Optional[pd.DataFrame]:
        """Parse COT text content and extract gold rows.

        The CFTC short format is comma-separated with these key columns:
          0: Market_and_Exchange_Names
          2: As_of_Date_In_Form_YYMMDD
          7: NonComm_Positions_Long_All
          8: NonComm_Positions_Short_All
          9: NonComm_Positions_Spreading_All
         10: Comm_Positions_Long_All
         11: Comm_Positions_Short_All
         13: Tot_Rept_Positions_Long_All
         14: Tot_Rept_Positions_Short_All
         15: Open_Interest_All
        """
        lines = content.strip().split("\n")
        if len(lines) < 2:
            return None

        gold_rows = []
        for line in lines[1:]:  # Skip header
            fields = [f.strip() for f in line.split(",")]
            if len(fields) < 16:
                continue

            # Check if this is a gold row
            market_name = fields[0].upper()
            if not any(term in market_name for term in self.GOLD_SEARCH_TERMS):
                continue

            try:
                row = self._extract_cot_fields(fields)
                if row:
                    gold_rows.append(row)
            except (ValueError, IndexError) as e:
                logger.debug(f"  Skipping malformed COT row: {e}")
                continue

        if not gold_rows:
            return None
        return pd.DataFrame(gold_rows)

    def _extract_cot_fields(self, fields: List[str]) -> Optional[dict]:
        """Extract structured data from a COT CSV row."""
        def safe_int(s):
            s = s.strip().replace(",", "")
            return int(s) if s and s != "." else 0

        # Parse date — CFTC uses YYMMDD or YYYY-MM-DD format
        date_str = fields[2].strip()
        try:
            if "-" in date_str:
                timestamp = pd.to_datetime(date_str)
            elif len(date_str) == 6:
                timestamp = pd.to_datetime(date_str, format="%y%m%d")
            else:
                timestamp = pd.to_datetime(date_str)
        except Exception:
            return None

        nc_long = safe_int(fields[7]) if len(fields) > 7 else 0
        nc_short = safe_int(fields[8]) if len(fields) > 8 else 0
        nc_spread = safe_int(fields[9]) if len(fields) > 9 else 0
        c_long = safe_int(fields[10]) if len(fields) > 10 else 0
        c_short = safe_int(fields[11]) if len(fields) > 11 else 0
        total_long = safe_int(fields[13]) if len(fields) > 13 else 0
        total_short = safe_int(fields[14]) if len(fields) > 14 else 0
        oi = safe_int(fields[15]) if len(fields) > 15 else 0

        return {
            "timestamp": timestamp,
            "contract": "GOLD",
            "noncommercial_long": nc_long,
            "noncommercial_short": nc_short,
            "noncommercial_spread": nc_spread,
            "commercial_long": c_long,
            "commercial_short": c_short,
            "total_long": total_long,
            "total_short": total_short,
            "open_interest": oi,
            "net_commercial": c_long - c_short,
            "net_noncommercial": nc_long - nc_short,
        }

    def _generate_synthetic_cot(self) -> pd.DataFrame:
        """Generate synthetic COT data for development/testing."""
        logger.info("  Generating synthetic COT data for development...")
        dates = pd.date_range(end=datetime.now(), periods=156, freq="W-TUE")
        np.random.seed(42)
        nc_long = 200000 + np.cumsum(np.random.randint(-5000, 5000, len(dates)))
        nc_short = 100000 + np.cumsum(np.random.randint(-3000, 3000, len(dates)))
        c_long = 150000 + np.cumsum(np.random.randint(-4000, 4000, len(dates)))
        c_short = 180000 + np.cumsum(np.random.randint(-4000, 4000, len(dates)))
        df = pd.DataFrame({
            "contract": "GOLD",
            "noncommercial_long": np.abs(nc_long).astype(int),
            "noncommercial_short": np.abs(nc_short).astype(int),
            "noncommercial_spread": np.random.randint(20000, 40000, len(dates)),
            "commercial_long": np.abs(c_long).astype(int),
            "commercial_short": np.abs(c_short).astype(int),
            "total_long": (np.abs(nc_long) + np.abs(c_long)).astype(int),
            "total_short": (np.abs(nc_short) + np.abs(c_short)).astype(int),
            "open_interest": np.random.randint(400000, 600000, len(dates)),
        }, index=dates)
        df.index.name = "timestamp"
        df["net_commercial"] = df["commercial_long"] - df["commercial_short"]
        df["net_noncommercial"] = df["noncommercial_long"] - df["noncommercial_short"]
        return df

    def save_to_parquet(self, df: pd.DataFrame) -> Path:
        fp = self.raw_dir / "cot_gold.parquet"
        df.to_parquet(fp, engine="pyarrow")
        logger.debug(f"Saved COT data: {len(df)} rows → {fp.name}")
        return fp


# ──────────────────────────────────────────────────────────
# News Sentiment — Real NewsAPI Integration
# ──────────────────────────────────────────────────────────

class SentimentScorer:
    """News sentiment scoring for gold using NewsAPI.

    Uses the NewsAPI (newsapi.org) to fetch real headlines,
    then scores them with keyword-based sentiment analysis.

    Falls back to synthetic data if API key is missing or API fails.
    """

    BULLISH_KEYWORDS = [
        "safe haven", "gold rally", "gold rises", "gold gains",
        "inflation fears", "rate cut", "fed cuts", "dovish",
        "geopolitical risk", "central bank buying", "dollar weakness",
        "recession fears", "uncertainty", "flight to safety",
        "gold demand", "bullion demand", "gold surges",
    ]

    BEARISH_KEYWORDS = [
        "rate hike", "strong dollar", "gold sell-off", "gold falls",
        "gold drops", "taper", "hawkish", "gold declines",
        "risk-on", "stock rally", "hawkish fed", "fed raises",
        "stronger dollar", "treasury yields rise", "gold slips",
    ]

    # Gold-related search queries for NewsAPI
    SEARCH_QUERIES = ["gold price", "gold market", "gold trading", "XAUUSD", "bullion"]

    def __init__(self, config: Optional[dict] = None):
        self.config = config or get_config()
        alt_cfg = self.config.get("data", {}).get("alternative", {})
        self.api_key = alt_cfg.get("newsapi_key", "")
        self.raw_dir = PROJECT_ROOT / "data" / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def fetch_and_score(self, days_back: int = 7) -> pd.DataFrame:
        """Fetch recent gold news from NewsAPI and score sentiment.

        Args:
            days_back: Number of days of news to fetch.

        Returns:
            DataFrame with daily sentiment scores.
        """
        if not self.api_key or self.api_key in ("", "${NEWSAPI_KEY}", "your_newsapi_key_here"):
            logger.warning("NewsAPI key not configured — using synthetic sentiment")
            return self.generate_synthetic_sentiment()

        try:
            headlines = self._fetch_newsapi_headlines(days_back)
            if not headlines:
                logger.warning("No headlines from NewsAPI — using synthetic")
                return self.generate_synthetic_sentiment()

            # Group headlines by date and score each day
            daily_scores = []
            headlines_by_date = {}
            for hl in headlines:
                date = hl["date"]
                if date not in headlines_by_date:
                    headlines_by_date[date] = []
                headlines_by_date[date].append(hl["title"])

            for date, titles in sorted(headlines_by_date.items()):
                scores = self.score_headlines(titles)
                scores["date"] = date
                scores["source"] = "newsapi"
                daily_scores.append(scores)

            if daily_scores:
                df = pd.DataFrame(daily_scores)
                df.index = pd.to_datetime(df["date"])
                df.index.name = "timestamp"
                df = df.drop(columns=["date"])
                logger.info(f"NewsAPI sentiment: {len(df)} days scored, {sum(s['article_count'] for s in daily_scores)} articles")
                return df

        except Exception as e:
            logger.error(f"NewsAPI fetch failed: {e}")

        return self.generate_synthetic_sentiment()

    def _fetch_newsapi_headlines(self, days_back: int) -> List[dict]:
        """Fetch gold-related headlines from NewsAPI."""
        import urllib.request
        import urllib.parse
        import json

        headlines = []
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        to_date = datetime.now().strftime("%Y-%m-%d")

        for query in self.SEARCH_QUERIES[:2]:  # Limit queries to avoid rate limits
            try:
                params = urllib.parse.urlencode({
                    "q": query,
                    "from": from_date,
                    "to": to_date,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 100,
                    "apiKey": self.api_key,
                })
                url = f"https://newsapi.org/v2/everything?{params}"

                req = urllib.request.Request(url, headers={"User-Agent": "MiniMedallion/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode())

                if data.get("status") == "ok":
                    for article in data.get("articles", []):
                        title = article.get("title", "")
                        pub_date = article.get("publishedAt", "")[:10]
                        if title and pub_date:
                            headlines.append({"title": title, "date": pub_date})

            except Exception as e:
                logger.debug(f"  NewsAPI query '{query}' failed: {e}")

        logger.info(f"  NewsAPI fetched {len(headlines)} headlines across {len(set(h['date'] for h in headlines))} days")
        return headlines

    def score_headlines(self, headlines: List[str]) -> Dict[str, float]:
        """Score a list of headlines for gold sentiment."""
        positive = 0
        negative = 0
        neutral = 0

        for headline in headlines:
            hl = headline.lower()
            bull_hits = sum(1 for kw in self.BULLISH_KEYWORDS if kw in hl)
            bear_hits = sum(1 for kw in self.BEARISH_KEYWORDS if kw in hl)
            if bull_hits > bear_hits:
                positive += 1
            elif bear_hits > bull_hits:
                negative += 1
            else:
                neutral += 1

        total = len(headlines) or 1
        keyword_score = (positive - negative) / total
        safe_haven_mentions = sum(
            1 for h in headlines
            if any(kw in h.lower() for kw in ["safe haven", "flight to safety", "uncertainty"])
        )

        return {
            "keyword_score": keyword_score,
            "article_count": len(headlines),
            "positive_count": positive,
            "negative_count": negative,
            "neutral_count": neutral,
            "safe_haven_mentions": safe_haven_mentions,
            "fear_index": safe_haven_mentions / total,
        }

    def generate_synthetic_sentiment(self, days: int = 365) -> pd.DataFrame:
        """Generate synthetic daily sentiment for development."""
        logger.info("  Generating synthetic sentiment data...")
        dates = pd.date_range(end=datetime.now(), periods=days, freq="B")
        np.random.seed(123)
        scores = np.random.normal(0.05, 0.3, len(dates)).clip(-1, 1)
        articles = np.random.randint(5, 50, len(dates))
        positives = (articles * (0.5 + scores * 0.3)).astype(int).clip(0)
        negatives = (articles * (0.5 - scores * 0.3)).astype(int).clip(0)
        df = pd.DataFrame({
            "source": "synthetic",
            "keyword_score": scores,
            "article_count": articles,
            "positive_count": positives,
            "negative_count": negatives,
            "neutral_count": articles - positives - negatives,
            "safe_haven_mentions": np.random.randint(0, 10, len(dates)),
            "fear_index": np.abs(np.random.normal(0.15, 0.1, len(dates))).clip(0, 1),
        }, index=dates)
        df.index.name = "timestamp"
        return df

    def save_to_parquet(self, df: pd.DataFrame) -> Path:
        fp = self.raw_dir / "sentiment_daily.parquet"
        df.to_parquet(fp, engine="pyarrow")
        return fp


# ──────────────────────────────────────────────────────────
# ETF Flow Tracker
# ──────────────────────────────────────────────────────────

class ETFFlowTracker:
    """Track gold ETF volume as a demand proxy."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or get_config()
        alt_cfg = self.config.get("data", {}).get("alternative", {})
        self.etf_symbols = alt_cfg.get("etf_symbols", ["GLD", "IAU"])
        self.raw_dir = PROJECT_ROOT / "data" / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def fetch_etf_flows(self, period: str = "5y") -> Dict[str, pd.DataFrame]:
        """Fetch ETF price and volume data, compute flow proxy."""
        import yfinance as yf
        etf_data = {}
        logger.info(f"Fetching ETF flow data: {self.etf_symbols}")
        for symbol in self.etf_symbols:
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=period, interval="1d")
                if df.empty:
                    continue
                df.columns = [c.lower().replace(" ", "_") for c in df.columns]
                df.index.name = "timestamp"
                df["volume_ma20"] = df["volume"].rolling(20).mean()
                df["volume_ratio"] = df["volume"] / df["volume_ma20"].replace(0, np.nan)
                price_dir = np.sign(df["close"].pct_change())
                df["flow_proxy"] = df["volume_ratio"] * price_dir
                for drop_col in ["dividends", "stock_splits", "capital_gains"]:
                    if drop_col in df.columns:
                        df = df.drop(columns=[drop_col])
                etf_data[symbol] = df
                logger.info(f"  ✅ {symbol}: {len(df)} bars")
            except Exception as e:
                logger.error(f"  ❌ {symbol}: {e}")
        return etf_data

    def save_to_parquet(self, etf_data: Dict[str, pd.DataFrame]) -> Dict[str, Path]:
        paths = {}
        for symbol, df in etf_data.items():
            fp = self.raw_dir / f"etf_{symbol.lower()}.parquet"
            df.to_parquet(fp, engine="pyarrow")
            paths[symbol] = fp
        return paths


# ──────────────────────────────────────────────────────────
# Unified Manager
# ──────────────────────────────────────────────────────────

class AlternativeDataManager:
    """Unified manager for all alternative data sources."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or get_config()
        self.cot = COTParser()
        self.sentiment = SentimentScorer(config)
        self.etf = ETFFlowTracker(config)

    def fetch_all(self) -> Dict[str, pd.DataFrame]:
        """Fetch all alternative data sources."""
        results = {}

        # COT data (real CFTC parsing)
        logger.info("Fetching COT data...")
        cot_df = self.cot.fetch_cot_data()
        if cot_df is not None:
            results["cot"] = cot_df
            self.cot.save_to_parquet(cot_df)

        # Sentiment (real NewsAPI if key available)
        logger.info("Fetching sentiment data...")
        sentiment_df = self.sentiment.fetch_and_score(days_back=30)
        results["sentiment"] = sentiment_df
        self.sentiment.save_to_parquet(sentiment_df)

        # ETF flows
        logger.info("Fetching ETF flow data...")
        etf_data = self.etf.fetch_etf_flows()
        for symbol, df in etf_data.items():
            results[f"etf_{symbol}"] = df
        self.etf.save_to_parquet(etf_data)

        logger.info(f"Alternative data: {len(results)} sources fetched")
        return results

"""
OANDA Institutional Data Fetcher
================================
Replaces Yahoo Finance with OANDA's institutional-grade API for Phase 7 Live Trading.
Fetches high-resolution tick/1-minute data and Level 2 Order Book imbalances
for Gold (XAU_USD).
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

from src.utils.config import get_config

class OandaFetcher:
    """
    Fetches real-time institutional data and order book imbalances from OANDA.
    """
    
    def __init__(self, api_key: Optional[str] = None, account_id: Optional[str] = None, environment: str = "practice"):
        self.config = get_config()
        
        # Load credentials from config or environment
        self.api_key = api_key or self.config.get("credentials", {}).get("oanda_api_key", "")
        self.account_id = account_id or self.config.get("credentials", {}).get("oanda_account_id", "")
        
        if not self.api_key:
            logger.warning("OANDA API Key not found. Please add 'oanda_api_key' to your config or environment variables.")
            
        # Select API endpoint based on environment
        if environment == "practice":
            self.base_url = "https://api-fxpractice.oanda.com/v3"
        else:
            self.base_url = "https://api-fxtrade.oanda.com/v3"
            
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept-Datetime-Format": "RFC3339"
        }
        
    def fetch_recent_bars(self, symbol: str = "XAU_USD", count: int = 500, granularity: str = "M1") -> pd.DataFrame:
        """
        Fetch high-resolution recent candlestick data.
        Granularity options: M1 (1 min), M5 (5 min), H1 (1 hour)
        """
        if not self.api_key:
            logger.error("Cannot fetch data: OANDA API key is missing.")
            return pd.DataFrame()
            
        endpoint = f"{self.base_url}/instruments/{symbol}/candles"
        params = {
            "count": count,
            "granularity": granularity,
            "price": "M"  # Midpoint pricing
        }
        
        logger.info(f"Fetching {count} {granularity} bars for {symbol} from OANDA...")
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            bars = []
            for candle in data.get("candles", []):
                if candle.get("complete", False):
                    bars.append({
                        "timestamp": pd.to_datetime(candle["time"]),
                        "open": float(candle["mid"]["o"]),
                        "high": float(candle["mid"]["h"]),
                        "low": float(candle["mid"]["l"]),
                        "close": float(candle["mid"]["c"]),
                        "volume": int(candle["volume"])
                    })
                    
            df = pd.DataFrame(bars)
            if not df.empty:
                df.set_index("timestamp", inplace=True)
                df["returns"] = df["close"].pct_change()
                logger.info(f"Successfully fetched {len(df)} {granularity} bars.")
                
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch OANDA candlestick data: {e}")
            return pd.DataFrame()

    def fetch_order_book_imbalance(self, symbol: str = "XAU_USD") -> Dict[str, float]:
        """
        Fetch the current Level 2 Order Book profile.
        Calculates the imbalance between long and short institutional positioning.
        This provides massive predictive alpha for the TFT and LSTM models.
        """
        if not self.api_key:
            return {"imbalance_score": 0.0}
            
        endpoint = f"{self.base_url}/instruments/{symbol}/orderBook"
        
        logger.info(f"Fetching Order Book for {symbol}...")
        
        try:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            book = data.get("orderBook", {})
            current_price = float(book.get("price", 0))
            
            long_volume = 0.0
            short_volume = 0.0
            
            # Parse the order book buckets
            for bucket in book.get("buckets", []):
                price = float(bucket["price"])
                long_qty = float(bucket["longCountPercent"])
                short_qty = float(bucket["shortCountPercent"])
                
                # Weigh volume near the current price heavier
                weight = 1.0 / (abs(price - current_price) + 1e-5)
                
                long_volume += long_qty * weight
                short_volume += short_qty * weight
                
            total_volume = long_volume + short_volume
            imbalance = (long_volume - short_volume) / total_volume if total_volume > 0 else 0.0
            
            logger.info(f"Order Book Imbalance: {imbalance:+.2f} (Positive = Bullish Flow)")
            
            return {
                "current_price": current_price,
                "long_pressure": long_volume,
                "short_pressure": short_volume,
                "imbalance_score": imbalance
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch OANDA Order Book: {e}")
            return {"imbalance_score": 0.0}

if __name__ == "__main__":
    # Test execution
    fetcher = OandaFetcher()
    df = fetcher.fetch_recent_bars(count=10)
    print(df.tail())
    
    ob = fetcher.fetch_order_book_imbalance()
    print(ob)

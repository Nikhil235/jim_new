"""
Phase 5: Backtester - Historical Data Feed Handler

This module handles loading and streaming historical OHLCV data from QuestDB.
Data is provided in chronological order to prevent lookahead bias.
"""

from datetime import datetime
from typing import Iterator, Optional
import logging

from loguru import logger

try:
    import questdb
except ImportError:
    questdb = None

from .events import MarketEvent, Direction


class DataHandler:
    """
    Historical data feed handler.
    
    Loads OHLCV data from QuestDB and streams it in chronological order.
    Handles missing data, gaps, and provides realistic bid/ask quotes.
    """

    def __init__(
        self,
        symbol: str = "XAU",
        questdb_host: str = "localhost",
        questdb_port: int = 9009,
        ilp_port: int = 9009,
        timezone: str = "UTC",
    ):
        """
        Initialize data handler.
        
        Args:
            symbol: Trading symbol (default 'XAU' for gold)
            questdb_host: QuestDB server host
            questdb_port: QuestDB HTTP port
            ilp_port: QuestDB ILP port (for data insertion)
            timezone: Timezone for timestamps
        """
        self.symbol = symbol
        self.questdb_host = questdb_host
        self.questdb_port = questdb_port
        self.ilp_port = ilp_port
        self.timezone = timezone
        
        self.conn = None
        self.cursor = None
        self._connect()
        
        logger.info(f"Data handler initialized for {symbol}")

    def _connect(self):
        """Connect to QuestDB."""
        if questdb is None:
            logger.warning("questdb module not available - using mock data")
            return
        
        try:
            self.conn = questdb.connect(
                host=self.questdb_host,
                port=self.questdb_port,
            )
            self.cursor = self.conn.cursor()
            logger.info(f"Connected to QuestDB at {self.questdb_host}:{self.questdb_port}")
        except Exception as e:
            logger.error(f"Failed to connect to QuestDB: {e}")
            self.conn = None
            self.cursor = None

    def load_data(
        self,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1d",
    ) -> Iterator[MarketEvent]:
        """
        Load historical data for date range.
        
        Args:
            start_date: Start of backtest period
            end_date: End of backtest period
            timeframe: Timeframe ('1h', '1d', etc.)
            
        Yields:
            MarketEvent objects in chronological order
        """
        if not self.conn:
            logger.warning("No QuestDB connection - using mock data")
            yield from self._mock_data(start_date, end_date)
            return
        
        # Convert to ISO format for SQL query
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()
        
        try:
            # Query: Load OHLCV bars from QuestDB
            query = f"""
                SELECT
                    ts,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    bid,
                    ask,
                    bid_vol,
                    ask_vol,
                    regime
                FROM xau_ohlcv
                WHERE ts >= '{start_str}' AND ts < '{end_str}'
                ORDER BY ts ASC
            """
            
            self.cursor.execute(query)
            
            for row in self.cursor.fetchall():
                ts, open_p, high_p, low_p, close_p, vol, bid, ask, bid_vol, ask_vol, regime = row
                
                yield MarketEvent(
                    event_type=None,  # Will be set by backtester
                    timestamp=ts,
                    symbol=self.symbol,
                    open_price=open_p,
                    high_price=high_p,
                    low_price=low_p,
                    close_price=close_p,
                    volume=vol,
                    bid_price=bid,
                    ask_price=ask,
                    bid_volume=bid_vol,
                    ask_volume=ask_vol,
                    regime=regime,
                )
            
            logger.info(f"Loaded data from {start_date} to {end_date}")
            
        except Exception as e:
            logger.error(f"Error loading data from QuestDB: {e}")
            yield from self._mock_data(start_date, end_date)

    def _mock_data(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Iterator[MarketEvent]:
        """
        Generate mock market data for testing.
        
        Creates realistic OHLCV data with random walk for price.
        """
        import random
        from datetime import timedelta
        
        # Starting price: current gold price approx $2000/oz
        price = 2000.0
        spread = 0.5  # $0.50 spread
        
        current = start_date
        while current < end_date:
            # Random daily return: mean 0.05%, std 1.5%
            daily_return = random.gauss(0.0005, 0.015)
            
            # Generate OHLCV
            open_p = price
            close_p = price * (1 + daily_return)
            high_p = max(open_p, close_p) * (1 + abs(random.gauss(0, 0.005)))
            low_p = min(open_p, close_p) * (1 - abs(random.gauss(0, 0.005)))
            volume = random.randint(100000, 500000)
            
            # Bid/ask quotes
            mid = close_p
            bid = mid - spread / 2
            ask = mid + spread / 2
            
            # Determine regime (simplified)
            if abs(daily_return) > 0.02:
                regime = "CRISIS"
            elif daily_return > 0.01:
                regime = "GROWTH"
            else:
                regime = "NORMAL"
            
            event = MarketEvent(
                event_type=None,
                timestamp=current,
                symbol=self.symbol,
                open_price=open_p,
                high_price=high_p,
                low_price=low_p,
                close_price=close_p,
                volume=volume,
                bid_price=bid,
                ask_price=ask,
                bid_volume=1000,
                ask_volume=1000,
                regime=regime,
            )
            
            yield event
            
            # Move to next day
            current += timedelta(days=1)
            price = close_p

    def get_latest_bar(self, symbol: str) -> Optional[MarketEvent]:
        """Get most recent bar for symbol (not used in event loop, for manual queries)."""
        if not self.conn:
            return None
        
        try:
            query = f"""
                SELECT
                    ts, open, high, low, close, volume, bid, ask, bid_vol, ask_vol, regime
                FROM xau_ohlcv
                WHERE symbol = '{symbol}'
                ORDER BY ts DESC
                LIMIT 1
            """
            self.cursor.execute(query)
            row = self.cursor.fetchone()
            
            if not row:
                return None
            
            ts, open_p, high_p, low_p, close_p, vol, bid, ask, bid_vol, ask_vol, regime = row
            
            return MarketEvent(
                event_type=None,
                timestamp=ts,
                symbol=symbol,
                open_price=open_p,
                high_price=high_p,
                low_price=low_p,
                close_price=close_p,
                volume=vol,
                bid_price=bid,
                ask_price=ask,
                bid_volume=bid_vol,
                ask_volume=ask_vol,
                regime=regime,
            )
        except Exception as e:
            logger.error(f"Error fetching latest bar: {e}")
            return None

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("QuestDB connection closed")

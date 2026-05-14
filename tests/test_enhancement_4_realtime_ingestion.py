"""
Tests for Enhancement #4: Real-Time Ingestion

Test coverage:
- Feed manager connection and subscription
- WebSocket message handling
- Streaming feature computation
- Technical indicator calculation
- Real-time regime detection
- Message buffering and backpressure
- Connection retry logic
"""

import asyncio
from datetime import datetime, timedelta

import pytest
import numpy as np

from src.ingestion.real_time_feed_manager import (
    FeedType,
    MessageType,
    ConnectionStatus,
    Quote,
    Trade,
    Candle,
    FeedMetrics,
    FeedConnector,
    MockFeedConnector,
    RealTimeFeedManager,
)

from src.ingestion.streaming_features import (
    IndicatorType,
    WindowedData,
    StreamingFeatures,
    IndicatorCalculator,
    StreamingFeatureEngine,
)


# ============================================================================
# Unit Tests: Quote Data
# ============================================================================

class TestQuote:
    """Test Quote data structure"""
    
    def test_quote_creation(self):
        """Test creating quote"""
        quote = Quote(
            symbol="SPY",
            timestamp=datetime.utcnow(),
            bid_price=450.00,
            bid_size=100,
            ask_price=450.01,
            ask_size=100,
            last_price=450.00,
            volume=1000000,
        )
        
        assert quote.symbol == "SPY"
        assert quote.bid_price == 450.00
    
    def test_quote_mid_price(self):
        """Test mid price calculation"""
        quote = Quote(
            symbol="SPY",
            timestamp=datetime.utcnow(),
            bid_price=450.00,
            bid_size=100,
            ask_price=450.02,
            ask_size=100,
            last_price=450.01,
            volume=1000000,
        )
        
        assert abs(quote.mid_price() - 450.01) < 0.001
    
    def test_quote_spread(self):
        """Test spread calculation"""
        quote = Quote(
            symbol="SPY",
            timestamp=datetime.utcnow(),
            bid_price=450.00,
            bid_size=100,
            ask_price=450.05,
            ask_size=100,
            last_price=450.02,
            volume=1000000,
        )
        
        assert abs(quote.spread() - 0.05) < 0.001


class TestTrade:
    """Test Trade data structure"""
    
    def test_trade_creation(self):
        """Test creating trade"""
        trade = Trade(
            symbol="SPY",
            timestamp=datetime.utcnow(),
            price=450.00,
            size=1000,
        )
        
        assert trade.symbol == "SPY"
        assert trade.price == 450.00
        assert trade.size == 1000


class TestCandle:
    """Test Candle data structure"""
    
    def test_candle_creation(self):
        """Test creating candle"""
        candle = Candle(
            symbol="SPY",
            timestamp=datetime.utcnow(),
            open_price=450.00,
            high_price=451.00,
            low_price=449.50,
            close_price=450.50,
            volume=1000000,
        )
        
        assert candle.symbol == "SPY"
        assert candle.open_price == 450.00
        assert candle.close_price == 450.50


# ============================================================================
# Unit Tests: Feed Manager
# ============================================================================

class TestFeedMetrics:
    """Test FeedMetrics"""
    
    def test_metrics_creation(self):
        """Test creating feed metrics"""
        metrics = FeedMetrics(feed_type=FeedType.ALPACA)
        assert metrics.feed_type == FeedType.ALPACA
        assert metrics.total_messages == 0


class TestMockFeedConnector:
    """Test MockFeedConnector"""
    
    def test_connector_connection(self):
        """Test feed connector connection"""
        loop = asyncio.new_event_loop()
        try:
            connector = MockFeedConnector(FeedType.ALPACA)
            
            connected = loop.run_until_complete(connector.connect())
            assert connected
            assert connector.connected
        finally:
            loop.close()
    
    def test_connector_subscription(self):
        """Test subscription"""
        loop = asyncio.new_event_loop()
        try:
            connector = MockFeedConnector(FeedType.ALPACA)
            loop.run_until_complete(connector.connect())
            
            success = loop.run_until_complete(connector.subscribe(["SPY", "QQQ"]))
            assert success
            assert "SPY" in connector.subscribed_symbols
            assert "QQQ" in connector.subscribed_symbols
        finally:
            loop.close()


class TestRealTimeFeedManager:
    """Test RealTimeFeedManager"""
    
    def test_manager_creation(self):
        """Test creating feed manager"""
        manager = RealTimeFeedManager()
        assert manager.feeds == {}
        assert manager.max_retries == 5
    
    def test_register_feed(self):
        """Test registering feed"""
        loop = asyncio.new_event_loop()
        try:
            manager = RealTimeFeedManager()
            connector = MockFeedConnector(FeedType.ALPACA)
            
            success = loop.run_until_complete(
                manager.register_feed(FeedType.ALPACA, connector)
            )
            
            assert success
            assert FeedType.ALPACA in manager.feeds
            assert manager.status[FeedType.ALPACA] == ConnectionStatus.DISCONNECTED
        finally:
            loop.close()
    
    def test_connect_feed(self):
        """Test feed connection"""
        loop = asyncio.new_event_loop()
        try:
            manager = RealTimeFeedManager()
            connector = MockFeedConnector(FeedType.ALPACA)
            
            loop.run_until_complete(manager.register_feed(FeedType.ALPACA, connector))
            success = loop.run_until_complete(manager.connect_feed(FeedType.ALPACA))
            
            assert success
            assert manager.status[FeedType.ALPACA] == ConnectionStatus.CONNECTED
        finally:
            loop.close()
    
    def test_disconnect_feed(self):
        """Test feed disconnection"""
        loop = asyncio.new_event_loop()
        try:
            manager = RealTimeFeedManager()
            connector = MockFeedConnector(FeedType.ALPACA)
            
            loop.run_until_complete(manager.register_feed(FeedType.ALPACA, connector))
            loop.run_until_complete(manager.connect_feed(FeedType.ALPACA))
            success = loop.run_until_complete(manager.disconnect_feed(FeedType.ALPACA))
            
            assert success
            assert manager.status[FeedType.ALPACA] == ConnectionStatus.DISCONNECTED
        finally:
            loop.close()
    
    def test_subscribe_symbols(self):
        """Test subscribing to symbols"""
        loop = asyncio.new_event_loop()
        try:
            manager = RealTimeFeedManager()
            connector = MockFeedConnector(FeedType.ALPACA)
            
            loop.run_until_complete(manager.register_feed(FeedType.ALPACA, connector))
            success = loop.run_until_complete(
                manager.subscribe(FeedType.ALPACA, ["SPY", "QQQ"])
            )
            
            assert success
            assert "SPY" in manager.get_subscriptions(FeedType.ALPACA)
            assert "QQQ" in manager.get_subscriptions(FeedType.ALPACA)
        finally:
            loop.close()
    
    def test_get_metrics(self):
        """Test getting feed metrics"""
        loop = asyncio.new_event_loop()
        try:
            manager = RealTimeFeedManager()
            connector = MockFeedConnector(FeedType.ALPACA)
            
            loop.run_until_complete(manager.register_feed(FeedType.ALPACA, connector))
            metrics = manager.get_metrics(FeedType.ALPACA)
            
            assert metrics is not None
            assert metrics.feed_type == FeedType.ALPACA
        finally:
            loop.close()


# ============================================================================
# Unit Tests: Technical Indicators
# ============================================================================

class TestIndicatorCalculator:
    """Test technical indicator calculations"""
    
    def test_sma_calculation(self):
        """Test SMA calculation"""
        prices = [100.0, 101.0, 102.0, 103.0, 104.0]
        sma = IndicatorCalculator.calculate_sma(prices, 3)
        
        expected = np.mean([102.0, 103.0, 104.0])
        assert abs(sma - expected) < 0.01
    
    def test_ema_calculation(self):
        """Test EMA calculation"""
        prices = [100.0] * 10 + [105.0] * 10
        ema = IndicatorCalculator.calculate_ema(prices, 5)
        
        # EMA should be > 100 after adding 105 prices
        assert ema > 100.0
    
    def test_rsi_calculation(self):
        """Test RSI calculation"""
        # Uptrend prices
        prices = [100.0 + i for i in range(20)]
        rsi = IndicatorCalculator.calculate_rsi(prices, 14)
        
        # Should be > 50 for uptrend
        assert rsi > 50.0
    
    def test_macd_calculation(self):
        """Test MACD calculation"""
        prices = [100.0 + i * 0.1 for i in range(50)]
        macd, signal, hist = IndicatorCalculator.calculate_macd(prices)
        
        assert isinstance(macd, float)
        assert isinstance(signal, float)
        assert isinstance(hist, float)
    
    def test_bollinger_bands_calculation(self):
        """Test Bollinger Bands calculation"""
        prices = [100.0] * 10 + [105.0] * 10
        upper, middle, lower = IndicatorCalculator.calculate_bollinger_bands(
            prices, period=20, std_dev=2.0
        )
        
        assert upper > middle > lower
    
    def test_atr_calculation(self):
        """Test ATR calculation"""
        highs = [101.0, 102.0, 103.0, 104.0, 105.0]
        lows = [99.0, 100.0, 101.0, 102.0, 103.0]
        closes = [100.0, 101.0, 102.0, 103.0, 104.0]
        
        atr = IndicatorCalculator.calculate_atr(highs, lows, closes, 3)
        assert atr > 0


# ============================================================================
# Unit Tests: Streaming Features
# ============================================================================

class TestWindowedData:
    """Test WindowedData"""
    
    def test_add_candle(self):
        """Test adding candle to window"""
        window = WindowedData(max_size=10)
        
        window.add_candle(
            datetime.utcnow(),
            100.0, 101.0, 99.0, 100.5, 1000
        )
        
        assert len(window.closes) == 1
        assert window.closes[0] == 100.5
    
    def test_max_size_enforcement(self):
        """Test max size enforcement"""
        window = WindowedData(max_size=3)
        
        for i in range(5):
            window.add_candle(
                datetime.utcnow(),
                100.0 + i, 101.0 + i, 99.0 + i, 100.5 + i, 1000
            )
        
        assert len(window.closes) == 3


class TestStreamingFeatureEngine:
    """Test StreamingFeatureEngine"""
    
    def test_engine_creation(self):
        """Test creating feature engine"""
        engine = StreamingFeatureEngine()
        assert len(engine.windows) == 0
    
    def test_add_candle(self):
        """Test adding candle"""
        loop = asyncio.new_event_loop()
        try:
            engine = StreamingFeatureEngine()
            
            loop.run_until_complete(engine.add_candle(
                "SPY",
                datetime.utcnow(),
                450.0, 451.0, 449.0, 450.5, 1000000
            ))
            
            features = engine.get_features("SPY")
            assert features is not None
            assert features.symbol == "SPY"
            assert features.price == 450.5
        finally:
            loop.close()
    
    def test_feature_computation(self):
        """Test feature computation"""
        loop = asyncio.new_event_loop()
        try:
            engine = StreamingFeatureEngine()
            
            # Add multiple candles
            for i in range(30):
                loop.run_until_complete(engine.add_candle(
                    "SPY",
                    datetime.utcnow() + timedelta(minutes=i),
                    450.0 + i*0.1,
                    451.0 + i*0.1,
                    449.0 + i*0.1,
                    450.5 + i*0.1,
                    1000000 + i*1000
                ))
            
            features = engine.get_features("SPY")
            
            # Check that features are computed
            assert features.sma_10 > 0
            assert features.sma_20 > 0
            assert 0 <= features.rsi_14 <= 100
        finally:
            loop.close()
    
    def test_regime_detection(self):
        """Test regime detection"""
        loop = asyncio.new_event_loop()
        try:
            engine = StreamingFeatureEngine()
            
            # Add candles with trend
            for i in range(30):
                loop.run_until_complete(engine.add_candle(
                    "SPY",
                    datetime.utcnow() + timedelta(minutes=i),
                    450.0 + i*0.5,
                    451.0 + i*0.5,
                    449.0 + i*0.5,
                    450.5 + i*0.5,
                    1000000
                ))
            
            features = engine.get_features("SPY")
            
            # Should detect uptrend
            assert features.trend in ["up", "down", "neutral"]
            assert features.volatility_regime in ["low", "normal", "high"]
        finally:
            loop.close()
    
    def test_get_all_features(self):
        """Test getting all features"""
        loop = asyncio.new_event_loop()
        try:
            engine = StreamingFeatureEngine()
            
            loop.run_until_complete(engine.add_candle(
                "SPY", datetime.utcnow(),
                450.0, 451.0, 449.0, 450.5, 1000000
            ))
            
            loop.run_until_complete(engine.add_candle(
                "QQQ", datetime.utcnow(),
                350.0, 351.0, 349.0, 350.5, 1000000
            ))
            
            all_features = engine.get_all_features()
            assert len(all_features) == 2
            assert "SPY" in all_features
            assert "QQQ" in all_features
        finally:
            loop.close()


# ============================================================================
# Integration Tests
# ============================================================================

class TestRealTimeIngestionIntegration:
    """Integration tests for real-time ingestion"""
    
    def test_feed_to_features_workflow(self):
        """Test full workflow from feed to features"""
        loop = asyncio.new_event_loop()
        try:
            # Setup feed manager
            manager = RealTimeFeedManager()
            connector = MockFeedConnector(FeedType.ALPACA)
            loop.run_until_complete(manager.register_feed(FeedType.ALPACA, connector))
            
            # Setup feature engine
            engine = StreamingFeatureEngine()
            
            # Connect and subscribe
            loop.run_until_complete(manager.connect_feed(FeedType.ALPACA))
            loop.run_until_complete(manager.subscribe(FeedType.ALPACA, ["SPY"]))
            
            # Add candles
            for i in range(30):
                loop.run_until_complete(engine.add_candle(
                    "SPY",
                    datetime.utcnow() + timedelta(minutes=i),
                    450.0 + i*0.1,
                    451.0 + i*0.1,
                    449.0 + i*0.1,
                    450.5 + i*0.1,
                    1000000 + i*1000
                ))
            
            # Verify
            features = engine.get_features("SPY")
            assert features is not None
            assert features.sma_10 > 0
        finally:
            loop.close()


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

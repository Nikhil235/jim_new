"""
Phase 5 Week 3: Model Backtest Runner

Orchestrates comprehensive backtesting of all Phase 3 models
with statistical validation and report generation.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
import pytz

from src.backtesting import (
    StrategyRunner, MarketEvent, EventType,
    create_strategy,
)


class TestPhase3ModelBacktests:
    """Run backtests for all Phase 3 models."""
    
    @staticmethod
    def generate_realistic_market_data(
        start_date: datetime,
        num_bars: int = 252,
        initial_price: float = 2000.0,
        drift: float = 0.0003,
        volatility: float = 0.012,
    ):
        """Generate realistic gold price data."""
        np.random.seed(42)
        data = []
        current_price = initial_price
        
        for i in range(num_bars):
            timestamp = start_date + timedelta(days=i)
            
            # Random walk with drift
            returns = np.random.normal(drift, volatility)
            current_price = current_price * (1 + returns)
            
            # Create OHLCV
            open_price = current_price * (1 + np.random.normal(0, 0.002))
            high_price = max(open_price, current_price) + abs(np.random.normal(0, 0.005))
            low_price = min(open_price, current_price) - abs(np.random.normal(0, 0.005))
            close_price = current_price
            volume = int(np.random.uniform(1e6, 5e6))
            
            # Determine regime based on volatility
            if volatility > 0.02:
                regime = "CRISIS"
            elif volatility > 0.01:
                regime = "NORMAL"
            else:
                regime = "GROWTH"
            
            market_event = MarketEvent(
                event_type=EventType.MARKET,
                timestamp=timestamp,
                symbol="XAU",
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                bid_price=close_price - 0.1,
                ask_price=close_price + 0.1,
                regime=regime,
            )
            
            data.append(market_event)
        
        return data
    
    def test_wavelet_backtest(self):
        """Test Wavelet Denoiser strategy."""
        runner = StrategyRunner(
            initial_capital=100000.0,
            num_strategies_tested=6,
        )
        
        market_data = self.generate_realistic_market_data(
            start_date=datetime(2023, 1, 1, tzinfo=pytz.UTC),
            num_bars=252,
        )
        
        strategy = create_strategy("wavelet")
        
        result = runner.run_backtest(
            strategy_name="Wavelet Denoiser",
            strategy_fn=strategy,
            market_data=market_data,
            model_name="wavelet",
            version="1.0",
        )
        
        assert result.metrics.total_trades >= 0
        assert result.dsr_result is not None
        assert 0 <= result.dsr_result.p_value <= 1
        print(f"\nWavelet: Sharpe={result.metrics.sharpe_ratio:.2f}, DSR p-value={result.dsr_result.p_value:.4f}")
    
    def test_hmm_backtest(self):
        """Test HMM Regime Detection strategy."""
        runner = StrategyRunner(
            initial_capital=100000.0,
            num_strategies_tested=6,
        )
        
        market_data = self.generate_realistic_market_data(
            start_date=datetime(2023, 1, 1, tzinfo=pytz.UTC),
            num_bars=252,
        )
        
        strategy = create_strategy("hmm")
        
        result = runner.run_backtest(
            strategy_name="HMM Regime Detector",
            strategy_fn=strategy,
            market_data=market_data,
            model_name="hmm",
            version="1.0",
        )
        
        assert result.metrics.total_trades >= 0
        assert result.dsr_result is not None
        print(f"\nHMM: Sharpe={result.metrics.sharpe_ratio:.2f}, DSR p-value={result.dsr_result.p_value:.4f}")
    
    def test_lstm_backtest(self):
        """Test LSTM Temporal model strategy."""
        runner = StrategyRunner(
            initial_capital=100000.0,
            num_strategies_tested=6,
        )
        
        market_data = self.generate_realistic_market_data(
            start_date=datetime(2023, 1, 1, tzinfo=pytz.UTC),
            num_bars=252,
        )
        
        strategy = create_strategy("lstm")
        
        result = runner.run_backtest(
            strategy_name="LSTM Temporal",
            strategy_fn=strategy,
            market_data=market_data,
            model_name="lstm",
            version="1.0",
        )
        
        assert result.metrics.total_trades >= 0
        assert result.dsr_result is not None
        print(f"\nLSTM: Sharpe={result.metrics.sharpe_ratio:.2f}, DSR p-value={result.dsr_result.p_value:.4f}")
    
    def test_tft_backtest(self):
        """Test TFT Forecaster model strategy."""
        runner = StrategyRunner(
            initial_capital=100000.0,
            num_strategies_tested=6,
        )
        
        market_data = self.generate_realistic_market_data(
            start_date=datetime(2023, 1, 1, tzinfo=pytz.UTC),
            num_bars=252,
        )
        
        strategy = create_strategy("tft")
        
        result = runner.run_backtest(
            strategy_name="TFT Forecaster",
            strategy_fn=strategy,
            market_data=market_data,
            model_name="tft",
            version="1.0",
        )
        
        assert result.metrics.total_trades >= 0
        assert result.dsr_result is not None
        print(f"\nTFT: Sharpe={result.metrics.sharpe_ratio:.2f}, DSR p-value={result.dsr_result.p_value:.4f}")
    
    def test_genetic_backtest(self):
        """Test Genetic Algorithm strategy."""
        runner = StrategyRunner(
            initial_capital=100000.0,
            num_strategies_tested=6,
        )
        
        market_data = self.generate_realistic_market_data(
            start_date=datetime(2023, 1, 1, tzinfo=pytz.UTC),
            num_bars=252,
        )
        
        strategy = create_strategy("genetic")
        
        result = runner.run_backtest(
            strategy_name="Genetic Algorithm",
            strategy_fn=strategy,
            market_data=market_data,
            model_name="genetic",
            version="1.0",
        )
        
        assert result.metrics.total_trades >= 0
        assert result.dsr_result is not None
        print(f"\nGenetic: Sharpe={result.metrics.sharpe_ratio:.2f}, DSR p-value={result.dsr_result.p_value:.4f}")
    
    def test_ensemble_backtest(self):
        """Test Ensemble Stacking strategy."""
        runner = StrategyRunner(
            initial_capital=100000.0,
            num_strategies_tested=6,
        )
        
        market_data = self.generate_realistic_market_data(
            start_date=datetime(2023, 1, 1, tzinfo=pytz.UTC),
            num_bars=252,
        )
        
        strategy = create_strategy("ensemble")
        
        result = runner.run_backtest(
            strategy_name="Ensemble Stacking",
            strategy_fn=strategy,
            market_data=market_data,
            model_name="ensemble",
            version="1.0",
        )
        
        assert result.metrics.total_trades >= 0
        assert result.dsr_result is not None
        print(f"\nEnsemble: Sharpe={result.metrics.sharpe_ratio:.2f}, DSR p-value={result.dsr_result.p_value:.4f}")
    
    def test_all_models_comparison(self):
        """Run all models and generate comparison report."""
        runner = StrategyRunner(
            initial_capital=100000.0,
            num_strategies_tested=6,
        )
        
        market_data = self.generate_realistic_market_data(
            start_date=datetime(2023, 1, 1, tzinfo=pytz.UTC),
            num_bars=252,
        )
        
        models = [
            ("wavelet", "Wavelet Denoiser"),
            ("hmm", "HMM Regime Detector"),
            ("lstm", "LSTM Temporal"),
            ("tft", "TFT Forecaster"),
            ("genetic", "Genetic Algorithm"),
            ("ensemble", "Ensemble Stacking"),
        ]
        
        results = {}
        
        for model_name, strategy_name in models:
            strategy = create_strategy(model_name)
            result = runner.run_backtest(
                strategy_name=strategy_name,
                strategy_fn=strategy,
                market_data=market_data,
                model_name=model_name,
                version="1.0",
            )
            results[model_name] = result
        
        # Generate summary
        summary = runner.summary()
        print(f"\n{summary}")
        
        # Assert all models have results
        assert len(results) == 6
        assert all(r.dsr_result is not None for r in results.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

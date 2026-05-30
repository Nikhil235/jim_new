"""
Comprehensive Unit Tests for HMM Pro Regime Detector

Covers:
- 20 unit tests similar to test_wavelet_pro.py
- All core functionality
- Edge cases and error handling
- Integration with ensemble
"""

import sys
import os
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.hmm_pro import HMMProDetector, run_hmm_pro


class TestHMMProBasics:
    """Test basic initialization and module functions"""
    
    def test_001_module_import(self):
        """Test that HMM Pro module imports without errors"""
        from models import hmm_pro
        assert hasattr(hmm_pro, 'HMMProDetector')
        assert hasattr(hmm_pro, 'run_hmm_pro')
        
    def test_002_detector_init_default(self):
        """Test HMMProDetector initialization with defaults"""
        detector = HMMProDetector()
        assert detector.n_states == 4
        assert detector.n_mix == 3
        assert detector.is_trained == False
        assert detector.model is not None  # Should initialize GMMHMM or fallback
        
    def test_003_detector_init_custom(self):
        """Test HMMProDetector initialization with custom parameters"""
        detector = HMMProDetector(n_states=3, n_mix=2, retrain_interval=250)
        assert detector.n_states == 3
        assert detector.n_mix == 2
        assert detector.retrain_interval == 250


class TestHMMProFeatureEngineering:
    """Test feature engineering pipeline"""
    
    @staticmethod
    def create_test_data(n_bars=200, include_macro=True):
        """Helper to create test OHLCV data"""
        dates = pd.date_range(start='2024-01-01', periods=n_bars, freq='1h')
        np.random.seed(42)
        close = np.linspace(1900, 2000, n_bars) + np.cumsum(np.random.randn(n_bars) * 5)
        high = close + np.abs(np.random.randn(n_bars) * 2)
        low = close - np.abs(np.random.randn(n_bars) * 2)
        open_prices = close + np.random.randn(n_bars) * 2
        volume = np.random.randint(1000000, 5000000, n_bars)
        
        df = pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
        }, index=dates)
        
        if include_macro:
            df['dxy_returns'] = np.random.randn(n_bars) * 0.01
            df['us10y_returns'] = np.random.randn(n_bars) * 0.005
            df['gold_silver_ratio'] = np.linspace(60, 70, n_bars)
        
        return df
    
    def test_010_feature_engineering_basic(self):
        """Test basic feature engineering with full data"""
        detector = HMMProDetector()
        df = self.create_test_data(200, include_macro=True)
        
        X, idx = detector._engineer_features(df)
        
        assert X.shape[0] > 100  # Should have many valid rows after dropna
        assert X.shape[1] == 23  # Should have 23 features with macro
        assert np.all(np.isfinite(X))  # No NaN or Inf
        
    def test_011_feature_engineering_no_macro(self):
        """Test feature engineering without macro data"""
        detector = HMMProDetector()
        df = self.create_test_data(200, include_macro=False)
        
        X, idx = detector._engineer_features(df)
        
        assert X.shape[0] > 100
        assert X.shape[1] == 20  # Should have 20 features without macro
        assert np.all(np.isfinite(X))
        
    def test_012_feature_engineering_small_dataset(self):
        """Test feature engineering with very small dataset"""
        detector = HMMProDetector()
        df = self.create_test_data(15, include_macro=True)
        
        X, idx = detector._engineer_features(df)
        
        # After dropna, should have very few rows
        assert X.shape[0] >= 0
        if len(X) > 0:
            assert np.all(np.isfinite(X))
    
    def test_013_feature_normalization(self):
        """Test feature normalization (fit mode)"""
        detector = HMMProDetector()
        df = self.create_test_data(200, include_macro=True)
        
        X, _ = detector._engineer_features(df)
        X_norm = detector._normalize_features(X.copy(), fit=True)
        
        # After normalization, mean should be ~0, std ~1
        assert np.abs(X_norm.mean(axis=0)).max() < 0.5  # Slightly lenient
        assert np.abs(X_norm.std(axis=0).mean() - 1.0) < 0.5
        
    def test_014_feature_normalization_inference(self):
        """Test feature normalization (inference mode)"""
        detector = HMMProDetector()
        df1 = self.create_test_data(200, include_macro=True)
        df2 = self.create_test_data(50, include_macro=True)
        
        X1, _ = detector._engineer_features(df1)
        X1_norm = detector._normalize_features(X1.copy(), fit=True)
        
        X2, _ = detector._engineer_features(df2)
        X2_norm = detector._normalize_features(X2.copy(), fit=False)
        
        # Both should be normalized without error
        assert X1_norm.shape[0] > 0
        assert X2_norm.shape[0] > 0
        assert np.all(np.isfinite(X1_norm))
        assert np.all(np.isfinite(X2_norm))


class TestHMMProTraining:
    """Test training functionality"""
    
    def test_020_training_basic(self):
        """Test basic model training"""
        detector = HMMProDetector()
        df = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        
        result = detector.train(df)
        
        assert detector.is_trained == True
        assert result['train_samples'] > 100
        assert result['n_features'] == 23
        assert detector._feature_count == 23
        
    def test_021_training_stores_feature_count(self):
        """Test that training stores feature count for alignment"""
        detector = HMMProDetector()
        df = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        
        detector.train(df)
        
        assert detector._feature_count is not None
        assert detector._feature_count == 23
        
    def test_022_training_state_stats(self):
        """Test that training computes state statistics"""
        detector = HMMProDetector()
        df = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        
        detector.train(df)
        
        assert detector._state_stats is not None
        assert len(detector._state_stats) == 4  # 4 states
        
        for state_id, stats in detector._state_stats.items():
            assert 'pct_time' in stats
            assert 'mean_return' in stats
            assert 'volatility' in stats
            assert 0 <= stats['pct_time'] <= 1
            
    def test_023_training_insufficient_data(self):
        """Test training with insufficient data"""
        detector = HMMProDetector()
        df = TestHMMProFeatureEngineering.create_test_data(20, include_macro=True)
        
        result = detector.train(df)
        
        # Should handle gracefully without crashing
        assert isinstance(result, dict)


class TestHMMProInference:
    """Test state prediction and signal generation"""
    
    def test_030_predict_state_basic(self):
        """Test basic state prediction"""
        detector = HMMProDetector()
        df = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        
        detector.train(df)
        state_id, probs, state_name = detector.predict_state(df)
        
        assert state_id in [0, 1, 2, 3]
        assert len(probs) == 4
        assert np.isclose(probs.sum(), 1.0)
        assert all(0 <= p <= 1 for p in probs)
        assert state_name in ['BULLISH', 'NEUTRAL', 'BEARISH', 'REVERSAL']
        
    def test_031_predict_state_feature_alignment(self):
        """Test feature alignment during prediction with mismatched dimensions"""
        detector = HMMProDetector()
        df_train = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        
        detector.train(df_train)
        
        # Predict with data missing macro columns
        df_predict = TestHMMProFeatureEngineering.create_test_data(100, include_macro=False)
        
        state_id, probs, state_name = detector.predict_state(df_predict)
        
        # Should succeed with padding
        assert state_id in [0, 1, 2, 3]
        assert np.isclose(probs.sum(), 1.0)
        
    def test_032_predict_state_empty_data(self):
        """Test prediction with empty data"""
        detector = HMMProDetector()
        df = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        
        detector.train(df)
        
        # Empty DataFrame should return default
        empty_df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        state_id, probs, state_name = detector.predict_state(empty_df)
        
        assert state_id == 1  # Default NEUTRAL
        assert state_name == 'NEUTRAL'
        
    def test_033_generate_signal_basic(self):
        """Test basic signal generation"""
        detector = HMMProDetector()
        df = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        
        signal_dict = detector.generate_signal(df)
        
        assert 'signal' in signal_dict
        assert signal_dict['signal'] in ['LONG', 'SHORT', 'HOLD']
        assert 'confidence' in signal_dict
        assert 0 <= signal_dict['confidence'] <= 1
        assert 'reasoning' in signal_dict
        
    def test_034_generate_signal_lazy_training(self):
        """Test that generate_signal trains if not already trained"""
        detector = HMMProDetector()
        df = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        
        assert detector.is_trained == False
        
        signal_dict = detector.generate_signal(df)
        
        assert detector.is_trained == True
        assert signal_dict['signal'] in ['LONG', 'SHORT', 'HOLD']
        
    def test_035_generate_signal_insufficient_data(self):
        """Test signal generation with insufficient data"""
        detector = HMMProDetector()
        df = TestHMMProFeatureEngineering.create_test_data(15, include_macro=True)
        
        signal_dict = detector.generate_signal(df)
        
        assert signal_dict['signal'] == 'HOLD'
        assert signal_dict['confidence'] == 0.0
        

class TestHMMProEdgeCases:
    """Test edge cases and robustness"""
    
    def test_040_constant_prices(self):
        """Test with constant prices (zero volatility)"""
        detector = HMMProDetector()
        df = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        df['close'] = 2000.0
        df['open'] = 2000.0
        df['high'] = 2000.0
        df['low'] = 2000.0
        
        detector.train(df)
        state_id, probs, state_name = detector.predict_state(df)
        
        # Should handle without NaN/Inf
        assert np.all(np.isfinite(probs))
        assert state_id in [0, 1, 2, 3]
        
    def test_041_extreme_prices(self):
        """Test with extreme price values"""
        detector = HMMProDetector()
        df = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        df['close'] = df['close'] * 1e6  # Very large values
        
        detector.train(df)
        signal = detector.generate_signal(df)
        
        assert signal['signal'] in ['LONG', 'SHORT', 'HOLD']
        assert 0 <= signal['confidence'] <= 1
        
    def test_042_missing_columns(self):
        """Test with missing optional columns"""
        detector = HMMProDetector()
        df = TestHMMProFeatureEngineering.create_test_data(200, include_macro=False)
        
        # Train without macro
        detector.train(df)
        assert detector._feature_count == 20
        
        # Predict still without macro
        signal = detector.generate_signal(df)
        assert signal['signal'] in ['LONG', 'SHORT', 'HOLD']
        
    def test_043_unicode_index(self):
        """Test with non-datetime index"""
        detector = HMMProDetector()
        df = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        df.index = [f"Bar_{i}" for i in range(len(df))]
        
        detector.train(df)
        signal = detector.generate_signal(df)
        
        assert signal['signal'] in ['LONG', 'SHORT', 'HOLD']


class TestHMMProIntegration:
    """Test integration with ensemble and runner functions"""
    
    def test_050_run_hmm_pro_function(self):
        """Test the module-level run_hmm_pro() function"""
        df = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        
        signal = run_hmm_pro(df)
        
        assert 'signal' in signal
        assert signal['signal'] in ['LONG', 'SHORT', 'HOLD']
        assert 'confidence' in signal
        assert 0 <= signal['confidence'] <= 1
        
    def test_051_run_hmm_pro_singleton(self):
        """Test that run_hmm_pro uses singleton pattern"""
        df1 = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        df2 = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        
        signal1 = run_hmm_pro(df1)
        signal2 = run_hmm_pro(df2)
        
        # Both should succeed (singleton reused)
        assert signal1['signal'] in ['LONG', 'SHORT', 'HOLD']
        assert signal2['signal'] in ['LONG', 'SHORT', 'HOLD']
        
    def test_052_align_features_method(self):
        """Test the _align_features method directly"""
        detector = HMMProDetector()
        df = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        
        detector.train(df)
        assert detector._feature_count == 23
        
        # Test padding
        X_small = np.random.randn(10, 20)
        X_aligned = detector._align_features(X_small)
        
        assert X_aligned.shape == (10, 23)
        
        # Test no-op
        X_exact = np.random.randn(10, 23)
        X_aligned = detector._align_features(X_exact)
        
        assert X_aligned.shape == (10, 23)


class TestHMMProConsistency:
    """Test consistency and determinism"""
    
    def test_060_signal_consistency(self):
        """Test that same data produces consistent signals"""
        detector = HMMProDetector(random_state=42)
        df = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        
        signal1 = detector.generate_signal(df)
        signal2 = detector.generate_signal(df)
        
        # Same model should produce same signal
        assert signal1['signal'] == signal2['signal']
        assert signal1['confidence'] == signal2['confidence']
        
    def test_061_state_order_stability(self):
        """Test that state ordering is stable after training"""
        detector = HMMProDetector(random_state=42)
        df = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        
        detector.train(df)
        state_order_1 = detector._state_order.copy() if detector._state_order else None
        
        # Predict multiple times
        for _ in range(5):
            detector.predict_state(df)
        
        # State order should remain unchanged
        state_order_2 = detector._state_order.copy() if detector._state_order else None
        
        assert state_order_1 == state_order_2


class TestHMMProConfidence:
    """Test confidence scoring and probability distributions"""
    
    def test_070_confidence_range(self):
        """Test that confidence values always in [0, 1]"""
        detector = HMMProDetector()
        
        for _ in range(10):
            df = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
            signal = detector.generate_signal(df)
            
            assert 0 <= signal['confidence'] <= 1
            
    def test_071_probability_normalization(self):
        """Test that state probabilities sum to 1"""
        detector = HMMProDetector()
        df = TestHMMProFeatureEngineering.create_test_data(200, include_macro=True)
        
        detector.train(df)
        
        for _ in range(5):
            _, probs, _ = detector.predict_state(df)
            assert np.isclose(probs.sum(), 1.0, rtol=1e-6)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

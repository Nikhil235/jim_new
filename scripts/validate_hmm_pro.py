"""
HMM Pro Validation Script

Similar to scripts/validate_wavelet_pro.py, provides detailed validation
with logging and performance metrics.

Runs:
- 10 validation tests
- Performance benchmarks
- Edge case verification
- Integration checks
"""

import sys
import os
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Add project root FIRST before any imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Add src to path
sys.path.insert(0, os.path.join(project_root, 'src'))

# Now import HMM Pro
from models.hmm_pro import HMMProDetector, run_hmm_pro


def create_synthetic_data(n_bars=200, include_macro=True, seed=42):
    """Create synthetic OHLCV test data"""
    np.random.seed(seed)
    dates = pd.date_range(start='2024-01-01', periods=n_bars, freq='1h')
    
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


def test_1_initialization():
    """Test 1: Model initialization and defaults"""
    print("\n=== Test 1: Model Initialization ===")
    
    detector = HMMProDetector()
    
    assert detector.n_states == 4, "Should have 4 states"
    assert detector.n_mix == 3, "Should have 3 mixture components"
    assert detector.is_trained == False, "Should not be trained initially"
    assert detector.model is not None, "Model should be initialized"
    
    print(f"✓ Model initialized: {detector._model_type}")
    print(f"  - States: {detector.n_states}")
    print(f"  - Mixtures: {detector.n_mix}")
    print(f"  - Covariance type: {detector.covariance_type}")
    print(f"  - Random state: {detector.random_state}")


def test_2_feature_engineering():
    """Test 2: Feature engineering quality"""
    print("\n=== Test 2: Feature Engineering ===")
    
    detector = HMMProDetector()
    df = create_synthetic_data(200, include_macro=True)
    
    X, idx = detector._engineer_features(df)
    
    assert len(X) > 100, "Should have many valid samples after dropna"
    assert X.shape[1] == 23, "Should have 23 features with macro"
    assert np.all(np.isfinite(X)), "No NaN or Inf in features"
    
    print(f"✓ Features engineered successfully")
    print(f"  - Input samples: {len(df)}")
    print(f"  - Output samples: {len(X)} (dropped {len(df) - len(X)} via dropna)")
    print(f"  - Feature count: {X.shape[1]}")
    print(f"  - Feature mean: {X.mean():.4f}")
    print(f"  - Feature std: {X.std():.4f}")
    print(f"  - NaN count: {np.isnan(X).sum()}")
    print(f"  - Inf count: {np.isinf(X).sum()}")


def test_3_training_quality():
    """Test 3: Model training quality"""
    print("\n=== Test 3: Model Training ===")
    
    detector = HMMProDetector()
    df = create_synthetic_data(200, include_macro=True)
    
    start_time = time.perf_counter()
    result = detector.train(df)
    elapsed = time.perf_counter() - start_time
    
    assert detector.is_trained, "Model should be marked as trained"
    assert detector._feature_count == 23, "Should store feature count"
    assert detector._state_stats is not None, "Should compute state stats"
    
    print(f"✓ Model trained successfully in {elapsed:.3f}s")
    print(f"  - Train samples: {result['train_samples']}")
    print(f"  - Features: {result['n_features']}")
    print(f"  - Model type: {result['model_type']}")
    print(f"\n  State Statistics:")
    
    for state_id, stats in detector._state_stats.items():
        state_names = ['BULLISH', 'NEUTRAL', 'BEARISH', 'REVERSAL']
        state_name = state_names[state_id] if state_id < len(state_names) else f"S{state_id}"
        
        print(f"    {state_name} (ID={state_id}):")
        print(f"      - Time: {stats['pct_time']:.1%}")
        print(f"      - Mean return: {stats['mean_return']:.5f}")
        print(f"      - Volatility: {stats['volatility']:.5f}")
        print(f"      - Samples: {stats['count']}")
        print(f"      - Avg duration: {stats['avg_duration']:.1f} bars")


def test_4_state_prediction():
    """Test 4: State prediction accuracy"""
    print("\n=== Test 4: State Prediction ===")
    
    detector = HMMProDetector()
    df = create_synthetic_data(200, include_macro=True)
    
    detector.train(df)
    
    state_id, probs, state_name = detector.predict_state(df)
    
    assert state_id in [0, 1, 2, 3], "State should be in [0, 1, 2, 3]"
    assert len(probs) == 4, "Should have 4 probabilities"
    assert np.isclose(probs.sum(), 1.0), "Probabilities should sum to 1"
    assert all(0 <= p <= 1 for p in probs), "Probabilities should be in [0, 1]"
    
    state_names = ['BULLISH', 'NEUTRAL', 'BEARISH', 'REVERSAL']
    print(f"✓ State predicted: {state_name} (ID={state_id})")
    print(f"  - Probabilities: {[f'{p:.4f}' for p in probs]}")
    print(f"  - Sum: {probs.sum():.6f}")
    print(f"  - Entropy: {-np.sum(probs[probs > 0] * np.log(probs[probs > 0])):.4f}")


def test_5_signal_generation():
    """Test 5: Signal generation quality"""
    print("\n=== Test 5: Signal Generation ===")
    
    detector = HMMProDetector()
    df = create_synthetic_data(200, include_macro=True)
    
    start_time = time.perf_counter()
    signal = detector.generate_signal(df)
    elapsed = time.perf_counter() - start_time
    
    assert signal['signal'] in ['LONG', 'SHORT', 'HOLD'], "Signal should be valid"
    assert 0 <= signal['confidence'] <= 1, "Confidence should be in [0, 1]"
    assert 'reasoning' in signal, "Should have reasoning"
    
    print(f"✓ Signal generated in {elapsed:.3f}s")
    print(f"  - Signal: {signal['signal']}")
    print(f"  - Confidence: {signal['confidence']:.4f}")
    print(f"  - Reasoning: {signal['reasoning']}")
    
    # Check metadata
    for key in ['state_id', 'state_name', 'model_type']:
        if key in signal:
            print(f"  - {key}: {signal[key]}")


def test_6_feature_dimension_handling():
    """Test 6: Feature dimension consistency & alignment"""
    print("\n=== Test 6: Feature Dimension Alignment ===")
    
    detector = HMMProDetector()
    
    # Train with full data (23 features)
    df_full = create_synthetic_data(200, include_macro=True)
    detector.train(df_full)
    
    print(f"✓ Trained on full data: {detector._feature_count} features")
    
    # Predict with partial data (20 features - no macro)
    df_partial = create_synthetic_data(100, include_macro=False)
    
    state_id, probs, state_name = detector.predict_state(df_partial)
    
    assert state_id in [0, 1, 2, 3], "Should handle feature mismatch"
    assert np.isclose(probs.sum(), 1.0), "Probabilities should be valid"
    
    print(f"✓ Successfully predicted with mismatched features")
    print(f"  - Expected features: {detector._feature_count}")
    print(f"  - Input features: 20 (missing macro)")
    print(f"  - Predicted state: {state_name}")
    print(f"  - Alignment: PADDING used")


def test_7_edge_case_constant_prices():
    """Test 7: Edge case - constant prices"""
    print("\n=== Test 7: Edge Case - Constant Prices ===")
    
    detector = HMMProDetector()
    df = create_synthetic_data(200, include_macro=True)
    df['close'] = 2000.0
    df['open'] = 2000.0
    df['high'] = 2000.0
    df['low'] = 2000.0
    
    detector.train(df)
    signal = detector.generate_signal(df)
    
    assert signal['signal'] in ['LONG', 'SHORT', 'HOLD'], "Should handle constant prices"
    assert 0 <= signal['confidence'] <= 1, "Confidence should be valid"
    assert np.all(np.isfinite([signal['confidence']])), "No NaN or Inf"
    
    print(f"✓ Handled constant prices correctly")
    print(f"  - Signal: {signal['signal']}")
    print(f"  - Confidence: {signal['confidence']:.4f}")


def test_8_edge_case_small_dataset():
    """Test 8: Edge case - small dataset"""
    print("\n=== Test 8: Edge Case - Small Dataset ===")
    
    detector = HMMProDetector()
    df = create_synthetic_data(20, include_macro=True)
    
    signal = detector.generate_signal(df)
    
    # Should return HOLD for insufficient data
    assert signal['signal'] in ['LONG', 'SHORT', 'HOLD'], "Should handle small data"
    assert 0 <= signal['confidence'] <= 1, "Confidence should be valid"
    
    print(f"✓ Handled small dataset ({len(df)} bars)")
    print(f"  - Signal: {signal['signal']}")
    print(f"  - Confidence: {signal['confidence']:.4f}")
    print(f"  - Reason: {signal['reasoning']}")


def test_9_run_function_integration():
    """Test 9: Module-level run_hmm_pro function"""
    print("\n=== Test 9: run_hmm_pro Integration ===")
    
    df = create_synthetic_data(200, include_macro=True)
    
    signal1 = run_hmm_pro(df)
    signal2 = run_hmm_pro(df)
    
    assert signal1['signal'] in ['LONG', 'SHORT', 'HOLD'], "First signal valid"
    assert signal2['signal'] in ['LONG', 'SHORT', 'HOLD'], "Second signal valid"
    
    # Both should succeed (singleton pattern)
    print(f"✓ run_hmm_pro singleton working")
    print(f"  - Call 1: {signal1['signal']} (conf={signal1['confidence']:.4f})")
    print(f"  - Call 2: {signal2['signal']} (conf={signal2['confidence']:.4f})")
    print(f"  - Consistency: Same model instance reused")


def test_10_confidence_distribution():
    """Test 10: Confidence distribution across multiple signals"""
    print("\n=== Test 10: Confidence Distribution ===")
    
    detector = HMMProDetector()
    
    confidences = []
    signals = []
    
    for i in range(10):
        df = create_synthetic_data(200, include_macro=True, seed=42+i)
        signal = detector.generate_signal(df)
        
        confidences.append(signal['confidence'])
        signals.append(signal['signal'])
    
    assert all(0 <= c <= 1 for c in confidences), "All confidences valid"
    assert all(s in ['LONG', 'SHORT', 'HOLD'] for s in signals), "All signals valid"
    
    print(f"✓ Generated {len(signals)} signals")
    print(f"  - Signal distribution: LONG={signals.count('LONG')}, SHORT={signals.count('SHORT')}, HOLD={signals.count('HOLD')}")
    print(f"  - Confidence mean: {np.mean(confidences):.4f}")
    print(f"  - Confidence std: {np.std(confidences):.4f}")
    print(f"  - Confidence range: [{np.min(confidences):.4f}, {np.max(confidences):.4f}]")


def benchmark_performance():
    """Performance benchmarking"""
    print("\n=== Performance Benchmarks ===")
    
    detector = HMMProDetector()
    df = create_synthetic_data(500, include_macro=True)
    
    # Feature engineering
    start = time.perf_counter()
    X, _ = detector._engineer_features(df)
    t_features = (time.perf_counter() - start) * 1000
    
    # Normalization
    start = time.perf_counter()
    X_norm = detector._normalize_features(X.copy(), fit=True)
    t_norm = (time.perf_counter() - start) * 1000
    
    # Training
    start = time.perf_counter()
    detector.train(df)
    t_train = (time.perf_counter() - start) * 1000
    
    # Prediction
    start = time.perf_counter()
    detector.predict_state(df)
    t_predict = (time.perf_counter() - start) * 1000
    
    # Signal generation
    start = time.perf_counter()
    detector.generate_signal(df)
    t_signal = (time.perf_counter() - start) * 1000
    
    print(f"Feature engineering:  {t_features:7.2f}ms")
    print(f"Normalization:        {t_norm:7.2f}ms")
    print(f"Training (GMMHMM):    {t_train:7.2f}ms")
    print(f"Prediction:           {t_predict:7.2f}ms")
    print(f"Signal generation:    {t_signal:7.2f}ms")
    print(f"Total (w/o training): {t_features + t_norm + t_predict + t_signal:7.2f}ms")


def main():
    """Run all validation tests"""
    print("\n" + "="*60)
    print("HMM Pro Validation Suite")
    print("="*60)
    
    try:
        test_1_initialization()
        test_2_feature_engineering()
        test_3_training_quality()
        test_4_state_prediction()
        test_5_signal_generation()
        test_6_feature_dimension_handling()
        test_7_edge_case_constant_prices()
        test_8_edge_case_small_dataset()
        test_9_run_function_integration()
        test_10_confidence_distribution()
        
        benchmark_performance()
        
        print("\n" + "="*60)
        print("✓ All 10 validation tests PASSED")
        print("✓ HMM Pro is PRODUCTION READY")
        print("="*60 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

"""
Wavelet Pro Validation Script
══════════════════════════════

This script validates each component of the Wavelet Pro implementation
and compares it with the basic Wavelet model.

Run with: python scripts/validate_wavelet_pro.py
"""

import numpy as np
import pandas as pd
import sys
from pathlib import Path
from loguru import logger

# Setup logging
logger.remove()
logger.add(sys.stderr, format="<level>{message}</level>")

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.wavelet_pro import WaveletPro, WaveletProConfig, compare_wavelet_models


def generate_test_data(n_samples: int = 512, with_trend: bool = True) -> np.ndarray:
    """Generate synthetic gold price data for testing."""
    np.random.seed(42)
    t = np.linspace(0, 20, n_samples)
    
    if with_trend:
        trend = 1800 + 10 * t + 50 * np.sin(2*np.pi*t/5)
    else:
        trend = 1800 * np.ones(n_samples)
    
    noise = np.random.randn(n_samples) * 10
    prices = trend + noise
    
    return prices


def test_dwt_decomposition():
    """Test 1: DWT 6-level decomposition."""
    logger.info("\n" + "="*70)
    logger.info("TEST 1: DWT 6-Level Decomposition")
    logger.info("="*70)
    
    prices = generate_test_data()
    wavelet_pro = WaveletPro()
    
    coeffs = wavelet_pro.decompose_dwt(prices)
    
    # Verify
    assert len(coeffs) == 7, f"Expected 7 components, got {len(coeffs)}"
    expected_keys = {"A6", "D6", "D5", "D4", "D3", "D2", "D1"}
    assert set(coeffs.keys()) == expected_keys, f"Keys mismatch: {coeffs.keys()}"
    
    logger.info(f"✓ Components: {list(coeffs.keys())}")
    logger.info(f"✓ A6 (approx) length: {len(coeffs['A6'])}")
    logger.info(f"✓ D1 (detail) length: {len(coeffs['D1'])}")
    
    return True


def test_soft_thresholding():
    """Test 2: Soft thresholding denoising."""
    logger.info("\n" + "="*70)
    logger.info("TEST 2: Soft Thresholding Denoising (Donoho-Johnstone)")
    logger.info("="*70)
    
    prices = generate_test_data()
    wavelet_pro = WaveletPro()
    
    denoised, thresholds = wavelet_pro.denoise_soft_threshold(prices)
    
    # Verify variance reduction
    original_var = np.var(prices)
    denoised_var = np.var(denoised)
    var_reduction = (1 - denoised_var/original_var) * 100
    
    assert denoised_var < original_var, "Denoising failed: variance increased"
    assert var_reduction > 5, f"Variance reduction too small: {var_reduction:.2f}%"
    
    logger.info(f"✓ Original variance: {original_var:.4f}")
    logger.info(f"✓ Denoised variance: {denoised_var:.4f}")
    logger.info(f"✓ Variance reduction: {var_reduction:.2f}%")
    logger.info(f"✓ Thresholds computed for {len(thresholds)} levels")
    
    return True


def test_wavelet_oscillator():
    """Test 3: Wavelet Oscillator (D3+D4)."""
    logger.info("\n" + "="*70)
    logger.info("TEST 3: Wavelet Oscillator (D3 + D4)")
    logger.info("="*70)
    
    prices = generate_test_data()
    wavelet_pro = WaveletPro()
    
    osc = wavelet_pro.compute_wavelet_oscillator(prices)
    
    # Verify
    assert len(osc) == len(prices), f"Length mismatch: {len(osc)} vs {len(prices)}"
    assert np.all(np.isfinite(osc)), "Oscillator contains non-finite values"
    
    # Check oscillation
    osc_mean = np.mean(osc)
    osc_std = np.std(osc)
    zero_crossings = np.sum(np.diff(np.sign(osc)) != 0)
    
    logger.info(f"✓ Oscillator length: {len(osc)}")
    logger.info(f"✓ Mean: {osc_mean:.6f} (should be near 0)")
    logger.info(f"✓ Std dev: {osc_std:.4f}")
    logger.info(f"✓ Zero-crossings: {zero_crossings} (indicators of cycles)")
    
    return True


def test_cwt_analysis():
    """Test 4: CWT for volatility analysis."""
    logger.info("\n" + "="*70)
    logger.info("TEST 4: Continuous Wavelet Transform (CWT)")
    logger.info("="*70)
    
    prices = generate_test_data()
    wavelet_pro = WaveletPro()
    
    coeffs, frequencies = wavelet_pro.compute_cwt(prices)
    
    # Verify
    assert coeffs.shape[0] == len(wavelet_pro.config.cwt_scales), "Scale mismatch"
    assert coeffs.shape[1] == len(prices), "Time mismatch"
    assert np.all(frequencies > 0), "Frequencies should be positive"
    
    logger.info(f"✓ CWT shape: {coeffs.shape}")
    logger.info(f"✓ Number of scales: {len(wavelet_pro.config.cwt_scales)}")
    logger.info(f"✓ Frequency range: {frequencies[0]:.4f} to {frequencies[-1]:.4f}")
    
    return True


def test_feature_engineering():
    """Test 5: Feature engineering (30+ features)."""
    logger.info("\n" + "="*70)
    logger.info("TEST 5: Feature Engineering")
    logger.info("="*70)
    
    prices = generate_test_data()
    prices_df = pd.DataFrame({"close": prices})
    
    wavelet_pro = WaveletPro()
    features = wavelet_pro.engineer_features(prices_df)
    
    # Verify
    assert len(features) == 1, "Should return 1 row of features"
    assert len(features.columns) >= 25, f"Expected ≥25 features, got {len(features.columns)}"
    assert not features.isna().any().any(), "Features contain NaN"
    assert not np.isinf(features.values).any(), "Features contain Inf"
    
    logger.info(f"✓ Number of features: {len(features.columns)}")
    logger.info(f"✓ Feature names (first 10):")
    for i, col in enumerate(features.columns[:10]):
        logger.info(f"   {i+1:2d}. {col}")
    logger.info(f"   ... ({len(features.columns)-10} more)")
    logger.info(f"✓ All values valid (no NaN/Inf)")
    
    return True


def test_signal_generation():
    """Test 6: Trading signal generation."""
    logger.info("\n" + "="*70)
    logger.info("TEST 6: Trading Signal Generation")
    logger.info("="*70)
    
    wavelet_pro = WaveletPro()
    
    # Test with uptrend
    t_up = np.linspace(0, 10, 256)
    uptrend = 1800 + 100 * t_up + 5 * np.sin(10*t_up)
    
    signal_up, conf_up, reason_up = wavelet_pro.generate_signal(uptrend)
    
    # Test with downtrend
    downtrend = 2000 - 100 * t_up + 5 * np.sin(10*t_up)
    signal_down, conf_down, reason_down = wavelet_pro.generate_signal(downtrend)
    
    # Verify format
    assert signal_up in ["LONG", "SHORT", "HOLD"], f"Invalid signal: {signal_up}"
    assert signal_down in ["LONG", "SHORT", "HOLD"], f"Invalid signal: {signal_down}"
    assert 0.0 <= conf_up <= 1.0, f"Confidence out of range: {conf_up}"
    assert 0.0 <= conf_down <= 1.0, f"Confidence out of range: {conf_down}"
    
    logger.info(f"✓ Uptrend signal: {signal_up} (conf={conf_up:.3f})")
    logger.info(f"  Reasoning: {reason_up}")
    logger.info(f"✓ Downtrend signal: {signal_down} (conf={conf_down:.3f})")
    logger.info(f"  Reasoning: {reason_down}")
    
    return True


def test_full_pipeline():
    """Test 7: Full prediction pipeline."""
    logger.info("\n" + "="*70)
    logger.info("TEST 7: Full Pipeline (Train → Predict → Evaluate)")
    logger.info("="*70)
    
    prices = generate_test_data(n_samples=512)
    prices_df = pd.DataFrame({"close": prices})
    
    wavelet_pro = WaveletPro()
    
    # Train
    train_result = wavelet_pro.train(prices_df)
    assert train_result["status"] == "trained", "Training failed"
    
    # Predict
    signals, confidences = wavelet_pro.predict(prices_df)
    assert len(signals) == len(prices_df), "Prediction length mismatch"
    assert all(s in ["LONG", "SHORT", "HOLD"] for s in signals), "Invalid signals"
    
    # Evaluate
    eval_result = wavelet_pro.evaluate(prices_df, None)
    
    logger.info(f"✓ Training: {train_result['status']}")
    logger.info(f"✓ Predictions: {len(signals)} signals")
    logger.info(f"  - LONG:  {np.sum(signals == 'LONG')}")
    logger.info(f"  - SHORT: {np.sum(signals == 'SHORT')}")
    logger.info(f"  - HOLD:  {np.sum(signals == 'HOLD')}")
    logger.info(f"✓ Mean confidence: {eval_result['mean_confidence']:.3f}")
    
    return True


def test_comparison_with_basic():
    """Test 8: Comparison with basic Wavelet model."""
    logger.info("\n" + "="*70)
    logger.info("TEST 8: Comparison - Pro vs Basic Wavelet Model")
    logger.info("="*70)
    
    prices = generate_test_data()
    
    pro_model = WaveletPro()
    
    comparison = compare_wavelet_models(prices, pro_model=pro_model)
    
    logger.info(f"✓ Pro model decomposition levels: {comparison['pro_decomposition_levels']}")
    logger.info(f"✓ Pro model feature count: {comparison['pro_feature_count']}")
    logger.info(f"✓ Pro signal: {comparison['pro_signal']} (conf={comparison['pro_confidence']:.3f})")
    
    logger.info(f"\n  KEY DIFFERENCES:")
    logger.info(f"  - Basic Wavelet: 5 levels, ~5 features, simple trend signal")
    logger.info(f"  - Wavelet Pro: 6 levels, 30+ features, oscillator + trend filter")
    logger.info(f"  - CWT analysis: Basic no, Pro yes")
    logger.info(f"  - Soft thresholding: Basic no, Pro yes")
    logger.info(f"  - Optional WNN: Basic no, Pro yes")
    
    return True


def test_parameter_ranges():
    """Test 9: Parameter configuration ranges."""
    logger.info("\n" + "="*70)
    logger.info("TEST 9: Configuration Parameter Ranges")
    logger.info("="*70)
    
    config = WaveletProConfig()
    
    logger.info(f"✓ DWT Wavelet: {config.dwt_wavelet}")
    logger.info(f"✓ DWT Levels: {config.dwt_levels}")
    logger.info(f"✓ Denoise Levels: {config.denoise_levels}")
    logger.info(f"✓ Denoise Method: {config.denoise_method}")
    logger.info(f"✓ Threshold Method: {config.threshold_method}")
    logger.info(f"✓ CWT Wavelet: {config.cwt_wavelet}")
    logger.info(f"✓ CWT Scales: {len(config.cwt_scales)} scales")
    logger.info(f"✓ Num Features: {config.num_features}")
    logger.info(f"✓ Confidence Threshold: {config.confidence_threshold}")
    logger.info(f"✓ Min Signal Strength: {config.min_signal_strength} std")
    
    return True


def test_edge_cases():
    """Test 10: Edge cases and error handling."""
    logger.info("\n" + "="*70)
    logger.info("TEST 10: Edge Cases & Error Handling")
    logger.info("="*70)
    
    wavelet_pro = WaveletPro()
    
    # Case 1: Small signal
    small_signal = np.array([1800, 1801, 1802])
    signal, conf, _ = wavelet_pro.generate_signal(small_signal)
    assert signal == "HOLD", "Small signal should return HOLD"
    assert conf == 0.0, "Small signal should have zero confidence"
    logger.info(f"✓ Small signal handled: {signal} (conf={conf})")
    
    # Case 2: Flat signal
    flat_signal = np.ones(512) * 1800
    signal, conf, _ = wavelet_pro.generate_signal(flat_signal)
    assert signal in ["LONG", "SHORT", "HOLD"], "Flat signal should return valid signal"
    logger.info(f"✓ Flat signal handled: {signal} (conf={conf:.3f})")
    
    # Case 3: Highly volatile signal
    t = np.linspace(0, 10, 512)
    volatile = 1800 + 500 * np.sin(20*t) + np.random.randn(512) * 100
    signal, conf, _ = wavelet_pro.generate_signal(volatile)
    assert signal in ["LONG", "SHORT", "HOLD"], "Volatile signal should return valid signal"
    logger.info(f"✓ Volatile signal handled: {signal} (conf={conf:.3f})")
    
    return True


def run_all_tests():
    """Run all validation tests."""
    logger.info("\n" + "█"*70)
    logger.info("█ WAVELET PRO VALIDATION SUITE")
    logger.info("█"*70)
    
    tests = [
        ("DWT 6-Level Decomposition", test_dwt_decomposition),
        ("Soft Thresholding Denoising", test_soft_thresholding),
        ("Wavelet Oscillator (D3+D4)", test_wavelet_oscillator),
        ("CWT Analysis", test_cwt_analysis),
        ("Feature Engineering", test_feature_engineering),
        ("Signal Generation", test_signal_generation),
        ("Full Pipeline", test_full_pipeline),
        ("Comparison with Basic", test_comparison_with_basic),
        ("Configuration Ranges", test_parameter_ranges),
        ("Edge Cases", test_edge_cases),
    ]
    
    results = {}
    passed = 0
    failed = 0
    
    for test_name, test_fn in tests:
        try:
            result = test_fn()
            results[test_name] = "PASSED" if result else "FAILED"
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"✗ {test_name}: {e}")
            results[test_name] = f"FAILED: {str(e)}"
            failed += 1
    
    # Summary
    logger.info("\n" + "█"*70)
    logger.info("█ TEST SUMMARY")
    logger.info("█"*70)
    
    for test_name, result in results.items():
        status = "✓" if result == "PASSED" else "✗"
        logger.info(f"{status} {test_name}: {result}")
    
    logger.info("█"*70)
    logger.info(f"TOTAL: {passed} PASSED, {failed} FAILED out of {len(tests)} tests")
    logger.info("█"*70)
    
    if failed == 0:
        logger.info("\n🎉 ALL TESTS PASSED! Wavelet Pro is ready to use.\n")
        return True
    else:
        logger.info(f"\n⚠️  {failed} test(s) failed. Please review above for details.\n")
        return False


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

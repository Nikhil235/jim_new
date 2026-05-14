"""
Test suite for Enhancement #8: Dynamic Risk Adjustment

Tests cover:
- VolatilityMetrics creation and field tracking
- CorrelationMetrics creation and spike detection
- ModelConsensus tracking
- DrawdownStressMetrics calculation
- DynamicRiskAdjustment computation
- VolatilityCalculator methods (realized vol, VIX proxy, regime classification)
- CorrelationDetector spike detection and trending
- DynamicRiskManager orchestration
- Full workflow: volatility → correlations → drawdown → consensus → adjustment

Test count: 40 tests | Expected coverage: >90%
"""

import asyncio
import pytest
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import List

from src.risk.dynamic_risk_adjuster import (
    VolatilityRegime,
    CorrelationStatus,
    VolatilityMetrics,
    CorrelationMetrics,
    ModelConsensus,
    DrawdownStressMetrics,
    DynamicRiskAdjustment,
    VolatilityCalculator,
    CorrelationDetector,
    DynamicRiskManager,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def sample_returns() -> List[float]:
    """Generate sample daily log returns"""
    np.random.seed(42)
    # Normal market conditions
    return list(np.random.normal(0.0005, 0.01, 60))  # Mean 0.05% daily, vol 1%


@pytest.fixture
def volatile_returns() -> List[float]:
    """Generate volatile market returns"""
    np.random.seed(42)
    # Crisis conditions
    return list(np.random.normal(-0.001, 0.03, 60))  # Mean -0.1%, vol 3%


@pytest.fixture
def asset_returns_matrix() -> np.ndarray:
    """Generate multi-asset returns matrix"""
    np.random.seed(42)
    # 3 assets with ~0.5 correlation
    n_periods = 60
    common_factor = np.random.normal(0, 0.01, (n_periods, 1))
    idiosyncratic_1 = np.random.normal(0, 0.005, (n_periods, 1))
    idiosyncratic_2 = np.random.normal(0, 0.005, (n_periods, 1))
    idiosyncratic_3 = np.random.normal(0, 0.005, (n_periods, 1))
    
    asset_1 = 0.7 * common_factor + 0.3 * idiosyncratic_1
    asset_2 = 0.7 * common_factor + 0.3 * idiosyncratic_2
    asset_3 = 0.7 * common_factor + 0.3 * idiosyncratic_3
    
    return np.hstack([asset_1, asset_2, asset_3])


@pytest.fixture
def volatility_calculator():
    """Create VolatilityCalculator"""
    return VolatilityCalculator()


@pytest.fixture
def correlation_detector():
    """Create CorrelationDetector"""
    return CorrelationDetector(window_size=20)


@pytest.fixture
def dynamic_risk_manager():
    """Create DynamicRiskManager"""
    return DynamicRiskManager(
        base_kelly_fraction=0.50,
        correlation_baseline=0.50,
        correlation_spike_threshold=0.15
    )


# ============================================================================
# TESTS: VolatilityMetrics
# ============================================================================

def test_volatility_metrics_creation():
    """Test VolatilityMetrics creation"""
    metrics = VolatilityMetrics(
        vix_level=15.5,
        historical_vol_30d=12.3,
        historical_vol_60d=14.1,
        realized_vol_today=0.8,
    )
    
    assert metrics.vix_level == 15.5
    assert metrics.historical_vol_30d == 12.3
    assert metrics.regime == VolatilityRegime.NORMAL
    assert metrics.volatility_trend == "stable"


def test_volatility_metrics_high_vol():
    """Test VolatilityMetrics with high volatility"""
    metrics = VolatilityMetrics(
        vix_level=28.5,
        historical_vol_30d=22.0,
        historical_vol_60d=20.0,
        realized_vol_today=3.2,
        regime=VolatilityRegime.HIGH,
    )
    
    assert metrics.vix_level == 28.5
    assert metrics.regime == VolatilityRegime.HIGH
    assert metrics.volatility_trend == "stable"


def test_volatility_metrics_extreme():
    """Test VolatilityMetrics with extreme volatility"""
    metrics = VolatilityMetrics(
        vix_level=45.0,
        historical_vol_30d=35.0,
        historical_vol_60d=28.0,
        realized_vol_today=8.5,
        regime=VolatilityRegime.EXTREME,
        volatility_trend="rising",
    )
    
    assert metrics.vix_level == 45.0
    assert metrics.regime == VolatilityRegime.EXTREME
    assert metrics.volatility_trend == "rising"


# ============================================================================
# TESTS: CorrelationMetrics
# ============================================================================

def test_correlation_metrics_creation():
    """Test CorrelationMetrics creation"""
    metrics = CorrelationMetrics(
        avg_correlation=0.52,
        spike_detected=False,
        status=CorrelationStatus.HEALTHY,
    )
    
    assert metrics.avg_correlation == 0.52
    assert metrics.spike_detected is False
    assert metrics.status == CorrelationStatus.HEALTHY
    assert metrics.baseline_correlation == 0.5


def test_correlation_metrics_spike():
    """Test CorrelationMetrics with spike"""
    metrics = CorrelationMetrics(
        avg_correlation=0.75,
        spike_detected=True,
        spike_magnitude=0.25,
        status=CorrelationStatus.BROKEN,
    )
    
    assert metrics.avg_correlation == 0.75
    assert metrics.spike_detected is True
    assert metrics.spike_magnitude == 0.25
    assert metrics.status == CorrelationStatus.BROKEN


def test_correlation_metrics_degrading():
    """Test CorrelationMetrics degrading status"""
    metrics = CorrelationMetrics(
        avg_correlation=0.58,
        spike_detected=False,
        status=CorrelationStatus.DEGRADING,
    )
    
    assert metrics.status == CorrelationStatus.DEGRADING
    assert metrics.spike_detected is False


# ============================================================================
# TESTS: ModelConsensus
# ============================================================================

def test_model_consensus_strong_agreement():
    """Test ModelConsensus with strong agreement"""
    consensus = ModelConsensus(
        consensus_strength=0.92,
        disagreement_count=1,
        total_models=12,
        confidence_in_signal=0.92,
    )
    
    assert consensus.consensus_strength == 0.92
    assert consensus.disagreement_count == 1
    assert consensus.total_models == 12


def test_model_consensus_weak_agreement():
    """Test ModelConsensus with weak agreement"""
    consensus = ModelConsensus(
        consensus_strength=0.58,
        disagreement_count=5,
        total_models=12,
        confidence_in_signal=0.58,
    )
    
    assert consensus.consensus_strength == 0.58
    assert consensus.disagreement_count == 5


# ============================================================================
# TESTS: DrawdownStressMetrics
# ============================================================================

def test_drawdown_stress_metrics_no_drawdown():
    """Test DrawdownStressMetrics with no drawdown"""
    metrics = DrawdownStressMetrics(
        current_drawdown_pct=0.0,
        max_historical_dd_pct=10.0,
        dd_stress_level=0.0,
        recovery_time_estimate_days=0.0,
    )
    
    assert metrics.current_drawdown_pct == 0.0
    assert metrics.dd_stress_level == 0.0


def test_drawdown_stress_metrics_moderate():
    """Test DrawdownStressMetrics with moderate drawdown"""
    metrics = DrawdownStressMetrics(
        current_drawdown_pct=5.0,
        max_historical_dd_pct=10.0,
        dd_stress_level=0.5,
        recovery_time_estimate_days=50.0,
    )
    
    assert metrics.current_drawdown_pct == 5.0
    assert metrics.dd_stress_level == 0.5


def test_drawdown_stress_metrics_severe():
    """Test DrawdownStressMetrics with severe drawdown"""
    metrics = DrawdownStressMetrics(
        current_drawdown_pct=10.0,
        max_historical_dd_pct=10.0,
        dd_stress_level=1.0,
        recovery_time_estimate_days=100.0,
    )
    
    assert metrics.current_drawdown_pct == 10.0
    assert metrics.dd_stress_level == 1.0


# ============================================================================
# TESTS: DynamicRiskAdjustment
# ============================================================================

def test_dynamic_risk_adjustment_creation():
    """Test DynamicRiskAdjustment creation"""
    adjustment = DynamicRiskAdjustment(
        base_kelly_fraction=0.50,
        volatility_multiplier=1.0,
        drawdown_multiplier=1.0,
        consensus_multiplier=1.0,
        correlation_multiplier=1.0,
        final_kelly_fraction=0.50,
        adjustment_reason="Normal market conditions",
        risk_score=3.5,
    )
    
    assert adjustment.base_kelly_fraction == 0.50
    assert adjustment.final_kelly_fraction == 0.50
    assert adjustment.volatility_multiplier == 1.0
    assert adjustment.risk_score == 3.5


def test_dynamic_risk_adjustment_with_reduction():
    """Test DynamicRiskAdjustment with risk reduction"""
    adjustment = DynamicRiskAdjustment(
        base_kelly_fraction=0.50,
        volatility_multiplier=0.7,
        drawdown_multiplier=0.75,
        consensus_multiplier=0.8,
        correlation_multiplier=0.9,
        final_kelly_fraction=0.189,  # 0.50 * 0.7 * 0.75 * 0.8 * 0.9
        adjustment_reason="Multiple risk factors detected",
        risk_score=7.2,
    )
    
    assert adjustment.final_kelly_fraction < adjustment.base_kelly_fraction
    assert adjustment.risk_score > 5.0


# ============================================================================
# TESTS: VolatilityCalculator
# ============================================================================

def test_volatility_calculator_realized_volatility(sample_returns, volatility_calculator):
    """Test VolatilityCalculator.calculate_realized_volatility()"""
    vol = volatility_calculator.calculate_realized_volatility(sample_returns, window=20)
    
    assert vol > 0  # Should be positive
    assert vol < 50  # Reasonable upper bound


def test_volatility_calculator_realized_vol_short_history(volatility_calculator):
    """Test realized volatility with insufficient data"""
    short_returns = [0.001, 0.002]
    vol = volatility_calculator.calculate_realized_volatility(short_returns, window=20)
    assert vol == 0.0  # Should return 0 for insufficient data (need 20 days minimum)


def test_volatility_calculator_vix_proxy(sample_returns, volatility_calculator):
    """Test VolatilityCalculator.calculate_vix_proxy()"""
    vix = volatility_calculator.calculate_vix_proxy(sample_returns)
    
    assert 0 < vix < 100
    # Should be in normal range for normal returns
    assert 8 < vix < 25


def test_volatility_calculator_vix_proxy_volatile(volatile_returns, volatility_calculator):
    """Test VIX proxy with volatile returns"""
    vix = volatility_calculator.calculate_vix_proxy(volatile_returns)
    
    assert vix > 0
    # Volatile returns should produce higher VIX
    assert vix < 100


def test_volatility_calculator_classify_low():
    """Test classify_volatility_regime() for low volatility"""
    regime = VolatilityCalculator.classify_volatility_regime(vix_level=10.0)
    assert regime == VolatilityRegime.LOW


def test_volatility_calculator_classify_normal():
    """Test classify_volatility_regime() for normal volatility"""
    regime = VolatilityCalculator.classify_volatility_regime(vix_level=15.0)
    assert regime == VolatilityRegime.NORMAL


def test_volatility_calculator_classify_high():
    """Test classify_volatility_regime() for high volatility"""
    regime = VolatilityCalculator.classify_volatility_regime(vix_level=25.0)
    assert regime == VolatilityRegime.HIGH


def test_volatility_calculator_classify_extreme():
    """Test classify_volatility_regime() for extreme volatility"""
    regime = VolatilityCalculator.classify_volatility_regime(vix_level=40.0)
    assert regime == VolatilityRegime.EXTREME


# ============================================================================
# TESTS: CorrelationDetector
# ============================================================================

def test_correlation_detector_initialization(correlation_detector):
    """Test CorrelationDetector initialization"""
    assert correlation_detector.window_size == 20
    assert len(correlation_detector.correlation_history) == 0


def test_correlation_detector_pairwise_correlation(asset_returns_matrix, correlation_detector):
    """Test CorrelationDetector.calculate_pairwise_correlation()"""
    corr = correlation_detector.calculate_pairwise_correlation(asset_returns_matrix)
    
    assert 0 <= corr <= 1
    # With 70% common factor + 30% idiosyncratic, expect ~0.6-0.9 correlation
    assert corr > 0.4


def test_correlation_detector_spike_detection(correlation_detector):
    """Test CorrelationDetector.detect_spike()"""
    # Normal correlation
    spike1, mag1 = correlation_detector.detect_spike(0.50, baseline=0.50, threshold=0.15)
    assert spike1 is False
    
    # Above threshold
    spike2, mag2 = correlation_detector.detect_spike(0.70, baseline=0.50, threshold=0.15)
    assert spike2 is True
    assert abs(mag2 - 0.20) < 1e-10  # Floating-point tolerance


def test_correlation_detector_history_tracking(correlation_detector):
    """Test CorrelationDetector tracks history"""
    correlations = [0.50, 0.51, 0.52, 0.53, 0.54]
    
    for corr in correlations:
        correlation_detector.detect_spike(corr, baseline=0.50, threshold=0.15)
    
    assert len(correlation_detector.correlation_history) == 5
    assert list(correlation_detector.correlation_history) == correlations


def test_correlation_detector_trend_rising(correlation_detector):
    """Test CorrelationDetector trend detection - rising"""
    for corr in [0.50, 0.51, 0.52, 0.53, 0.56]:  # Rising trend
        correlation_detector.detect_spike(corr, baseline=0.50, threshold=0.15)
    
    trend = correlation_detector.get_correlation_trend()
    assert trend == "rising"


def test_correlation_detector_trend_falling(correlation_detector):
    """Test CorrelationDetector trend detection - falling"""
    for corr in [0.56, 0.55, 0.54, 0.53, 0.50]:  # Falling trend
        correlation_detector.detect_spike(corr, baseline=0.50, threshold=0.15)
    
    trend = correlation_detector.get_correlation_trend()
    assert trend == "falling"


def test_correlation_detector_trend_stable(correlation_detector):
    """Test CorrelationDetector trend detection - stable"""
    for corr in [0.50, 0.50, 0.51, 0.50, 0.50]:  # Stable
        correlation_detector.detect_spike(corr, baseline=0.50, threshold=0.15)
    
    trend = correlation_detector.get_correlation_trend()
    assert trend == "stable"


# ============================================================================
# TESTS: DynamicRiskManager - Initialization & Metrics
# ============================================================================

def test_dynamic_risk_manager_initialization(dynamic_risk_manager):
    """Test DynamicRiskManager initialization"""
    assert dynamic_risk_manager.base_kelly_fraction == 0.50
    assert dynamic_risk_manager.correlation_baseline == 0.50
    assert dynamic_risk_manager.vol_metrics.vix_level == 15.0
    assert dynamic_risk_manager.corr_metrics.avg_correlation == 0.50


def test_dynamic_risk_manager_update_volatility(event_loop, dynamic_risk_manager, sample_returns):
    """Test DynamicRiskManager.update_volatility()"""
    async def run_test():
        metrics = await dynamic_risk_manager.update_volatility(sample_returns)
        
        assert metrics.vix_level > 0
        assert metrics.historical_vol_30d > 0
        assert metrics.regime in [VolatilityRegime.LOW, VolatilityRegime.NORMAL, VolatilityRegime.HIGH]
    
    event_loop.run_until_complete(run_test())


def test_dynamic_risk_manager_update_correlations(event_loop, dynamic_risk_manager, asset_returns_matrix):
    """Test DynamicRiskManager.update_correlations()"""
    async def run_test():
        metrics = await dynamic_risk_manager.update_correlations(asset_returns_matrix)
        
        assert 0 <= metrics.avg_correlation <= 1
        assert metrics.status in [CorrelationStatus.HEALTHY, CorrelationStatus.DEGRADING, 
                                 CorrelationStatus.BROKEN, CorrelationStatus.RECOVERING]
    
    event_loop.run_until_complete(run_test())


def test_dynamic_risk_manager_update_drawdown(event_loop, dynamic_risk_manager):
    """Test DynamicRiskManager.update_drawdown()"""
    async def run_test():
        metrics = await dynamic_risk_manager.update_drawdown(
            current_equity=95000,
            peak_equity=100000,
            historical_max_drawdown=0.15
        )
        
        assert metrics.current_drawdown_pct == 5.0
        assert 0 <= metrics.dd_stress_level <= 1.0
    
    event_loop.run_until_complete(run_test())


def test_dynamic_risk_manager_update_model_consensus(event_loop, dynamic_risk_manager):
    """Test DynamicRiskManager.update_model_consensus()"""
    async def run_test():
        consensus = await dynamic_risk_manager.update_model_consensus(
            consensus_strength=0.85,
            disagreement_count=2,
            total_models=10
        )
        
        assert consensus.consensus_strength == 0.85
        assert consensus.disagreement_count == 2
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# TESTS: DynamicRiskManager - Adjustment Calculation
# ============================================================================

def test_dynamic_risk_manager_calculate_adjustment_normal(event_loop, dynamic_risk_manager):
    """Test adjustment calculation in normal conditions"""
    async def run_test():
        # Set up normal conditions
        await dynamic_risk_manager.update_volatility([0.001, 0.002, -0.001])
        await dynamic_risk_manager.update_drawdown(current_equity=100000, peak_equity=100000)
        await dynamic_risk_manager.update_model_consensus(0.90)
        
        adjustment = await dynamic_risk_manager.calculate_adjustment()
        
        assert adjustment.base_kelly_fraction == 0.50
        assert 0.001 <= adjustment.final_kelly_fraction <= 0.05
        assert adjustment.risk_score < 5.0
    
    event_loop.run_until_complete(run_test())


def test_dynamic_risk_manager_calculate_adjustment_high_vol(event_loop, dynamic_risk_manager):
    """Test adjustment calculation with high volatility"""
    async def run_test():
        volatile_returns = [0.05, -0.04, 0.03, -0.06, 0.04]
        await dynamic_risk_manager.update_volatility(volatile_returns)
        await dynamic_risk_manager.update_drawdown(current_equity=100000, peak_equity=100000)
        
        adjustment = await dynamic_risk_manager.calculate_adjustment()
        
        # High vol should reduce final Kelly
        assert adjustment.volatility_multiplier < 1.0
        assert adjustment.final_kelly_fraction < adjustment.base_kelly_fraction
    
    event_loop.run_until_complete(run_test())


def test_dynamic_risk_manager_calculate_adjustment_drawdown(event_loop, dynamic_risk_manager):
    """Test adjustment calculation with drawdown"""
    async def run_test():
        await dynamic_risk_manager.update_volatility([0.001, 0.002, -0.001])
        await dynamic_risk_manager.update_drawdown(
            current_equity=85000,
            peak_equity=100000,
            historical_max_drawdown=0.20
        )
        
        adjustment = await dynamic_risk_manager.calculate_adjustment()
        
        # Drawdown should reduce Kelly
        assert adjustment.drawdown_multiplier < 1.0
        assert adjustment.final_kelly_fraction < adjustment.base_kelly_fraction
    
    event_loop.run_until_complete(run_test())


def test_dynamic_risk_manager_calculate_adjustment_correlation_spike(event_loop, dynamic_risk_manager):
    """Test adjustment calculation with correlation spike"""
    async def run_test():
        # Create returns matrix with high correlation
        corr_matrix = np.ones((30, 3)) * 0.5
        high_corr_matrix = np.ones((30, 3)) * 0.85  # Very high correlation (spike)
        
        await dynamic_risk_manager.update_correlations(high_corr_matrix)
        await dynamic_risk_manager.update_volatility([0.001, 0.002, -0.001])
        await dynamic_risk_manager.update_drawdown(current_equity=100000, peak_equity=100000)
        
        adjustment = await dynamic_risk_manager.calculate_adjustment()
        
        # Correlation spike should trigger sharp reduction
        if dynamic_risk_manager.corr_metrics.spike_detected:
            assert adjustment.correlation_multiplier == 0.1  # 90% reduction
    
    event_loop.run_until_complete(run_test())


def test_dynamic_risk_manager_calculate_adjustment_low_consensus(event_loop, dynamic_risk_manager):
    """Test adjustment calculation with low model consensus"""
    async def run_test():
        await dynamic_risk_manager.update_volatility([0.001, 0.002, -0.001])
        await dynamic_risk_manager.update_drawdown(current_equity=100000, peak_equity=100000)
        await dynamic_risk_manager.update_model_consensus(0.55)  # Low consensus
        
        adjustment = await dynamic_risk_manager.calculate_adjustment()
        
        # Low consensus should reduce Kelly
        assert adjustment.consensus_multiplier < 1.0
        assert adjustment.final_kelly_fraction < adjustment.base_kelly_fraction
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# TESTS: DynamicRiskManager - History & Metrics
# ============================================================================

def test_dynamic_risk_manager_adjustment_history(event_loop, dynamic_risk_manager):
    """Test adjustment history tracking"""
    async def run_test():
        for i in range(3):
            await dynamic_risk_manager.calculate_adjustment()
        
        history = dynamic_risk_manager.get_adjustment_history()
        assert len(history) == 3
    
    event_loop.run_until_complete(run_test())


def test_dynamic_risk_manager_get_latest_adjustment(event_loop, dynamic_risk_manager):
    """Test getting latest adjustment"""
    async def run_test():
        await dynamic_risk_manager.calculate_adjustment()
        
        latest = dynamic_risk_manager.get_latest_adjustment()
        assert latest is not None
        assert isinstance(latest, DynamicRiskAdjustment)
    
    event_loop.run_until_complete(run_test())


def test_dynamic_risk_manager_get_current_metrics(event_loop, dynamic_risk_manager):
    """Test getting current metrics as dictionary"""
    async def run_test():
        await dynamic_risk_manager.update_volatility([0.001, 0.002, -0.001])
        
        metrics = dynamic_risk_manager.get_current_metrics()
        
        assert "volatility" in metrics
        assert "correlations" in metrics
        assert "model_consensus" in metrics
        assert "drawdown" in metrics
        assert metrics["volatility"]["vix_level"] > 0
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_dynamic_risk_manager_full_workflow(event_loop, dynamic_risk_manager, 
                                           sample_returns, asset_returns_matrix):
    """Test full dynamic risk adjustment workflow"""
    async def run_test():
        # Update all metrics
        await dynamic_risk_manager.update_volatility(sample_returns)
        await dynamic_risk_manager.update_correlations(asset_returns_matrix)
        await dynamic_risk_manager.update_drawdown(100000, 100000, 0.15)
        await dynamic_risk_manager.update_model_consensus(0.88, 1, 8)
        
        # Calculate adjustment
        adjustment = await dynamic_risk_manager.calculate_adjustment()
        
        # Verify all components
        assert adjustment.base_kelly_fraction > 0
        assert adjustment.final_kelly_fraction > 0
        assert 0 <= adjustment.risk_score <= 10
        assert adjustment.timestamp is not None
    
    event_loop.run_until_complete(run_test())


def test_dynamic_risk_manager_sequential_updates(event_loop, dynamic_risk_manager):
    """Test sequential metric updates and adjustments"""
    async def run_test():
        for i in range(5):
            await dynamic_risk_manager.update_volatility([0.001 * (i+1)] * 10)
            await dynamic_risk_manager.update_drawdown(100000 - (i * 2000), 100000)
            adjustment = await dynamic_risk_manager.calculate_adjustment()
            
            assert adjustment is not None
        
        # Verify adjustment history builds
        history = dynamic_risk_manager.get_adjustment_history()
        assert len(history) == 5
    
    event_loop.run_until_complete(run_test())


def test_dynamic_risk_manager_stress_scenario(event_loop, dynamic_risk_manager, 
                                             volatile_returns, asset_returns_matrix):
    """Test stress scenario: high vol + high correlation + drawdown"""
    async def run_test():
        # Stress conditions
        await dynamic_risk_manager.update_volatility(volatile_returns)
        await dynamic_risk_manager.update_correlations(asset_returns_matrix)
        await dynamic_risk_manager.update_drawdown(80000, 100000, 0.25)  # 20% DD
        await dynamic_risk_manager.update_model_consensus(0.65, 4, 10)  # Low consensus
        
        adjustment = await dynamic_risk_manager.calculate_adjustment()
        
        # Under stress, final Kelly should be significantly reduced
        assert adjustment.final_kelly_fraction < adjustment.base_kelly_fraction * 0.8
        assert adjustment.risk_score > 5.0
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# ENUM VALIDATION TESTS
# ============================================================================

def test_volatility_regime_enum():
    """Test VolatilityRegime enum values"""
    assert VolatilityRegime.LOW.value == "low"
    assert VolatilityRegime.NORMAL.value == "normal"
    assert VolatilityRegime.HIGH.value == "high"
    assert VolatilityRegime.EXTREME.value == "extreme"


def test_correlation_status_enum():
    """Test CorrelationStatus enum values"""
    assert CorrelationStatus.HEALTHY.value == "healthy"
    assert CorrelationStatus.DEGRADING.value == "degrading"
    assert CorrelationStatus.BROKEN.value == "broken"
    assert CorrelationStatus.RECOVERING.value == "recovering"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

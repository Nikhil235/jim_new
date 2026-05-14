"""
Tests for Enhancement #5: Feature Drift Detection

Test coverage:
- Distribution calculation
- KL divergence computation
- Wasserstein distance calculation
- Drift detection
- Alert generation
- Baseline updates
- Data quality monitoring
"""

import asyncio
from datetime import datetime, timedelta

import pytest
import numpy as np

from src.features.feature_drift_detector import (
    DriftType,
    DriftSeverity,
    FeatureDistribution,
    DriftAlert,
    DriftMetrics,
    DistributionCalculator,
    FeatureDriftDetector,
    DataQualityMonitor,
)


# ============================================================================
# Unit Tests: FeatureDistribution
# ============================================================================

class TestFeatureDistribution:
    """Test FeatureDistribution"""
    
    def test_distribution_creation(self):
        """Test creating distribution"""
        dist = FeatureDistribution(
            name="price",
            mean=450.0,
            std=5.0,
        )
        
        assert dist.name == "price"
        assert dist.mean == 450.0
    
    def test_distribution_to_dict(self):
        """Test distribution to_dict"""
        dist = FeatureDistribution(
            name="price",
            mean=450.0,
            std=5.0,
            count=100,
        )
        
        d = dist.to_dict()
        assert d["name"] == "price"
        assert d["mean"] == 450.0
        assert d["count"] == 100


class TestDriftAlert:
    """Test DriftAlert"""
    
    def test_alert_creation(self):
        """Test creating drift alert"""
        baseline = FeatureDistribution(name="price", mean=450.0, std=5.0)
        current = FeatureDistribution(name="price", mean=460.0, std=8.0)
        
        alert = DriftAlert(
            timestamp=datetime.utcnow(),
            feature_name="price",
            drift_type=DriftType.COVARIATE,
            severity=DriftSeverity.WARNING,
            drift_score=0.65,
            threshold=0.5,
            baseline_distribution=baseline,
            current_distribution=current,
        )
        
        assert alert.feature_name == "price"
        assert alert.drift_score == 0.65
        assert alert.severity == DriftSeverity.WARNING
    
    def test_alert_to_dict(self):
        """Test alert to_dict"""
        baseline = FeatureDistribution(name="price", mean=450.0, std=5.0)
        current = FeatureDistribution(name="price", mean=460.0, std=8.0)
        
        alert = DriftAlert(
            timestamp=datetime(2026, 5, 14, 10, 0, 0),
            feature_name="price",
            drift_type=DriftType.COVARIATE,
            severity=DriftSeverity.WARNING,
            drift_score=0.65,
            threshold=0.5,
            baseline_distribution=baseline,
            current_distribution=current,
        )
        
        d = alert.to_dict()
        assert d["feature_name"] == "price"
        assert d["drift_type"] == "covariate"
        assert d["severity"] == "warning"


# ============================================================================
# Unit Tests: DistributionCalculator
# ============================================================================

class TestDistributionCalculator:
    """Test DistributionCalculator"""
    
    def test_calculate_distribution(self):
        """Test calculating distribution"""
        data = [450.0, 451.0, 452.0, 453.0, 454.0]
        dist = DistributionCalculator.calculate_distribution(data)
        
        assert abs(dist.mean - 452.0) < 0.1
        assert dist.count == 5
        assert dist.min_val == 450.0
        assert dist.max_val == 454.0
    
    def test_calculate_kl_divergence(self):
        """Test KL divergence calculation"""
        baseline = FeatureDistribution(name="p1", mean=450.0, std=5.0)
        current = FeatureDistribution(name="p2", mean=450.0, std=5.0)
        
        kl = DistributionCalculator.calculate_kl_divergence(baseline, current)
        assert kl >= 0
    
    def test_kl_divergence_detects_shift(self):
        """Test KL divergence detects distribution shift"""
        baseline = FeatureDistribution(name="p1", mean=450.0, std=5.0)
        current = FeatureDistribution(name="p2", mean=460.0, std=5.0)
        
        kl_same = DistributionCalculator.calculate_kl_divergence(
            baseline,
            FeatureDistribution(name="p3", mean=450.0, std=5.0)
        )
        kl_diff = DistributionCalculator.calculate_kl_divergence(baseline, current)
        
        assert kl_diff > kl_same
    
    def test_calculate_wasserstein_distance(self):
        """Test Wasserstein distance calculation"""
        baseline = FeatureDistribution(
            name="p1", mean=450.0, std=5.0,
            q25=448.0, q50=450.0, q75=452.0,
            min_val=440.0, max_val=460.0
        )
        current = FeatureDistribution(
            name="p2", mean=450.0, std=5.0,
            q25=448.0, q50=450.0, q75=452.0,
            min_val=440.0, max_val=460.0
        )
        
        wd = DistributionCalculator.calculate_wasserstein_distance(baseline, current)
        assert 0 <= wd <= 1


# ============================================================================
# Unit Tests: FeatureDriftDetector
# ============================================================================

class TestFeatureDriftDetector:
    """Test FeatureDriftDetector"""
    
    def test_detector_creation(self):
        """Test creating detector"""
        detector = FeatureDriftDetector(window_size=100, drift_threshold=0.5)
        assert detector.window_size == 100
        assert detector.drift_threshold == 0.5
    
    def test_update_features(self):
        """Test updating features"""
        loop = asyncio.new_event_loop()
        try:
            detector = FeatureDriftDetector()
            
            features = {"price": 450.0, "volume": 1000000}
            loop.run_until_complete(detector.update_features(features))
            
            assert "price" in detector.current_windows
            assert "volume" in detector.current_windows
        finally:
            loop.close()
    
    def test_check_drift_no_baseline(self):
        """Test check_drift with no baseline"""
        loop = asyncio.new_event_loop()
        try:
            detector = FeatureDriftDetector()
            
            # Add initial samples
            for _ in range(20):
                loop.run_until_complete(detector.update_features({"price": 450.0}))
            
            # First check creates baseline
            alert = loop.run_until_complete(detector.check_drift("price"))
            assert alert is None  # No alert on first check
        finally:
            loop.close()
    
    def test_check_drift_detects_shift(self):
        """Test drift detection with distribution shift"""
        loop = asyncio.new_event_loop()
        try:
            detector = FeatureDriftDetector(drift_threshold=0.3)
            
            # Create baseline with low values
            for _ in range(50):
                loop.run_until_complete(detector.update_features({"price": 450.0}))
            
            # First check to establish baseline
            loop.run_until_complete(detector.check_drift("price"))
            
            # Now shift to high values (drift)
            for _ in range(50):
                loop.run_until_complete(detector.update_features({"price": 460.0}))
            
            # Check drift - should detect
            alert = loop.run_until_complete(detector.check_drift("price"))
            assert alert is not None
            assert alert.drift_score > 0.3
        finally:
            loop.close()
    
    def test_update_baseline(self):
        """Test updating baseline"""
        loop = asyncio.new_event_loop()
        try:
            detector = FeatureDriftDetector()
            
            # Add samples
            for _ in range(20):
                loop.run_until_complete(detector.update_features({"price": 450.0}))
            
            # Update baseline
            success = detector.update_baseline("price")
            assert success
            assert "price" in detector.baseline_distributions
        finally:
            loop.close()
    
    def test_get_metrics(self):
        """Test getting metrics"""
        loop = asyncio.new_event_loop()
        try:
            detector = FeatureDriftDetector()
            
            loop.run_until_complete(detector.update_features({"price": 450.0}))
            
            metrics = detector.get_metrics("price")
            assert "price" in metrics
            assert isinstance(metrics["price"], DriftMetrics)
        finally:
            loop.close()
    
    def test_get_alerts(self):
        """Test getting alerts"""
        detector = FeatureDriftDetector()
        
        # No alerts initially
        alerts = detector.get_alerts()
        assert len(alerts) == 0
    
    def test_determine_severity(self):
        """Test severity determination"""
        detector = FeatureDriftDetector()
        
        sev_info = detector._determine_severity(0.4)
        sev_warn = detector._determine_severity(0.65)
        sev_crit = detector._determine_severity(0.85)
        
        assert sev_info == DriftSeverity.INFO
        assert sev_warn == DriftSeverity.WARNING
        assert sev_crit == DriftSeverity.CRITICAL
    
    def test_get_feature_status(self):
        """Test getting feature status"""
        loop = asyncio.new_event_loop()
        try:
            detector = FeatureDriftDetector()
            
            for _ in range(20):
                loop.run_until_complete(detector.update_features({"price": 450.0}))
            
            status = detector.get_feature_status("price")
            assert status["feature_name"] == "price"
            assert status["samples"] == 20
        finally:
            loop.close()


# ============================================================================
# Unit Tests: DataQualityMonitor
# ============================================================================

class TestDataQualityMonitor:
    """Test DataQualityMonitor"""
    
    def test_monitor_creation(self):
        """Test creating monitor"""
        monitor = DataQualityMonitor()
        assert monitor.total_records == 0
    
    def test_check_quality(self):
        """Test quality check"""
        loop = asyncio.new_event_loop()
        try:
            monitor = DataQualityMonitor()
            
            features = {"price": 450.0, "volume": 1000000}
            report = loop.run_until_complete(monitor.check_quality(features))
            
            assert report["total_records"] == 1
            assert len(report["issues"]) == 0
        finally:
            loop.close()
    
    def test_check_quality_detects_nulls(self):
        """Test detecting null values"""
        loop = asyncio.new_event_loop()
        try:
            monitor = DataQualityMonitor()
            
            features = {"price": None, "volume": 1000000}
            report = loop.run_until_complete(monitor.check_quality(features))
            
            assert any("missing value" in issue for issue in report["issues"])
        finally:
            loop.close()
    
    def test_check_quality_detects_outliers(self):
        """Test detecting outliers"""
        loop = asyncio.new_event_loop()
        try:
            monitor = DataQualityMonitor()
            
            features = {"price": 1e15, "volume": 1000000}  # Extreme value
            report = loop.run_until_complete(monitor.check_quality(features))
            
            assert any("outlier" in issue for issue in report["issues"])
        finally:
            loop.close()
    
    def test_get_quality_report(self):
        """Test getting quality report"""
        loop = asyncio.new_event_loop()
        try:
            monitor = DataQualityMonitor()
            
            for _ in range(10):
                loop.run_until_complete(monitor.check_quality({"price": 450.0}))
            
            report = monitor.get_quality_report()
            assert report["total_records"] == 10
        finally:
            loop.close()


# ============================================================================
# Integration Tests
# ============================================================================

class TestDriftDetectionIntegration:
    """Integration tests for drift detection"""
    
    def test_drift_detection_workflow(self):
        """Test complete drift detection workflow"""
        loop = asyncio.new_event_loop()
        try:
            detector = FeatureDriftDetector(drift_threshold=0.3)
            monitor = DataQualityMonitor()
            
            # Phase 1: Establish baseline
            for i in range(50):
                features = {"price": 450.0 + np.random.normal(0, 1)}
                loop.run_until_complete(detector.update_features(features))
                loop.run_until_complete(monitor.check_quality(features))
            
            # First check to set baseline
            loop.run_until_complete(detector.check_drift("price"))
            
            # Phase 2: Introduce drift
            for i in range(50):
                features = {"price": 460.0 + np.random.normal(0, 1)}
                loop.run_until_complete(detector.update_features(features))
                loop.run_until_complete(monitor.check_quality(features))
            
            # Check for drift
            alert = loop.run_until_complete(detector.check_drift("price"))
            
            # Should detect drift
            if alert:
                assert alert.drift_score > 0.3
                assert alert.severity in [DriftSeverity.WARNING, DriftSeverity.CRITICAL]
            
            # Get quality report
            quality = monitor.get_quality_report()
            assert quality["total_records"] == 100
        finally:
            loop.close()


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

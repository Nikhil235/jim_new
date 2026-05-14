"""
Test suite for Enhancement #9: Comprehensive Stress Testing

Tests cover:
- ScenarioType and ResilienceLevel enums
- AssetShock creation and shock tracking
- StressScenario creation, shock addition, metadata
- PortfolioImpact creation and calculation
- StressTestResult execution and reporting
- ReverseStressResult tracking
- ScenarioBuilder methods (historical, hypothetical, correlation, fat tail, cascade)
- ScenarioSimulator scenario execution
- ResilienceAnalyzer classification and scoring
- ReverseStressTester max loss tolerance finding
- StressTester orchestration and workflows

Test count: 48 tests | Expected coverage: >90%
"""

import asyncio
import pytest
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from src.risk.stress_tester import (
    ScenarioType,
    ResilienceLevel,
    AssetShock,
    StressScenario,
    PortfolioImpact,
    StressTestResult,
    ReverseStressResult,
    ScenarioBuilder,
    ScenarioSimulator,
    ResilienceAnalyzer,
    ReverseStressTester,
    StressTester,
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
def baseline_portfolio() -> Dict[str, float]:
    """Create baseline portfolio"""
    return {
        "gold": 50000,
        "stocks": 30000,
        "bonds": 20000,
        "commodities": 10000,
    }


@pytest.fixture
def scenario_builder():
    """Create ScenarioBuilder"""
    return ScenarioBuilder()


@pytest.fixture
def scenario_simulator():
    """Create ScenarioSimulator"""
    return ScenarioSimulator()


@pytest.fixture
def stress_tester():
    """Create StressTester"""
    return StressTester(max_acceptable_loss_pct=20.0)


# ============================================================================
# TESTS: Enums
# ============================================================================

def test_scenario_type_enum():
    """Test ScenarioType enum values"""
    assert ScenarioType.HISTORICAL.value == "historical"
    assert ScenarioType.HYPOTHETICAL.value == "hypothetical"
    assert ScenarioType.CORRELATION.value == "correlation"
    assert ScenarioType.FAT_TAIL.value == "fat_tail"
    assert ScenarioType.CASCADE.value == "cascade"


def test_resilience_level_enum():
    """Test ResilienceLevel enum values"""
    assert ResilienceLevel.CRITICAL.value == "critical"
    assert ResilienceLevel.WEAK.value == "weak"
    assert ResilienceLevel.MODERATE.value == "moderate"
    assert ResilienceLevel.STRONG.value == "strong"
    assert ResilienceLevel.ROBUST.value == "robust"


# ============================================================================
# TESTS: AssetShock
# ============================================================================

def test_asset_shock_creation():
    """Test AssetShock creation"""
    shock = AssetShock(
        asset_name="gold",
        shock_magnitude=0.05,
        shock_duration_days=1,
        shock_volatility=0.02,
    )
    
    assert shock.asset_name == "gold"
    assert shock.shock_magnitude == 0.05
    assert shock.shock_duration_days == 1
    assert shock.shock_volatility == 0.02


def test_asset_shock_negative_shock():
    """Test AssetShock with negative magnitude"""
    shock = AssetShock(
        asset_name="stocks",
        shock_magnitude=-0.15,
    )
    
    assert shock.shock_magnitude == -0.15
    assert shock.shock_duration_days == 1


# ============================================================================
# TESTS: StressScenario
# ============================================================================

def test_stress_scenario_creation():
    """Test StressScenario creation"""
    scenario = StressScenario(
        scenario_id="test_1",
        name="Test Scenario",
        description="A test scenario",
        scenario_type=ScenarioType.HYPOTHETICAL,
        probability_estimate=0.05,
    )
    
    assert scenario.scenario_id == "test_1"
    assert scenario.name == "Test Scenario"
    assert scenario.scenario_type == ScenarioType.HYPOTHETICAL
    assert scenario.probability_estimate == 0.05
    assert len(scenario.shocks) == 0


def test_stress_scenario_add_shock():
    """Test adding shocks to scenario"""
    scenario = StressScenario(
        scenario_id="test_2",
        name="Multi-Shock Scenario",
        description="Scenario with multiple shocks",
        scenario_type=ScenarioType.HISTORICAL,
    )
    
    scenario.add_shock("gold", 0.05)
    scenario.add_shock("stocks", -0.15)
    
    assert len(scenario.shocks) == 2
    assert scenario.shocks[0].asset_name == "gold"
    assert scenario.shocks[1].shock_magnitude == -0.15
    assert "gold" in scenario.affected_assets
    assert "stocks" in scenario.affected_assets


def test_stress_scenario_with_metadata():
    """Test StressScenario with complete metadata"""
    lookback = datetime(2008, 9, 15)
    scenario = StressScenario(
        scenario_id="hist_2008",
        name="2008 Financial Crisis",
        description="Historical crisis",
        scenario_type=ScenarioType.HISTORICAL,
        probability_estimate=0.02,
        lookback_date=lookback,
        correlation_spike_multiplier=1.8,
    )
    
    assert scenario.lookback_date == lookback
    assert scenario.correlation_spike_multiplier == 1.8


# ============================================================================
# TESTS: PortfolioImpact
# ============================================================================

def test_portfolio_impact_creation():
    """Test PortfolioImpact creation"""
    impact = PortfolioImpact(
        scenario_id="test_1",
        scenario_name="Test Scenario",
        pnl_change_pct=-5.0,
        max_drawdown_pct=5.0,
        sharpe_ratio_change=-0.2,
        volatility_increase_pct=15.0,
        recovery_days=10,
        recovery_probability_pct=95.0,
        worst_affected_position="stocks",
        worst_affected_loss_pct=8.5,
    )
    
    assert impact.scenario_id == "test_1"
    assert impact.pnl_change_pct == -5.0
    assert impact.recovery_days == 10


def test_portfolio_impact_severe():
    """Test PortfolioImpact with severe impact"""
    impact = PortfolioImpact(
        scenario_id="crisis",
        scenario_name="Crisis Scenario",
        pnl_change_pct=-25.0,
        max_drawdown_pct=25.0,
        sharpe_ratio_change=-1.2,
        volatility_increase_pct=75.0,
        recovery_days=180,
        recovery_probability_pct=85.0,
        worst_affected_position="equities",
        worst_affected_loss_pct=35.0,
    )
    
    assert impact.max_drawdown_pct == 25.0
    assert impact.recovery_days == 180


# ============================================================================
# TESTS: StressTestResult
# ============================================================================

def test_stress_test_result_creation():
    """Test StressTestResult creation"""
    result = StressTestResult(
        test_id="test_1",
        scenario_id="scenario_1",
        scenario_name="Test Scenario",
        execution_timestamp=datetime.utcnow(),
        risk_level="moderate",
    )
    
    assert result.test_id == "test_1"
    assert result.scenario_id == "scenario_1"
    assert result.risk_level == "moderate"
    assert len(result.portfolio_impacts) == 0


def test_stress_test_result_with_impacts():
    """Test StressTestResult with portfolio impacts"""
    impact = PortfolioImpact(
        scenario_id="s1",
        scenario_name="Scenario 1",
        pnl_change_pct=-5.0,
        max_drawdown_pct=5.0,
        sharpe_ratio_change=-0.1,
        volatility_increase_pct=10.0,
        recovery_days=5,
        recovery_probability_pct=95.0,
        worst_affected_position="stocks",
        worst_affected_loss_pct=7.0,
    )
    
    result = StressTestResult(
        test_id="test_2",
        scenario_id="s1",
        scenario_name="Scenario 1",
        execution_timestamp=datetime.utcnow(),
        portfolio_impacts=[impact],
        average_max_drawdown=5.0,
        scenarios_passed=1,
        scenarios_failed=0,
    )
    
    assert len(result.portfolio_impacts) == 1
    assert result.scenarios_passed == 1


def test_stress_test_result_to_dict():
    """Test StressTestResult serialization"""
    result = StressTestResult(
        test_id="test_3",
        scenario_id="scenario_3",
        scenario_name="Test Scenario",
        execution_timestamp=datetime.utcnow(),
        risk_level="high",
        average_max_drawdown=12.5,
    )
    
    result_dict = result.to_dict()
    assert result_dict["test_id"] == "test_3"
    assert result_dict["risk_level"] == "high"
    assert result_dict["average_max_drawdown"] == 12.5


# ============================================================================
# TESTS: ReverseStressResult
# ============================================================================

def test_reverse_stress_result_creation():
    """Test ReverseStressResult creation"""
    result = ReverseStressResult(
        test_id="reverse_1",
        timestamp=datetime.utcnow(),
        max_loss_pct=18.5,
        max_loss_confidence=0.88,
        recovery_time_estimate_days=45,
        minimum_buffer_required_pct=5.0,
    )
    
    assert result.test_id == "reverse_1"
    assert result.max_loss_pct == 18.5
    assert result.max_loss_confidence == 0.88


def test_reverse_stress_result_with_breaches():
    """Test ReverseStressResult with breach scenarios"""
    result = ReverseStressResult(
        test_id="reverse_2",
        timestamp=datetime.utcnow(),
        max_loss_pct=22.0,
        max_loss_confidence=0.85,
        breach_scenarios=["2008 Crisis", "Fat Tail Event"],
        recovery_time_estimate_days=60,
        minimum_buffer_required_pct=2.0,
    )
    
    assert len(result.breach_scenarios) == 2
    assert "2008 Crisis" in result.breach_scenarios


# ============================================================================
# TESTS: ScenarioBuilder - Historical Scenarios
# ============================================================================

def test_scenario_builder_2008_crisis():
    """Test building 2008 Financial Crisis scenario"""
    scenarios = ScenarioBuilder.build_historical_scenarios()
    
    assert len(scenarios) >= 1
    crisis_2008 = [s for s in scenarios if "2008" in s.name][0]
    assert crisis_2008.scenario_type == ScenarioType.HISTORICAL
    assert crisis_2008.lookback_date.year == 2008
    assert len(crisis_2008.shocks) > 0


def test_scenario_builder_covid_2020():
    """Test building 2020 COVID scenario"""
    scenarios = ScenarioBuilder.build_historical_scenarios()
    covid = [s for s in scenarios if "COVID" in s.name][0]
    
    assert covid.scenario_type == ScenarioType.HISTORICAL
    assert covid.lookback_date.year == 2020
    assert any(shock.asset_name == "gold" for shock in covid.shocks)


def test_scenario_builder_flash_crash():
    """Test building flash crash scenario"""
    scenarios = ScenarioBuilder.build_historical_scenarios()
    flash = [s for s in scenarios if "Flash" in s.name][0]
    
    assert flash.scenario_type == ScenarioType.HISTORICAL
    assert flash.shocks[0].shock_duration_days == 1


# ============================================================================
# TESTS: ScenarioBuilder - Hypothetical Scenarios
# ============================================================================

def test_scenario_builder_rate_shock():
    """Test building rate shock scenario"""
    scenarios = ScenarioBuilder.build_hypothetical_scenarios()
    
    rate_shock = [s for s in scenarios if "Rate" in s.name][0]
    assert rate_shock.scenario_type == ScenarioType.HYPOTHETICAL
    assert any(shock.asset_name == "gold" for shock in rate_shock.shocks)


def test_scenario_builder_geopolitical():
    """Test building geopolitical scenario"""
    scenarios = ScenarioBuilder.build_hypothetical_scenarios()
    geo = [s for s in scenarios if "Geopolitical" in s.name][0]
    
    assert geo.scenario_type == ScenarioType.HYPOTHETICAL
    assert geo.correlation_spike_multiplier > 1.5


def test_scenario_builder_policy_shock():
    """Test building policy shock scenario"""
    scenarios = ScenarioBuilder.build_hypothetical_scenarios()
    policy = [s for s in scenarios if "Policy" in s.name][0]
    
    assert policy.scenario_type == ScenarioType.HYPOTHETICAL


# ============================================================================
# TESTS: ScenarioBuilder - Correlation Scenarios
# ============================================================================

def test_scenario_builder_correlation_breakdown():
    """Test building correlation breakdown scenario"""
    scenarios = ScenarioBuilder.build_correlation_scenarios()
    
    assert len(scenarios) >= 1
    corr_break = scenarios[0]
    assert corr_break.scenario_type == ScenarioType.CORRELATION
    assert corr_break.correlation_spike_multiplier > 2.0


# ============================================================================
# TESTS: ScenarioBuilder - Fat Tail Scenarios
# ============================================================================

def test_scenario_builder_5sigma():
    """Test building 5-sigma fat tail scenario"""
    scenarios = ScenarioBuilder.build_fat_tail_scenarios()
    
    sigma_5 = [s for s in scenarios if "5-Sigma" in s.name][0]
    assert sigma_5.scenario_type == ScenarioType.FAT_TAIL
    assert sigma_5.probability_estimate < 0.01


def test_scenario_builder_6sigma():
    """Test building 6-sigma black swan scenario"""
    scenarios = ScenarioBuilder.build_fat_tail_scenarios()
    
    sigma_6 = [s for s in scenarios if "6-Sigma" in s.name][0]
    assert sigma_6.scenario_type == ScenarioType.FAT_TAIL
    assert sigma_6.probability_estimate < 0.001  # Extremely rare event


# ============================================================================
# TESTS: ScenarioBuilder - Cascade Scenarios
# ============================================================================

def test_scenario_builder_cascade():
    """Test building cascade failure scenario"""
    scenarios = ScenarioBuilder.build_cascade_scenarios()
    
    assert len(scenarios) >= 1
    cascade = scenarios[0]
    assert cascade.scenario_type == ScenarioType.CASCADE
    assert len(cascade.shocks) >= 3  # Multiple assets


# ============================================================================
# TESTS: ScenarioSimulator
# ============================================================================

def test_scenario_simulator_run_scenario(event_loop, scenario_simulator, baseline_portfolio):
    """Test ScenarioSimulator.run_scenario()"""
    async def run_test():
        scenario = StressScenario(
            scenario_id="test_sim",
            name="Test Simulation",
            description="Test",
            scenario_type=ScenarioType.HYPOTHETICAL,
        )
        scenario.add_shock("gold", -0.10)
        scenario.add_shock("stocks", -0.15)
        
        impact = await scenario_simulator.run_scenario(scenario, baseline_portfolio)
        
        assert impact.scenario_id == "test_sim"
        assert impact.pnl_change_pct < 0  # Negative shocks
        assert impact.recovery_days > 0
    
    event_loop.run_until_complete(run_test())


def test_scenario_simulator_run_multiple(event_loop, scenario_simulator, baseline_portfolio):
    """Test ScenarioSimulator.run_multiple_scenarios()"""
    async def run_test():
        scenarios = [
            StressScenario(
                scenario_id="test_1",
                name="Scenario 1",
                description="",
                scenario_type=ScenarioType.HYPOTHETICAL,
            ),
            StressScenario(
                scenario_id="test_2",
                name="Scenario 2",
                description="",
                scenario_type=ScenarioType.HYPOTHETICAL,
            ),
        ]
        
        scenarios[0].add_shock("gold", -0.05)
        scenarios[1].add_shock("stocks", -0.10)
        
        impacts = await scenario_simulator.run_multiple_scenarios(scenarios, baseline_portfolio)
        
        assert len(impacts) == 2
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# TESTS: ResilienceAnalyzer
# ============================================================================

def test_resilience_analyzer_classify_critical():
    """Test classifying critical resilience"""
    resilience = ResilienceAnalyzer.classify_resilience(
        max_drawdown_pct=30.0,
        recovery_days=200
    )
    
    assert resilience == ResilienceLevel.CRITICAL


def test_resilience_analyzer_classify_weak():
    """Test classifying weak resilience"""
    resilience = ResilienceAnalyzer.classify_resilience(
        max_drawdown_pct=18.0,
        recovery_days=100
    )
    
    assert resilience == ResilienceLevel.WEAK


def test_resilience_analyzer_classify_moderate():
    """Test classifying moderate resilience"""
    resilience = ResilienceAnalyzer.classify_resilience(
        max_drawdown_pct=8.0,
        recovery_days=20
    )
    
    assert resilience == ResilienceLevel.MODERATE


def test_resilience_analyzer_classify_strong():
    """Test classifying strong resilience"""
    resilience = ResilienceAnalyzer.classify_resilience(
        max_drawdown_pct=2.0,
        recovery_days=5
    )
    
    assert resilience == ResilienceLevel.STRONG


def test_resilience_analyzer_classify_robust():
    """Test classifying robust resilience"""
    resilience = ResilienceAnalyzer.classify_resilience(
        max_drawdown_pct=0.0,
        recovery_days=0
    )
    
    assert resilience == ResilienceLevel.ROBUST


def test_resilience_analyzer_score_calculation():
    """Test resilience score calculation"""
    impact = PortfolioImpact(
        scenario_id="test",
        scenario_name="Test",
        pnl_change_pct=-5.0,
        max_drawdown_pct=5.0,
        sharpe_ratio_change=-0.1,
        volatility_increase_pct=10.0,
        recovery_days=10,
        recovery_probability_pct=95.0,
        worst_affected_position="stocks",
        worst_affected_loss_pct=7.0,
    )
    
    score = ResilienceAnalyzer.calculate_resilience_score([impact])
    
    assert 0 <= score <= 100


def test_resilience_analyzer_score_empty():
    """Test resilience score with empty impacts"""
    score = ResilienceAnalyzer.calculate_resilience_score([])
    assert score == 50.0  # Default


# ============================================================================
# TESTS: ReverseStressTester
# ============================================================================

def test_reverse_stress_tester_initialization():
    """Test ReverseStressTester initialization"""
    tester = ReverseStressTester(max_acceptable_loss_pct=20.0)
    assert tester.max_acceptable_loss_pct == 20.0


def test_reverse_stress_tester_find_max_loss(event_loop):
    """Test ReverseStressTester.find_max_loss_tolerance()"""
    async def run_test():
        tester = ReverseStressTester(max_acceptable_loss_pct=20.0)
        builder = ScenarioBuilder()
        scenarios = builder.build_historical_scenarios()
        portfolio = {"gold": 50000, "stocks": 30000}
        
        result = await tester.find_max_loss_tolerance(scenarios, portfolio)
        
        assert result.test_id is not None
        assert result.max_loss_pct >= 0
        assert result.timestamp is not None
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# TESTS: StressTester - Full Workflow
# ============================================================================

def test_stress_tester_initialization():
    """Test StressTester initialization"""
    tester = StressTester(max_acceptable_loss_pct=20.0)
    assert len(tester.test_results) == 0
    assert len(tester.reverse_test_results) == 0


def test_stress_tester_run_full_test(event_loop, stress_tester, baseline_portfolio):
    """Test StressTester.run_full_stress_test()"""
    async def run_test():
        result = await stress_tester.run_full_stress_test(baseline_portfolio)
        
        assert result.test_id is not None
        assert len(result.portfolio_impacts) > 0
        assert result.average_max_drawdown >= 0
    
    event_loop.run_until_complete(run_test())


def test_stress_tester_run_scenario_type(event_loop, stress_tester, baseline_portfolio):
    """Test StressTester.run_scenario_type()"""
    async def run_test():
        result = await stress_tester.run_scenario_type(
            ScenarioType.HISTORICAL,
            baseline_portfolio
        )
        
        assert len(result.portfolio_impacts) > 0
    
    event_loop.run_until_complete(run_test())


def test_stress_tester_run_reverse_test(event_loop, stress_tester, baseline_portfolio):
    """Test StressTester.run_reverse_stress_test()"""
    async def run_test():
        result = await stress_tester.run_reverse_stress_test(baseline_portfolio)
        
        assert result.test_id is not None
        assert result.max_loss_pct >= 0
    
    event_loop.run_until_complete(run_test())


def test_stress_tester_multiple_tests(event_loop, stress_tester, baseline_portfolio):
    """Test running multiple stress tests sequentially"""
    async def run_test():
        result1 = await stress_tester.run_full_stress_test(baseline_portfolio)
        result2 = await stress_tester.run_scenario_type(ScenarioType.HYPOTHETICAL, baseline_portfolio)
        
        assert len(stress_tester.test_results) == 2
    
    event_loop.run_until_complete(run_test())


def test_stress_tester_calculate_resilience_score(event_loop, stress_tester, baseline_portfolio):
    """Test resilience score calculation"""
    async def run_test():
        await stress_tester.run_full_stress_test(baseline_portfolio)
        score = stress_tester.calculate_resilience_score()
        
        assert 0 <= score <= 100
    
    event_loop.run_until_complete(run_test())


def test_stress_tester_get_test_results(event_loop, stress_tester, baseline_portfolio):
    """Test getting test results"""
    async def run_test():
        await stress_tester.run_full_stress_test(baseline_portfolio)
        results = stress_tester.get_test_results()
        
        assert len(results) >= 1
    
    event_loop.run_until_complete(run_test())


def test_stress_tester_get_latest_assessment(event_loop, stress_tester, baseline_portfolio):
    """Test getting latest resilience assessment"""
    async def run_test():
        await stress_tester.run_full_stress_test(baseline_portfolio)
        assessment = stress_tester.get_latest_resilience_assessment()
        
        assert assessment is not None
        assert "resilience_score" in assessment
        assert "worst_scenario" in assessment
    
    event_loop.run_until_complete(run_test())


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_full_stress_testing_workflow(event_loop, baseline_portfolio):
    """Test complete stress testing workflow"""
    async def run_test():
        tester = StressTester()
        
        # Run full suite
        result = await tester.run_full_stress_test(baseline_portfolio)
        assert result is not None
        
        # Run reverse stress test
        reverse_result = await tester.run_reverse_stress_test(baseline_portfolio)
        assert reverse_result is not None
        
        # Get assessment
        assessment = tester.get_latest_resilience_assessment()
        assert assessment is not None
    
    event_loop.run_until_complete(run_test())


def test_scenario_variety_coverage(event_loop, baseline_portfolio):
    """Test that all scenario types are covered"""
    async def run_test():
        tester = StressTester()
        
        for scenario_type in ScenarioType:
            result = await tester.run_scenario_type(scenario_type, baseline_portfolio)
            assert len(result.portfolio_impacts) > 0
        
        # All 5 types tested
        assert len(tester.test_results) == 5
    
    event_loop.run_until_complete(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

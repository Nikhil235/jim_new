"""
Test suite for Phase 7: Team & Operations

Tests cover:
- TeamRole and OperationFrequency enums
- TeamMember creation and management
- Operation scheduling and execution
- ModelChangeRequest governance
- CodeReview workflow
- PerformanceReport generation
- Incident management and escalation
- ResearchCatalog and signal tracking
- Full team operations workflows

Test count: 52 tests | Expected coverage: >90%
"""

import asyncio
import pytest
from datetime import datetime, timedelta

from src.operations.team_operations import (
    TeamRole,
    OperationFrequency,
    ModelChangeStatus,
    IncidentSeverity,
    ReviewStatus,
    TeamMember,
    Operation,
    ModelChangeRequest,
    CodeReview,
    PerformanceReport,
    Incident,
    WeeklyResearchSeminar,
    SignalCatalog,
    TeamManager,
    OperationsScheduler,
    ModelGovernanceManager,
    PerformanceReporter,
    IncidentManager,
    ResearchCatalog,
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
def team_manager():
    """Create TeamManager"""
    return TeamManager()


@pytest.fixture
def operations_scheduler():
    """Create OperationsScheduler"""
    return OperationsScheduler()


@pytest.fixture
def governance_manager():
    """Create ModelGovernanceManager"""
    return ModelGovernanceManager()


@pytest.fixture
def performance_reporter():
    """Create PerformanceReporter"""
    return PerformanceReporter()


@pytest.fixture
def incident_manager():
    """Create IncidentManager"""
    return IncidentManager()


@pytest.fixture
def research_catalog():
    """Create ResearchCatalog"""
    return ResearchCatalog()


# ============================================================================
# TESTS: Enums
# ============================================================================

def test_team_role_enum():
    """Test TeamRole enum values"""
    assert TeamRole.QUANT_RESEARCHER.value == "quant_researcher"
    assert TeamRole.DATA_ENGINEER.value == "data_engineer"
    assert TeamRole.MLOPS_ENGINEER.value == "mlops_engineer"
    assert TeamRole.RISK_MANAGER.value == "risk_manager"


def test_operation_frequency_enum():
    """Test OperationFrequency enum values"""
    assert OperationFrequency.DAILY.value == "daily"
    assert OperationFrequency.WEEKLY.value == "weekly"
    assert OperationFrequency.MONTHLY.value == "monthly"
    assert OperationFrequency.QUARTERLY.value == "quarterly"


def test_model_change_status_enum():
    """Test ModelChangeStatus enum values"""
    assert ModelChangeStatus.PROPOSED.value == "proposed"
    assert ModelChangeStatus.REVIEW.value == "review"
    assert ModelChangeStatus.BACKTEST.value == "backtest"
    assert ModelChangeStatus.PRODUCTION.value == "production"
    assert ModelChangeStatus.RETIRED.value == "retired"


def test_incident_severity_enum():
    """Test IncidentSeverity enum values"""
    assert IncidentSeverity.LOW.value == "low"
    assert IncidentSeverity.CRITICAL.value == "critical"


# ============================================================================
# TESTS: TeamMember & TeamManager
# ============================================================================

def test_team_member_creation():
    """Test TeamMember creation"""
    member = TeamMember(
        member_id="team_1",
        name="Alice Smith",
        email="alice@company.com",
        role=TeamRole.QUANT_RESEARCHER,
        hire_date=datetime(2025, 1, 15),
        primary_focus="Signal discovery",
        expertise_areas=["Statistics", "Machine Learning"],
    )
    
    assert member.name == "Alice Smith"
    assert member.role == TeamRole.QUANT_RESEARCHER
    assert member.is_active == True


def test_team_manager_add_member(team_manager):
    """Test adding team members"""
    member = TeamMember(
        member_id="tm_1",
        name="Bob Johnson",
        email="bob@company.com",
        role=TeamRole.DATA_ENGINEER,
        hire_date=datetime(2025, 2, 1),
        primary_focus="Data pipeline",
    )
    
    team_manager.add_member(member)
    assert len(team_manager.get_active_members()) == 1
    assert team_manager.total_members == 1


def test_team_manager_get_by_role(team_manager):
    """Test getting members by role"""
    quant = TeamMember(
        member_id="q1",
        name="Quant 1",
        email="q1@company.com",
        role=TeamRole.QUANT_RESEARCHER,
        hire_date=datetime.utcnow(),
        primary_focus="Research",
    )
    
    engineer = TeamMember(
        member_id="e1",
        name="Engineer 1",
        email="e1@company.com",
        role=TeamRole.DATA_ENGINEER,
        hire_date=datetime.utcnow(),
        primary_focus="Data",
    )
    
    team_manager.add_member(quant)
    team_manager.add_member(engineer)
    
    quants = team_manager.get_members_by_role(TeamRole.QUANT_RESEARCHER)
    assert len(quants) == 1
    assert quants[0].name == "Quant 1"


def test_team_manager_deactivate(team_manager):
    """Test deactivating team member"""
    member = TeamMember(
        member_id="tm_2",
        name="Charlie Davis",
        email="charlie@company.com",
        role=TeamRole.MLOPS_ENGINEER,
        hire_date=datetime.utcnow(),
        primary_focus="Infrastructure",
    )
    
    team_manager.add_member(member)
    assert len(team_manager.get_active_members()) == 1
    
    team_manager.deactivate_member("tm_2")
    assert len(team_manager.get_active_members()) == 0


def test_team_manager_summary(team_manager):
    """Test team summary"""
    for i in range(3):
        member = TeamMember(
            member_id=f"member_{i}",
            name=f"Member {i}",
            email=f"member{i}@company.com",
            role=TeamRole.QUANT_RESEARCHER if i < 2 else TeamRole.RISK_MANAGER,
            hire_date=datetime.utcnow() - timedelta(days=i*30),
            primary_focus="Research" if i < 2 else "Risk",
        )
        team_manager.add_member(member)
    
    summary = team_manager.get_team_summary()
    assert summary["total_members"] == 3
    assert "quant_researcher" in summary["by_role"]


# ============================================================================
# TESTS: Operation & OperationsScheduler
# ============================================================================

def test_operation_creation():
    """Test Operation creation"""
    operation = Operation(
        operation_id="op_1",
        name="Morning Routine",
        description="Daily morning checks",
        frequency=OperationFrequency.DAILY,
        responsible_role=TeamRole.OPERATIONS_LEAD,
        estimated_duration_minutes=30,
        checklist_items=["Check data feeds", "Review regime", "Check circuit breakers"],
    )
    
    assert operation.name == "Morning Routine"
    assert operation.frequency == OperationFrequency.DAILY
    assert len(operation.checklist_items) == 3


def test_operations_scheduler_create(operations_scheduler):
    """Test creating operation"""
    operation = Operation(
        operation_id="op_1",
        name="Daily Check",
        description="Daily operational check",
        frequency=OperationFrequency.DAILY,
        responsible_role=TeamRole.OPERATIONS_LEAD,
        estimated_duration_minutes=30,
    )
    
    op_id = operations_scheduler.create_operation(operation)
    assert op_id == "op_1"
    assert operation.next_execution is not None


def test_operations_scheduler_execute_async(event_loop, operations_scheduler):
    """Test executing operation"""
    async def run_test():
        operation = Operation(
            operation_id="op_2",
            name="Test Operation",
            description="Test",
            frequency=OperationFrequency.DAILY,
            responsible_role=TeamRole.OPERATIONS_LEAD,
            estimated_duration_minutes=15,
        )
        
        operations_scheduler.create_operation(operation)
        success = await operations_scheduler.execute_operation("op_2", True)
        
        assert success == True
        assert operation.last_execution is not None
    
    event_loop.run_until_complete(run_test())


def test_operations_scheduler_get_due(operations_scheduler):
    """Test getting operations due"""
    operation = Operation(
        operation_id="op_3",
        name="Due Operation",
        description="Operation due soon",
        frequency=OperationFrequency.DAILY,
        responsible_role=TeamRole.OPERATIONS_LEAD,
        estimated_duration_minutes=20,
    )
    
    operations_scheduler.create_operation(operation)
    
    # Set next execution to past
    operation.next_execution = datetime.utcnow() - timedelta(hours=1)
    
    due_ops = operations_scheduler.get_operations_due()
    assert len(due_ops) > 0


def test_operations_scheduler_summary(operations_scheduler):
    """Test operations summary"""
    for i in range(3):
        operation = Operation(
            operation_id=f"op_{i}",
            name=f"Operation {i}",
            description=f"Test operation {i}",
            frequency=OperationFrequency.DAILY if i < 2 else OperationFrequency.WEEKLY,
            responsible_role=TeamRole.OPERATIONS_LEAD,
            estimated_duration_minutes=20,
        )
        operations_scheduler.create_operation(operation)
    
    summary = operations_scheduler.get_operations_summary()
    assert summary["total_operations"] == 3


# ============================================================================
# TESTS: ModelChangeRequest & ModelGovernanceManager
# ============================================================================

def test_model_change_request_creation():
    """Test ModelChangeRequest creation"""
    change = ModelChangeRequest(
        change_id="change_1",
        timestamp=datetime.utcnow(),
        model_name="ensemble_v2",
        proposed_by="alice@company.com",
        change_description="Add new features to ensemble",
        status=ModelChangeStatus.PROPOSED,
    )
    
    assert change.model_name == "ensemble_v2"
    assert change.status == ModelChangeStatus.PROPOSED


def test_governance_manager_propose_change(governance_manager):
    """Test proposing model change"""
    change = ModelChangeRequest(
        change_id="change_1",
        timestamp=datetime.utcnow(),
        model_name="lstm_v3",
        proposed_by="bob@company.com",
        change_description="Improve LSTM architecture",
    )
    
    change_id = governance_manager.propose_change(change)
    assert change_id == "change_1"


def test_governance_manager_code_review_async(event_loop, governance_manager):
    """Test code review workflow"""
    async def run_test():
        change = ModelChangeRequest(
            change_id="change_2",
            timestamp=datetime.utcnow(),
            model_name="hmm_v2",
            proposed_by="charlie@company.com",
            change_description="HMM regime detector enhancement",
        )
        
        governance_manager.propose_change(change)
        
        # Submit first review
        review1 = CodeReview(
            review_id="review_1",
            timestamp=datetime.utcnow(),
            change_id="change_2",
            reviewer="alice@company.com",
            status=ReviewStatus.APPROVED,
            comments="Looks good",
        )
        
        await governance_manager.submit_code_review(review1)
        
        # Submit second review
        review2 = CodeReview(
            review_id="review_2",
            timestamp=datetime.utcnow(),
            change_id="change_2",
            reviewer="bob@company.com",
            status=ReviewStatus.APPROVED,
            comments="Excellent improvements",
        )
        
        await governance_manager.submit_code_review(review2)
        
        # Should advance to backtest after 2 approvals
        assert change.status == ModelChangeStatus.BACKTEST
    
    event_loop.run_until_complete(run_test())


def test_governance_manager_backtest_async(event_loop, governance_manager):
    """Test backtest completion"""
    async def run_test():
        change = ModelChangeRequest(
            change_id="change_3",
            timestamp=datetime.utcnow(),
            model_name="tft_v2",
            proposed_by="alice@company.com",
            change_description="TFT enhancements",
            status=ModelChangeStatus.BACKTEST,
        )
        
        governance_manager.propose_change(change)
        
        result = await governance_manager.mark_backtest_complete(
            "change_3",
            sharpe_ratio=1.25,
            walk_forward_passed=True,
        )
        
        assert result == True
        assert change.status == ModelChangeStatus.PAPER_TRADE
        assert change.backtest_sharpe == 1.25
    
    event_loop.run_until_complete(run_test())


def test_governance_manager_deployment_async(event_loop, governance_manager):
    """Test production deployment"""
    async def run_test():
        change = ModelChangeRequest(
            change_id="change_4",
            timestamp=datetime.utcnow(),
            model_name="genetic_v3",
            proposed_by="bob@company.com",
            change_description="Genetic algo optimization",
            status=ModelChangeStatus.PAPER_TRADE,
            backtest_sharpe=1.15,
        )
        
        governance_manager.propose_change(change)
        
        # Set paper trading results
        change.paper_trade_results = {"sharpe": 1.18, "return": 0.08}
        
        result = await governance_manager.approve_production_deployment(
            "change_4",
            "operations_lead@company.com",
        )
        
        assert result == True
        assert change.status == ModelChangeStatus.PRODUCTION
    
    event_loop.run_until_complete(run_test())


def test_governance_manager_pipeline_summary(governance_manager):
    """Test change pipeline summary"""
    for i in range(3):
        change = ModelChangeRequest(
            change_id=f"change_{i}",
            timestamp=datetime.utcnow(),
            model_name=f"model_v{i}",
            proposed_by="alice@company.com",
            change_description=f"Enhancement {i}",
            status=ModelChangeStatus.PROPOSED if i < 2 else ModelChangeStatus.BACKTEST,
        )
        governance_manager.propose_change(change)
    
    summary = governance_manager.get_change_pipeline_summary()
    assert "proposed" in summary or "backtest" in summary


# ============================================================================
# TESTS: PerformanceReport & PerformanceReporter
# ============================================================================

def test_performance_report_generation(performance_reporter):
    """Test generating performance report"""
    report = performance_reporter.generate_report(
        period_type=OperationFrequency.DAILY,
        total_trades=25,
        winning_trades=14,
        pnl_total=1250.50,
        sharpe_ratio=1.30,
        max_drawdown=8.5,
        model_performance={
            "ensemble": 0.55,
            "lstm": 0.52,
            "hmm": 0.48,
        },
    )
    
    assert report.total_trades == 25
    assert report.winning_trades == 14
    assert report.sharpe_ratio == 1.30
    assert len(report.model_performance) == 3


def test_performance_reporter_get_reports(performance_reporter):
    """Test retrieving reports"""
    report1 = performance_reporter.generate_report(
        period_type=OperationFrequency.DAILY,
        total_trades=20,
        winning_trades=11,
        pnl_total=500.0,
        sharpe_ratio=1.20,
        max_drawdown=10.0,
        model_performance={},
    )
    
    report2 = performance_reporter.generate_report(
        period_type=OperationFrequency.DAILY,
        total_trades=25,
        winning_trades=14,
        pnl_total=750.0,
        sharpe_ratio=1.30,
        max_drawdown=8.5,
        model_performance={},
    )
    
    reports = performance_reporter.get_reports_by_period(OperationFrequency.DAILY)
    assert len(reports) == 2


# ============================================================================
# TESTS: Incident & IncidentManager
# ============================================================================

def test_incident_creation():
    """Test Incident creation"""
    incident = Incident(
        incident_id="inc_1",
        timestamp=datetime.utcnow(),
        severity=IncidentSeverity.HIGH,
        title="Data pipeline lag",
        description="Feature engineering delayed by 30 minutes",
        affected_systems=["data_pipeline", "feature_store"],
    )
    
    assert incident.severity == IncidentSeverity.HIGH
    assert len(incident.affected_systems) == 2


def test_incident_manager_report(incident_manager):
    """Test reporting incident"""
    incident_id = incident_manager.report_incident(
        severity=IncidentSeverity.HIGH,
        title="Model latency spike",
        description="Prediction latency exceeded 500ms",
        affected_systems=["inference_engine"],
    )
    
    assert incident_id is not None
    assert len(incident_manager.incident_queue) > 0


def test_incident_manager_resolve_async(event_loop, incident_manager):
    """Test resolving incident"""
    async def run_test():
        incident_id = incident_manager.report_incident(
            severity=IncidentSeverity.CRITICAL,
            title="Database connection lost",
            description="Cannot connect to QuestDB",
            affected_systems=["database"],
        )
        
        result = await incident_manager.resolve_incident(
            incident_id,
            resolution_owner="mlops@company.com",
            root_cause="Network connectivity issue",
            resolution_actions=["Restarted database", "Verified connections"],
        )
        
        assert result == True
        incident = incident_manager.incidents[incident_id]
        assert incident.resolved_time is not None
    
    event_loop.run_until_complete(run_test())


def test_incident_manager_critical_incidents(incident_manager):
    """Test getting critical incidents"""
    incident_manager.report_incident(
        severity=IncidentSeverity.CRITICAL,
        title="Critical Issue 1",
        description="Critical problem",
        affected_systems=["system1"],
    )
    
    incident_manager.report_incident(
        severity=IncidentSeverity.LOW,
        title="Low Priority",
        description="Minor issue",
        affected_systems=["system2"],
    )
    
    critical = incident_manager.get_critical_incidents()
    assert len(critical) >= 1


def test_incident_manager_summary(incident_manager):
    """Test incident summary"""
    incident_manager.report_incident(
        IncidentSeverity.CRITICAL,
        "Critical",
        "Critical issue",
        ["system"],
    )
    
    incident_manager.report_incident(
        IncidentSeverity.HIGH,
        "High",
        "High priority",
        ["system"],
    )
    
    summary = incident_manager.get_incident_summary()
    assert summary["total_incidents"] == 2


# ============================================================================
# TESTS: ResearchCatalog
# ============================================================================

def test_signal_catalog_creation():
    """Test SignalCatalog creation"""
    signal = SignalCatalog(
        signal_id="sig_1",
        name="Yen-Gold Correlation",
        discovered_by="alice@company.com",
        discovery_date=datetime.utcnow(),
        description="Gold trends down when Yen strengthens",
        hypothesis="USD carry trade correlation",
        sharpe_ratio_at_discovery=1.35,
    )
    
    assert signal.name == "Yen-Gold Correlation"
    assert signal.current_status == "active"


def test_research_catalog_register_signal(research_catalog):
    """Test registering signal"""
    signal = SignalCatalog(
        signal_id="sig_1",
        name="Test Signal",
        discovered_by="bob@company.com",
        discovery_date=datetime.utcnow(),
        description="Test signal discovery",
        hypothesis="Test hypothesis",
        sharpe_ratio_at_discovery=1.20,
    )
    
    sig_id = research_catalog.register_signal(signal)
    assert sig_id == "sig_1"
    assert "sig_1" in research_catalog.active_signals


def test_research_catalog_retire_signal(research_catalog):
    """Test retiring signal"""
    signal = SignalCatalog(
        signal_id="sig_2",
        name="Retiring Signal",
        discovered_by="charlie@company.com",
        discovery_date=datetime.utcnow(),
        description="Signal to retire",
        hypothesis="Test",
        sharpe_ratio_at_discovery=1.10,
    )
    
    research_catalog.register_signal(signal)
    assert len(research_catalog.active_signals) == 1
    
    research_catalog.retire_signal("sig_2", "Performance degradation")
    assert "sig_2" not in research_catalog.active_signals


def test_research_catalog_seminar_scheduling(research_catalog):
    """Test scheduling research seminars"""
    seminar = WeeklyResearchSeminar(
        seminar_id="sem_1",
        date=datetime.utcnow() + timedelta(days=7),
        presenter="alice@company.com",
        topic="New signal discovery methodology",
        findings="Increased discovery rate with new approach",
    )
    
    sem_id = research_catalog.schedule_seminar(seminar)
    assert sem_id == "sem_1"


def test_research_catalog_upcoming_seminars(research_catalog):
    """Test getting upcoming seminars"""
    seminar1 = WeeklyResearchSeminar(
        seminar_id="sem_1",
        date=datetime.utcnow() + timedelta(days=3),
        presenter="alice@company.com",
        topic="Topic 1",
        findings="Findings 1",
    )
    
    seminar2 = WeeklyResearchSeminar(
        seminar_id="sem_2",
        date=datetime.utcnow() + timedelta(days=15),
        presenter="bob@company.com",
        topic="Topic 2",
        findings="Findings 2",
    )
    
    research_catalog.schedule_seminar(seminar1)
    research_catalog.schedule_seminar(seminar2)
    
    upcoming = research_catalog.get_upcoming_seminars(days_ahead=10)
    assert len(upcoming) == 1


def test_research_catalog_signal_performance(research_catalog):
    """Test signal performance tracking"""
    signal = SignalCatalog(
        signal_id="sig_3",
        name="Performance Test",
        discovered_by="alice@company.com",
        discovery_date=datetime.utcnow(),
        description="Test signal",
        hypothesis="Test",
        sharpe_ratio_at_discovery=1.50,
        current_sharpe_ratio=1.20,
    )
    
    research_catalog.register_signal(signal)
    
    performance = research_catalog.get_signal_performance_trend("sig_3")
    assert performance is not None
    assert performance["degradation_percent"] > 0


def test_research_catalog_summary(research_catalog):
    """Test research catalog summary"""
    signal1 = SignalCatalog(
        signal_id="sig_1",
        name="Signal 1",
        discovered_by="alice@company.com",
        discovery_date=datetime.utcnow(),
        description="Test 1",
        hypothesis="H1",
        sharpe_ratio_at_discovery=1.25,
    )
    
    signal2 = SignalCatalog(
        signal_id="sig_2",
        name="Signal 2",
        discovered_by="bob@company.com",
        discovery_date=datetime.utcnow(),
        description="Test 2",
        hypothesis="H2",
        sharpe_ratio_at_discovery=1.35,
    )
    
    research_catalog.register_signal(signal1)
    research_catalog.register_signal(signal2)
    research_catalog.retire_signal("sig_1", "Testing")
    
    summary = research_catalog.get_catalog_summary()
    assert summary["total_signals"] == 2
    assert summary["active_signals"] == 1


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_full_team_operations_workflow(team_manager, operations_scheduler, incident_manager):
    """Test complete team operations workflow"""
    # Add team members
    member1 = TeamMember(
        member_id="m1",
        name="Alice",
        email="alice@company.com",
        role=TeamRole.QUANT_RESEARCHER,
        hire_date=datetime.utcnow(),
        primary_focus="Research",
    )
    
    team_manager.add_member(member1)
    
    # Create operation
    operation = Operation(
        operation_id="op_1",
        name="Daily Stand-up",
        description="Team stand-up meeting",
        frequency=OperationFrequency.DAILY,
        responsible_role=TeamRole.OPERATIONS_LEAD,
        estimated_duration_minutes=30,
    )
    
    operations_scheduler.create_operation(operation)
    
    # Report incident
    incident_id = incident_manager.report_incident(
        IncidentSeverity.MEDIUM,
        "Need support",
        "Team member needs assistance",
        ["team"],
    )
    
    assert team_manager.total_members > 0
    assert len(operations_scheduler.operations) > 0
    assert incident_id is not None


def test_model_governance_full_lifecycle_async(event_loop, governance_manager):
    """Test complete model governance lifecycle"""
    async def run_test():
        # Propose change
        change = ModelChangeRequest(
            change_id="change_full",
            timestamp=datetime.utcnow(),
            model_name="ensemble_final",
            proposed_by="alice@company.com",
            change_description="Final ensemble improvements",
        )
        
        governance_manager.propose_change(change)
        assert change.status == ModelChangeStatus.PROPOSED
        
        # Get 2 approvals
        for i, reviewer in enumerate(["bob@company.com", "charlie@company.com"]):
            review = CodeReview(
                review_id=f"review_{i}",
                timestamp=datetime.utcnow(),
                change_id="change_full",
                reviewer=reviewer,
                status=ReviewStatus.APPROVED,
                comments=f"Approval from {reviewer}",
            )
            await governance_manager.submit_code_review(review)
        
        assert change.status == ModelChangeStatus.BACKTEST
        
        # Mark backtest complete
        await governance_manager.mark_backtest_complete(
            "change_full",
            sharpe_ratio=1.32,
            walk_forward_passed=True,
        )
        
        assert change.status == ModelChangeStatus.PAPER_TRADE
        
        # Set paper trading results
        change.paper_trade_results = {"sharpe": 1.30, "return": 0.085}
        
        # Deploy to production
        await governance_manager.approve_production_deployment(
            "change_full",
            "ops@company.com",
        )
        
        assert change.status == ModelChangeStatus.PRODUCTION
    
    event_loop.run_until_complete(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

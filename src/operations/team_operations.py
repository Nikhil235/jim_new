"""
Phase 7: Team & Operations Management

Comprehensive team operations framework including:
- Team structure and roles management
- Daily/weekly/monthly operations scheduling
- Model governance and change management
- Performance tracking and reporting
- Code review and collaboration workflows
- Incident management and escalation

Production file: src/operations/team_operations.py
~900 lines of code with async support
"""

import asyncio
import logging
import json
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict
import uuid


logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class TeamRole(Enum):
    """Team member roles"""
    QUANT_RESEARCHER = "quant_researcher"
    DATA_ENGINEER = "data_engineer"
    MLOPS_ENGINEER = "mlops_engineer"
    RISK_MANAGER = "risk_manager"
    EXECUTION_ENGINEER = "execution_engineer"
    OPERATIONS_LEAD = "operations_lead"


class OperationFrequency(Enum):
    """Operation scheduling frequency"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class ModelChangeStatus(Enum):
    """Status of model governance change request"""
    PROPOSED = "proposed"
    REVIEW = "review"
    BACKTEST = "backtest"
    PAPER_TRADE = "paper_trade"
    STAGING = "staging"
    PRODUCTION = "production"
    RETIRED = "retired"
    REJECTED = "rejected"


class IncidentSeverity(Enum):
    """Incident severity classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewStatus(Enum):
    """Code review status"""
    PENDING = "pending"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class TeamMember:
    """Team member profile"""
    member_id: str
    name: str
    email: str
    role: TeamRole
    hire_date: datetime
    primary_focus: str
    expertise_areas: List[str] = field(default_factory=list)
    is_active: bool = True
    slack_handle: Optional[str] = None


@dataclass
class Operation:
    """Scheduled operation"""
    operation_id: str
    name: str
    description: str
    frequency: OperationFrequency
    responsible_role: TeamRole
    estimated_duration_minutes: int
    checklist_items: List[str] = field(default_factory=list)
    last_execution: Optional[datetime] = None
    next_execution: Optional[datetime] = None
    success_rate_percent: float = 0.0


@dataclass
class ModelChangeRequest:
    """Model governance change request"""
    change_id: str
    timestamp: datetime
    model_name: str
    proposed_by: str
    change_description: str
    status: ModelChangeStatus = ModelChangeStatus.PROPOSED
    reviewers_approved: Set[str] = field(default_factory=set)
    reviewers_requested: Set[str] = field(default_factory=set)
    backtest_sharpe: Optional[float] = None
    walk_forward_validation_passed: bool = False
    paper_trade_duration_days: int = 7
    paper_trade_results: Optional[Dict[str, float]] = None
    production_deployment_date: Optional[datetime] = None
    retirement_date: Optional[datetime] = None
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "change_id": self.change_id,
            "timestamp": self.timestamp.isoformat(),
            "model_name": self.model_name,
            "proposed_by": self.proposed_by,
            "status": self.status.value,
            "reviewers_approved": len(self.reviewers_approved),
            "backtest_sharpe": self.backtest_sharpe,
            "paper_trade_duration_days": self.paper_trade_duration_days,
        }


@dataclass
class CodeReview:
    """Code review record"""
    review_id: str
    timestamp: datetime
    change_id: str
    reviewer: str
    status: ReviewStatus
    comments: str
    files_reviewed: List[str] = field(default_factory=list)
    lines_changed: int = 0
    approval_score: float = 0.0  # 0-1


@dataclass
class PerformanceReport:
    """Daily/Weekly/Monthly performance report"""
    report_id: str
    period_start: datetime
    period_end: datetime
    period_type: OperationFrequency
    total_trades: int = 0
    winning_trades: int = 0
    pnl_total: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    model_performance: Dict[str, float] = field(default_factory=dict)
    alerts_triggered: int = 0
    incidents_reported: int = 0
    key_insights: List[str] = field(default_factory=list)


@dataclass
class Incident:
    """Incident record"""
    incident_id: str
    timestamp: datetime
    severity: IncidentSeverity
    title: str
    description: str
    affected_systems: List[str] = field(default_factory=list)
    root_cause: Optional[str] = None
    resolution_actions: List[str] = field(default_factory=list)
    resolved_time: Optional[datetime] = None
    resolution_owner: Optional[str] = None
    postmortem_link: Optional[str] = None


@dataclass
class WeeklyResearchSeminar:
    """Weekly research seminar record"""
    seminar_id: str
    date: datetime
    presenter: str
    topic: str
    findings: str
    test_results: Dict[str, float] = field(default_factory=dict)
    peer_feedback: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    attendees: List[str] = field(default_factory=list)


@dataclass
class SignalCatalog:
    """Catalog of all discovered signals"""
    signal_id: str
    name: str
    discovered_by: str
    discovery_date: datetime
    description: str
    hypothesis: str
    backtest_results: Dict[str, float] = field(default_factory=dict)
    current_status: str = "active"  # active, retired, testing
    retirement_reason: Optional[str] = None
    sharpe_ratio_at_discovery: float = 0.0
    current_sharpe_ratio: float = 0.0
    performance_degradation_percent: float = 0.0


# ============================================================================
# TEAM MANAGEMENT
# ============================================================================

class TeamManager:
    """Manages team members and organization"""
    
    def __init__(self):
        self.members: Dict[str, TeamMember] = {}
        self.total_members = 0
    
    def add_member(self, member: TeamMember) -> None:
        """Add team member"""
        self.members[member.member_id] = member
        self.total_members += 1
        logger.info(f"Added team member: {member.name} ({member.role.value})")
    
    def get_members_by_role(self, role: TeamRole) -> List[TeamMember]:
        """Get all members with specific role"""
        return [m for m in self.members.values() if m.role == role and m.is_active]
    
    def get_member(self, member_id: str) -> Optional[TeamMember]:
        """Get member by ID"""
        return self.members.get(member_id)
    
    def get_active_members(self) -> List[TeamMember]:
        """Get all active members"""
        return [m for m in self.members.values() if m.is_active]
    
    def deactivate_member(self, member_id: str) -> bool:
        """Deactivate team member"""
        if member_id in self.members:
            self.members[member_id].is_active = False
            return True
        return False
    
    def get_team_summary(self) -> Dict[str, Any]:
        """Get team composition summary"""
        role_counts = defaultdict(int)
        for member in self.get_active_members():
            role_counts[member.role.value] += 1
        
        return {
            "total_members": len(self.get_active_members()),
            "by_role": dict(role_counts),
            "average_tenure_days": self._calculate_avg_tenure(),
        }
    
    def _calculate_avg_tenure(self) -> float:
        """Calculate average tenure in days"""
        active_members = self.get_active_members()
        if not active_members:
            return 0.0
        
        total_days = sum(
            (datetime.utcnow() - m.hire_date).days
            for m in active_members
        )
        return total_days / len(active_members)


# ============================================================================
# OPERATIONS MANAGEMENT
# ============================================================================

class OperationsScheduler:
    """Manages daily/weekly/monthly operations"""
    
    def __init__(self):
        self.operations: Dict[str, Operation] = {}
        self.execution_history: List[Tuple[str, datetime, bool]] = []
    
    def create_operation(self, operation: Operation) -> str:
        """Create new operation"""
        self.operations[operation.operation_id] = operation
        self._schedule_next_execution(operation)
        return operation.operation_id
    
    def _schedule_next_execution(self, operation: Operation) -> None:
        """Schedule next execution time"""
        now = datetime.utcnow()
        
        if operation.frequency == OperationFrequency.DAILY:
            operation.next_execution = now + timedelta(days=1)
        elif operation.frequency == OperationFrequency.WEEKLY:
            operation.next_execution = now + timedelta(weeks=1)
        elif operation.frequency == OperationFrequency.MONTHLY:
            operation.next_execution = now + timedelta(days=30)
        elif operation.frequency == OperationFrequency.QUARTERLY:
            operation.next_execution = now + timedelta(days=90)
    
    async def execute_operation(self, operation_id: str, success: bool) -> bool:
        """Record operation execution"""
        if operation_id not in self.operations:
            return False
        
        operation = self.operations[operation_id]
        operation.last_execution = datetime.utcnow()
        
        # Update success rate
        self.execution_history.append((operation_id, datetime.utcnow(), success))
        
        # Calculate success rate from history
        recent_executions = [
            h for h in self.execution_history
            if h[0] == operation_id and (datetime.utcnow() - h[1]).days <= 30
        ]
        if recent_executions:
            successes = sum(1 for h in recent_executions if h[2])
            operation.success_rate_percent = (successes / len(recent_executions)) * 100
        
        # Schedule next execution
        self._schedule_next_execution(operation)
        return True
    
    def get_operations_due(self) -> List[Operation]:
        """Get operations due for execution"""
        now = datetime.utcnow()
        due = []
        
        for operation in self.operations.values():
            if operation.next_execution and operation.next_execution <= now:
                due.append(operation)
        
        return sorted(due, key=lambda x: x.next_execution)
    
    def get_operations_summary(self) -> Dict[str, Any]:
        """Get operations summary"""
        by_frequency = defaultdict(int)
        by_role = defaultdict(list)
        
        for op in self.operations.values():
            by_frequency[op.frequency.value] += 1
            by_role[op.responsible_role.value].append(op.name)
        
        return {
            "total_operations": len(self.operations),
            "by_frequency": dict(by_frequency),
            "by_role": dict(by_role),
            "average_success_rate": self._calculate_avg_success_rate(),
        }
    
    def _calculate_avg_success_rate(self) -> float:
        """Calculate average success rate"""
        if not self.execution_history:
            return 0.0
        
        successes = sum(1 for h in self.execution_history if h[2])
        return (successes / len(self.execution_history)) * 100


# ============================================================================
# MODEL GOVERNANCE
# ============================================================================

class ModelGovernanceManager:
    """Manages model change requests and governance"""
    
    def __init__(self):
        self.change_requests: Dict[str, ModelChangeRequest] = {}
        self.code_reviews: Dict[str, List[CodeReview]] = defaultdict(list)
        self.approved_changes: Set[str] = set()
        self.rejected_changes: Set[str] = set()
    
    def propose_change(self, change: ModelChangeRequest) -> str:
        """Propose model change"""
        self.change_requests[change.change_id] = change
        logger.info(f"Model change proposed: {change.model_name} by {change.proposed_by}")
        return change.change_id
    
    async def submit_code_review(self, review: CodeReview) -> bool:
        """Submit code review"""
        change_id = review.change_id
        if change_id not in self.change_requests:
            return False
        
        self.code_reviews[change_id].append(review)
        change = self.change_requests[change_id]
        
        if review.status == ReviewStatus.APPROVED:
            change.reviewers_approved.add(review.reviewer)
            
            # Auto-advance to next stage if min 2 approvals
            if len(change.reviewers_approved) >= 2:
                change.status = ModelChangeStatus.BACKTEST
        
        elif review.status == ReviewStatus.CHANGES_REQUESTED:
            change.status = ModelChangeStatus.REVIEW
        
        return True
    
    async def mark_backtest_complete(
        self,
        change_id: str,
        sharpe_ratio: float,
        walk_forward_passed: bool,
    ) -> bool:
        """Mark backtest as complete"""
        if change_id not in self.change_requests:
            return False
        
        change = self.change_requests[change_id]
        change.backtest_sharpe = sharpe_ratio
        change.walk_forward_validation_passed = walk_forward_passed
        
        if walk_forward_passed:
            change.status = ModelChangeStatus.PAPER_TRADE
            logger.info(f"Model {change.model_name} advanced to paper trading")
        else:
            change.status = ModelChangeStatus.REJECTED
            self.rejected_changes.add(change_id)
            logger.warning(f"Model {change.model_name} validation failed")
        
        return True
    
    async def approve_production_deployment(
        self,
        change_id: str,
        deployment_owner: str,
    ) -> bool:
        """Approve production deployment"""
        if change_id not in self.change_requests:
            return False
        
        change = self.change_requests[change_id]
        
        # Verify paper trading passed
        if not change.paper_trade_results:
            logger.warning("Paper trade results not available")
            return False
        
        # Check if results within 20% of backtest
        if change.backtest_sharpe:
            deviation = abs(
                (change.paper_trade_results.get("sharpe", 0) - change.backtest_sharpe) /
                change.backtest_sharpe
            )
            if deviation > 0.20:
                logger.warning(f"Paper trade results deviate >20% from backtest")
                return False
        
        change.status = ModelChangeStatus.PRODUCTION
        change.production_deployment_date = datetime.utcnow()
        self.approved_changes.add(change_id)
        logger.info(f"Model {change.model_name} deployed to production")
        
        return True
    
    def get_change_pipeline_summary(self) -> Dict[str, int]:
        """Get count of changes at each stage"""
        summary = defaultdict(int)
        
        for change in self.change_requests.values():
            summary[change.status.value] += 1
        
        return dict(summary)


# ============================================================================
# PERFORMANCE REPORTING
# ============================================================================

class PerformanceReporter:
    """Generates performance reports"""
    
    def __init__(self):
        self.reports: Dict[str, PerformanceReport] = {}
    
    def generate_report(
        self,
        period_type: OperationFrequency,
        total_trades: int,
        winning_trades: int,
        pnl_total: float,
        sharpe_ratio: float,
        max_drawdown: float,
        model_performance: Dict[str, float],
    ) -> PerformanceReport:
        """Generate performance report"""
        now = datetime.utcnow()
        
        if period_type == OperationFrequency.DAILY:
            period_start = now - timedelta(days=1)
        elif period_type == OperationFrequency.WEEKLY:
            period_start = now - timedelta(weeks=1)
        elif period_type == OperationFrequency.MONTHLY:
            period_start = now - timedelta(days=30)
        else:
            period_start = now - timedelta(days=90)
        
        report = PerformanceReport(
            report_id=str(uuid.uuid4()),
            period_start=period_start,
            period_end=now,
            period_type=period_type,
            total_trades=total_trades,
            winning_trades=winning_trades,
            pnl_total=pnl_total,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            model_performance=model_performance,
        )
        
        self.reports[report.report_id] = report
        return report
    
    def get_report(self, report_id: str) -> Optional[PerformanceReport]:
        """Get report by ID"""
        return self.reports.get(report_id)
    
    def get_reports_by_period(
        self,
        period_type: OperationFrequency,
        limit: int = 10,
    ) -> List[PerformanceReport]:
        """Get recent reports by period type"""
        reports = [
            r for r in self.reports.values()
            if r.period_type == period_type
        ]
        return sorted(
            reports,
            key=lambda x: x.period_end,
            reverse=True
        )[:limit]


# ============================================================================
# INCIDENT MANAGEMENT
# ============================================================================

class IncidentManager:
    """Manages incidents and escalation"""
    
    def __init__(self):
        self.incidents: Dict[str, Incident] = {}
        self.incident_queue: List[Incident] = []
    
    def report_incident(
        self,
        severity: IncidentSeverity,
        title: str,
        description: str,
        affected_systems: List[str],
    ) -> str:
        """Report new incident"""
        incident = Incident(
            incident_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            severity=severity,
            title=title,
            description=description,
            affected_systems=affected_systems,
        )
        
        self.incidents[incident.incident_id] = incident
        
        # Add to queue for processing
        if severity in [IncidentSeverity.CRITICAL, IncidentSeverity.HIGH]:
            self.incident_queue.insert(0, incident)  # Priority queue
        else:
            self.incident_queue.append(incident)
        
        logger.warning(f"Incident reported: {title} (Severity: {severity.value})")
        return incident.incident_id
    
    async def resolve_incident(
        self,
        incident_id: str,
        resolution_owner: str,
        root_cause: str,
        resolution_actions: List[str],
    ) -> bool:
        """Resolve incident"""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        incident.resolved_time = datetime.utcnow()
        incident.resolution_owner = resolution_owner
        incident.root_cause = root_cause
        incident.resolution_actions = resolution_actions
        
        # Remove from queue
        self.incident_queue = [
            i for i in self.incident_queue
            if i.incident_id != incident_id
        ]
        
        logger.info(f"Incident resolved: {incident.title}")
        return True
    
    def get_critical_incidents(self) -> List[Incident]:
        """Get unresolved critical incidents"""
        return [
            i for i in self.incidents.values()
            if i.severity == IncidentSeverity.CRITICAL and i.resolved_time is None
        ]
    
    def get_incident_summary(self) -> Dict[str, Any]:
        """Get incident summary"""
        unresolved = [i for i in self.incidents.values() if i.resolved_time is None]
        by_severity = defaultdict(int)
        
        for incident in unresolved:
            by_severity[incident.severity.value] += 1
        
        return {
            "total_incidents": len(self.incidents),
            "unresolved": len(unresolved),
            "by_severity": dict(by_severity),
            "pending_queue_size": len(self.incident_queue),
        }


# ============================================================================
# RESEARCH & KNOWLEDGE
# ============================================================================

class ResearchCatalog:
    """Manages research seminars and signal catalog"""
    
    def __init__(self):
        self.seminars: Dict[str, WeeklyResearchSeminar] = {}
        self.signals: Dict[str, SignalCatalog] = {}
        self.active_signals: Set[str] = set()
    
    def schedule_seminar(self, seminar: WeeklyResearchSeminar) -> str:
        """Schedule research seminar"""
        self.seminars[seminar.seminar_id] = seminar
        return seminar.seminar_id
    
    def get_upcoming_seminars(self, days_ahead: int = 7) -> List[WeeklyResearchSeminar]:
        """Get upcoming seminars"""
        now = datetime.utcnow()
        cutoff = now + timedelta(days=days_ahead)
        
        return [
            s for s in self.seminars.values()
            if now <= s.date <= cutoff
        ]
    
    def register_signal(self, signal: SignalCatalog) -> str:
        """Register new signal in catalog"""
        self.signals[signal.signal_id] = signal
        self.active_signals.add(signal.signal_id)
        return signal.signal_id
    
    def retire_signal(
        self,
        signal_id: str,
        reason: str,
    ) -> bool:
        """Retire signal"""
        if signal_id not in self.signals:
            return False
        
        signal = self.signals[signal_id]
        signal.current_status = "retired"
        signal.retirement_reason = reason
        self.active_signals.discard(signal_id)
        
        return True
    
    def get_signal_performance_trend(self, signal_id: str) -> Optional[Dict[str, float]]:
        """Get signal performance degradation trend"""
        if signal_id not in self.signals:
            return None
        
        signal = self.signals[signal_id]
        
        if signal.sharpe_ratio_at_discovery == 0:
            return None
        
        degradation = (
            (signal.sharpe_ratio_at_discovery - signal.current_sharpe_ratio) /
            signal.sharpe_ratio_at_discovery * 100
        )
        
        return {
            "discovery_sharpe": signal.sharpe_ratio_at_discovery,
            "current_sharpe": signal.current_sharpe_ratio,
            "degradation_percent": degradation,
            "status": "needs_investigation" if degradation > 20 else "stable",
        }
    
    def get_catalog_summary(self) -> Dict[str, Any]:
        """Get signal catalog summary"""
        return {
            "total_signals": len(self.signals),
            "active_signals": len(self.active_signals),
            "retired_signals": len(self.signals) - len(self.active_signals),
            "total_seminars": len(self.seminars),
            "average_discovery_sharpe": self._calculate_avg_discovery_sharpe(),
        }
    
    def _calculate_avg_discovery_sharpe(self) -> float:
        """Calculate average discovery Sharpe ratio"""
        if not self.signals:
            return 0.0
        
        total = sum(s.sharpe_ratio_at_discovery for s in self.signals.values())
        return total / len(self.signals)


if __name__ == "__main__":
    print("Phase 7: Team & Operations Management Framework Loaded")

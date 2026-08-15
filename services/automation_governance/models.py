from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
def now(): return datetime.now(timezone.utc).isoformat()
class ActionType: NOTIFY="NOTIFY"; CREATE_TICKET="CREATE_TICKET"; ISOLATE_SIMULATION="ISOLATE_SIMULATION"; BLOCK_SIMULATION="BLOCK_SIMULATION"; RESET_SIMULATION="RESET_SIMULATION"; COLLECT_EVIDENCE="COLLECT_EVIDENCE"
class RiskLevel: LOW="LOW"; MEDIUM="MEDIUM"; HIGH="HIGH"; CRITICAL="CRITICAL"
@dataclass
class AutomationWorkflow:
    workflow_id: str; tenant_id: str; name: str; description: str = ""; status: str = "DRAFT"; created_at: str = field(default_factory=now)
    def to_dict(self): return asdict(self)
@dataclass
class AutomationAction:
    action_id: str; workflow_id: str; action_type: str; target_system: str; risk_level: str = RiskLevel.MEDIUM; requires_approval: bool = True
    def to_dict(self): return asdict(self)
@dataclass
class AutomationExecution:
    execution_id: str; workflow_id: str; tenant_id: str; status: str = "PENDING_APPROVAL"; started_at: str = field(default_factory=now); completed_at: str | None = None; result: dict = field(default_factory=dict); error_message: str = ""
    def to_dict(self): return asdict(self)
@dataclass
class ApprovalRecord:
    approval_id: str; execution_id: str; tenant_id: str; requester: str; approver: str = ""; decision: str = "PENDING"; timestamp: str = field(default_factory=now); reason: str = ""
    def to_dict(self): return asdict(self)

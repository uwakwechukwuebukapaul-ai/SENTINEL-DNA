from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass(frozen=True)
class ResponseAction:
    action_id: str
    action_type: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    destructive: bool = False
    requires_approval: bool = True
    def to_dict(self): return asdict(self)

@dataclass
class ResponsePlan:
    plan_id: str
    tenant_id: str | None
    incident_type: str
    actions: list[ResponseAction] = field(default_factory=list)
    rationale: str = ""
    risk_score: float = 0.0
    status: str = "pending_approval"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self): return {**asdict(self), "actions": [x.to_dict() for x in self.actions]}

@dataclass
class ApprovalRequest:
    request_id: str
    tenant_id: str | None
    plan_id: str
    requester: str
    approver: str | None = None
    decision: str = "pending"
    requested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decided_at: str | None = None
    def to_dict(self): return asdict(self)

@dataclass
class ExecutionResult:
    execution_id: str
    plan_id: str
    tenant_id: str | None
    status: str
    simulated: bool = True
    actions: list[dict[str, Any]] = field(default_factory=list)
    message: str = "No external action executed"
    def to_dict(self): return asdict(self)

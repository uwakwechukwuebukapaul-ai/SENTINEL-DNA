from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
@dataclass
class SOARAction:
    action_id: str; action_type: str; parameters: dict[str,Any]=field(default_factory=dict); risk_level: str="low"; requires_approval: bool=False
    def to_dict(self): return asdict(self)
@dataclass
class SOARPlaybook:
    id: str; name: str; description: str; trigger_type: str; severity: str; actions: list[SOARAction]; approval_required: bool=True; enabled: bool=True; created_at: str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat()); synthetic_only: bool=True
    def to_dict(self): d=asdict(self); d["actions"]=[a.to_dict() for a in self.actions]; return d
@dataclass
class SOARExecution:
    execution_id: str; playbook_id: str; case_id: str; status: str; actions_completed: list[str]=field(default_factory=list); started_at: str=""; completed_at: str=""; metadata: dict[str,Any]=field(default_factory=dict)
    def to_dict(self): return asdict(self)
@dataclass
class SOARApproval:
    approval_id: str; execution_id: str; approved_by: str=""; status: str="pending"; timestamp: str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat()); notes: str=""
    def to_dict(self): return asdict(self)

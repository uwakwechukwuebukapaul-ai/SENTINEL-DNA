from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class DecisionProvenance:
    source_subsystem:str; source_reference:str=""; basis:str=""; generated_at:str=field(default_factory=now); advisory:bool=True
    def to_dict(self): return asdict(self)
@dataclass
class GovernanceSignal:
    tenant_id:str; category:str; value:object=None; severity:str="medium"; direction:str="stable"; confidence:float=0.0; evidence_references:list=field(default_factory=list); source_references:list=field(default_factory=list); affected_controls:list=field(default_factory=list); affected_assets:list=field(default_factory=list); provenance:list=field(default_factory=list)
    def to_dict(self): return asdict(self)
@dataclass
class DecisionDependency:
    dependency_id:str=field(default_factory=lambda:str(uuid4())); from_signal:str=""; to_signal:str=""; relationship:str="influences"; explanation:str=""; advisory:bool=True
    def to_dict(self): return asdict(self)
@dataclass
class DecisionCandidate:
    tenant_id:str; category:str; priority:str="medium"; severity:str="medium"; status:str="pending_review"; decision_id:str=field(default_factory=lambda:str(uuid4())); rationale:str=""; confidence:float=0.0; evidence_references:list=field(default_factory=list); source_references:list=field(default_factory=list); affected_controls:list=field(default_factory=list); affected_assets:list=field(default_factory=list); dependencies:list=field(default_factory=list); generated_at:str=field(default_factory=now); advisory:bool=True; requires_human_review:bool=True; provenance:list=field(default_factory=list)
    def to_dict(self): return asdict(self)
@dataclass
class ReviewState:
    decision_id:str; tenant_id:str; state:str="pending_review"; reviewer:str=""; note:str=""; updated_at:str=field(default_factory=now)
    def to_dict(self): return asdict(self)

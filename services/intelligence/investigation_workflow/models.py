from dataclasses import asdict, dataclass
from services.intelligence.investigation_learning.models import stable_id
@dataclass(frozen=True)
class WorkflowInsight:
    workflow_id: str
    tenant_id: str
    stage_transitions: tuple = ()
    complexity_indicators: tuple = ()
    improvement_opportunities: tuple = ()
    confidence: str = "insufficient_history"
    provenance: tuple = ()
    uncertainty_state: str = "insufficient_history"
    advisory_only: bool = True
    def to_dict(self): return asdict(self)

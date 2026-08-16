from dataclasses import asdict, dataclass
from services.intelligence.investigation_learning.models import stable_id
@dataclass(frozen=True)
class KnowledgeEvolution:
    knowledge_id: str
    tenant_id: str
    maturity: str = "insufficient_history"
    observed_trends: tuple = ()
    associated_patterns: tuple = ()
    provenance: tuple = ()
    confidence: str = "insufficient_history"
    uncertainty_state: str = "insufficient_history"
    advisory_only: bool = True
    def to_dict(self): return asdict(self)

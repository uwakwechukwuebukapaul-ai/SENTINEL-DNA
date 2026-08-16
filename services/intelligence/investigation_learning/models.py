from dataclasses import asdict, dataclass
import hashlib

def stable_id(tenant_id, kind):
    return f"{kind}-{hashlib.sha256(f'{tenant_id}:{kind}'.encode()).hexdigest()[:20]}"

@dataclass(frozen=True)
class LearningInsight:
    learning_id: str
    tenant_id: str
    observed_patterns: tuple = ()
    evidence_sources: tuple = ()
    confidence: str = "insufficient_history"
    provenance: tuple = ()
    uncertainty_state: str = "insufficient_history"
    improvement_opportunities: tuple = ()
    advisory_only: bool = True
    def to_dict(self): return asdict(self)

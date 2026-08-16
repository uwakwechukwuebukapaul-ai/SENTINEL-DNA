from dataclasses import asdict, dataclass
from typing import Any
def stable_id(tenant_id, kind, value):
    import hashlib
    return f"{kind}-{hashlib.sha256(f'{tenant_id}:{value}'.encode()).hexdigest()[:20]}"
@dataclass(frozen=True)
class SecurityDataSource:
    tenant_id: str; source_id: str; name: str; source_type: str="unknown"; lifecycle_state: str="registered"; connector_readiness: str="insufficient_data"; provenance: tuple=(); advisory_only: bool=True
    def to_dict(self): return asdict(self)
@dataclass(frozen=True)
class NormalizedSecurityEvent:
    tenant_id: str; event_id: str; event_type: str="unknown"; observed: tuple=(); normalized: tuple=(); provenance: tuple=(); normalization_confidence: str="insufficient_data"; evidence_reference: str|None=None; advisory_only: bool=True
    def to_dict(self): return asdict(self)
@dataclass(frozen=True)
class DataQualityReport:
    tenant_id: str; report_id: str; event_quality_score: float|None=None; completeness: str="insufficient_data"; freshness: str="insufficient_data"; normalization_confidence: str="insufficient_data"; observed_event_count: int=0; uncertainty: tuple=(); provenance: tuple=(); advisory_only: bool=True
    def to_dict(self): return asdict(self)

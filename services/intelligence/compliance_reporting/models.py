from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

def now(): return datetime.now(timezone.utc).isoformat()
def _dict(x): return x.to_dict() if hasattr(x,"to_dict") else x

@dataclass
class Provenance:
    source_subsystem:str; source_reference:str=""; basis:str=""; reporting_period:dict=field(default_factory=dict); generated_at:str=field(default_factory=now); advisory:bool=True
    def to_dict(self): return asdict(self)
@dataclass
class Recommendation:
    recommendation_id:str=field(default_factory=lambda:str(uuid4())); category:str="governance"; priority:str="medium"; rationale:str=""; evidence_references:list=field(default_factory=list); source_references:list=field(default_factory=list); advisory:bool=True; requires_human_review:bool=True
    def to_dict(self): return asdict(self)
@dataclass
class ControlReport:
    tenant_id:str; framework_id:str; control_id:str; status:str="unknown"; previous_status:str=""; current_status:str="unknown"; status_change:str=""; evidence_coverage:float=0.0; evidence_freshness:float=0.0; evidence_availability:float=0.0; confidence:float|None=None; drift:dict|None=None; unresolved_gap:bool=False; historical_stability:str="insufficient_history"; recommendation_references:list=field(default_factory=list); provenance:list=field(default_factory=list)
    def to_dict(self): return asdict(self)
@dataclass
class EvidenceSummary:
    tenant_id:str; framework_id:str; evidence_references:list=field(default_factory=list); source_availability:float=0.0; freshness:float=0.0; coverage:float=0.0; completeness:float=0.0; expired:list=field(default_factory=list); missing:list=field(default_factory=list); stale:list=field(default_factory=list); unavailable:list=field(default_factory=list); readiness_impact:str="unknown"; provenance:list=field(default_factory=list)
    def to_dict(self): return asdict(self)
@dataclass
class TrendSummary:
    tenant_id:str; framework_id:str; direction:str="insufficient_history"; improving_controls:list=field(default_factory=list); deteriorating_controls:list=field(default_factory=list); stable_controls:list=field(default_factory=list); recurring_gaps:list=field(default_factory=list); new_gaps:list=field(default_factory=list); resolved_gaps:list=field(default_factory=list); coverage_trend:list=field(default_factory=list); readiness_trend:list=field(default_factory=list); provenance:list=field(default_factory=list)
    def to_dict(self): return asdict(self)
@dataclass
class ExecutiveComplianceSummary:
    tenant_id:str; current_posture:str; major_weaknesses:list=field(default_factory=list); significant_gaps:list=field(default_factory=list); evidence_readiness:float=0.0; audit_readiness:float=0.0; major_trends:list=field(default_factory=list); recurring_issues:list=field(default_factory=list); business_impact_references:list=field(default_factory=list); recommended_priorities:list=field(default_factory=list); provenance:list=field(default_factory=list); advisory:bool=True
    def to_dict(self): return asdict(self)
@dataclass
class GovernanceReport:
    tenant_id:str; report_id:str=field(default_factory=lambda:str(uuid4())); generated_at:str=field(default_factory=now); reporting_period:dict=field(default_factory=dict); frameworks_covered:list=field(default_factory=list); control_totals:dict=field(default_factory=dict); compliant_controls:list=field(default_factory=list); partially_compliant_controls:list=field(default_factory=list); non_compliant_controls:list=field(default_factory=list); insufficient_evidence_controls:list=field(default_factory=list); unknown_controls:list=field(default_factory=list); evidence_coverage:float=0.0; audit_readiness:float=0.0; drift_summary:dict=field(default_factory=dict); unresolved_gap_summary:list=field(default_factory=list); historical_trend:dict=field(default_factory=dict); executive_risk_references:list=field(default_factory=list); recommendations:list=field(default_factory=list); evidence_references:list=field(default_factory=list); provenance:list=field(default_factory=list); advisory:bool=True; certification_claim:bool=False
    def to_dict(self): return asdict(self)

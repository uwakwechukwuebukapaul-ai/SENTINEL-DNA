from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class OutcomeRecord:
    tenant_id:str; lifecycle_id:str; case_id:str=""; investigation_id:str=""; detection_reference:str=""; decision_reference:str=""; approval_reference:str=""; action_reference:str=""; verification_reference:str=""; final_lifecycle_state:str=""; resolution_status:str="UNKNOWN"; verification_status:str="UNKNOWN"; evidence_references:list=field(default_factory=list); provenance:dict=field(default_factory=dict); analyst_feedback:str=""; false_positive_signal:str="unknown"; confidence:float|None=None; uncertainty:str=""; recorded_at:str=field(default_factory=now); outcome_id:str=field(default_factory=lambda:str(uuid4()))
    def to_dict(self): return asdict(self)
@dataclass
class QualityAssessment:
    tenant_id:str; outcome_id:str; detection_quality:str="UNKNOWN"; investigation_quality:str="UNKNOWN"; recommendation_quality:str="UNKNOWN"; action_effectiveness:str="UNKNOWN"; confidence:float|None=None; uncertainty:str=""; human_review_required:bool=True; provenance:dict=field(default_factory=dict)
    def to_dict(self): return asdict(self)
@dataclass
class RecurringPattern:
    tenant_id:str; pattern_type:str; key:str; count:int; outcome_references:list=field(default_factory=list); confidence:float|None=None; provenance:dict=field(default_factory=dict)
    def to_dict(self): return asdict(self)
@dataclass
class ImprovementCandidate:
    tenant_id:str; category:str; title:str; rationale:str; outcome_references:list=field(default_factory=list); evidence_references:list=field(default_factory=list); confidence:float|None=None; priority:str="medium"; advisory:bool=True; requires_human_review:bool=True; provenance:dict=field(default_factory=dict); candidate_id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=now)
    def to_dict(self): return asdict(self)

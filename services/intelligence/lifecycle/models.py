from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
STATES={"DETECTED","INVESTIGATING","UNDERSTOOD","DECISION_PENDING","APPROVAL_PENDING","APPROVED","REJECTED","ACTION_PENDING","ACTION_EXECUTED","VERIFICATION_PENDING","VERIFIED","FAILED","LEARNING","CLOSED"}
ALLOWED={"DETECTED":{"INVESTIGATING"},"INVESTIGATING":{"UNDERSTOOD"},"UNDERSTOOD":{"DECISION_PENDING"},"DECISION_PENDING":{"APPROVAL_PENDING"},"APPROVAL_PENDING":{"APPROVED","REJECTED"},"APPROVED":{"ACTION_PENDING"},"ACTION_PENDING":{"ACTION_EXECUTED"},"ACTION_EXECUTED":{"VERIFICATION_PENDING"},"VERIFICATION_PENDING":{"VERIFIED","FAILED"},"VERIFIED":{"LEARNING"},"FAILED":{"LEARNING"},"LEARNING":{"CLOSED"}}
@dataclass
class Lifecycle:
    tenant_id:str; case_id:str=""; investigation_id:str=""; lifecycle_id:str=field(default_factory=lambda:str(uuid4())); state:str="DETECTED"; created_at:str=field(default_factory=now); updated_at:str=field(default_factory=now); history:list=field(default_factory=list); availability:dict=field(default_factory=dict)
    def to_dict(self): return asdict(self)
@dataclass
class DecisionRecord:
    tenant_id:str; lifecycle_id:str; decision_id:str=field(default_factory=lambda:str(uuid4())); decision_state:str="AI_RECOMMENDATION"; decision_type:str="review"; evidence_references:list=field(default_factory=list); findings:list=field(default_factory=list); risk_context:dict=field(default_factory=dict); recommendation_references:list=field(default_factory=list); rationale:str=""; confidence:float|None=None; uncertainty:str=""; analyst_reference:str=""; created_at:str=field(default_factory=now); provenance:dict=field(default_factory=dict); requires_human_review:bool=True
    def to_dict(self): return asdict(self)
@dataclass
class ApprovalRecord:
    tenant_id:str; lifecycle_id:str; status:str="approval_required"; reviewer_reference:str=""; rationale:str=""; decision_timestamp:str=field(default_factory=now); approval_id:str=field(default_factory=lambda:str(uuid4()))
    def to_dict(self): return asdict(self)
@dataclass
class VerificationRecord:
    tenant_id:str; lifecycle_id:str; status:str="NOT_STARTED"; execution_reference:str=""; outcome_reference:str=""; detail:str=""; recorded_at:str=field(default_factory=now)
    def to_dict(self): return asdict(self)
@dataclass
class LearningRecord:
    tenant_id:str; lifecycle_id:str; detection_reference:str=""; investigation_outcome:str=""; decision_reference:str=""; action_reference:str=""; verification_outcome:str="UNKNOWN"; false_positive:bool|None=None; analyst_feedback:str=""; recommendation_quality:str="unknown"; recurring_pattern:str=""; improvement_candidate:str=""; recorded_at:str=field(default_factory=now)
    def to_dict(self): return asdict(self)

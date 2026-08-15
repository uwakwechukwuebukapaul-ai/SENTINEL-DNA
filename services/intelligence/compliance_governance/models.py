from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class Framework:
    framework_id:str; tenant_id:str; name:str; version:str=""; description:str=""; metadata:dict=field(default_factory=dict)
    def to_dict(self): return asdict(self)
@dataclass
class Control:
    control_id:str; framework_id:str; tenant_id:str; name:str; description:str=""; status:str="unknown"; evidence_refs:list=field(default_factory=list); metadata:dict=field(default_factory=dict)
    def to_dict(self): return asdict(self)
@dataclass
class ControlRequirement:
    requirement_id:str; control_id:str; tenant_id:str; description:str; mandatory:bool=True; status:str="unknown"
    def to_dict(self): return asdict(self)
@dataclass
class ComplianceAssessment:
    assessment_id:str; tenant_id:str; framework_id:str; score:float; status:str; assessed_controls:int=0; compliant_controls:int=0; created_at:str=field(default_factory=now)
    def to_dict(self): return asdict(self)
@dataclass
class ComplianceGap:
    gap_id:str=field(default_factory=lambda:str(uuid4())); tenant_id:str=""; framework_id:str=""; control_id:str=""; severity:str="medium"; explanation:str=""; recommendation:str=""; requires_human_review:bool=True
    def to_dict(self): return asdict(self)

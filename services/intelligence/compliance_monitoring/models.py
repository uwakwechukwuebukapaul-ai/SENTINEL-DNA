from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class ComplianceMonitorSnapshot:
    snapshot_id:str; tenant_id:str; framework_id:str; control_count:int=0; compliant_count:int=0; coverage:float=0.0; status:str="unknown"; observed_at:str=field(default_factory=now); metadata:dict=field(default_factory=dict)
    def to_dict(self): return asdict(self)
@dataclass
class ComplianceDrift:
    drift_id:str=field(default_factory=lambda:str(uuid4())); tenant_id:str=""; framework_id:str=""; control_id:str=""; previous_status:str=""; current_status:str=""; severity:str="medium"; explanation:str=""; requires_human_review:bool=True; detected_at:str=field(default_factory=now)
    def to_dict(self): return asdict(self)
@dataclass
class EvidenceRecord:
    evidence_id:str; tenant_id:str; framework_id:str; control_id:str; reference:str; source:str=""; collected_at:str=field(default_factory=now); valid:bool=True
    def to_dict(self): return asdict(self)
@dataclass
class AuditReadiness:
    readiness_id:str; tenant_id:str; framework_id:str; evidence_count:int=0; covered_controls:int=0; readiness_score:float=0.0; gaps:list=field(default_factory=list); created_at:str=field(default_factory=now)
    def to_dict(self): return asdict(self)

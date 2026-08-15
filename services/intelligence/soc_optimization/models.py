from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class OptimizationSignal:
    tenant_id:str; domain:str; category:str; key:str=""; frequency:int=0; impact:str="unknown"; confidence:float|None=None; evidence_quality:str="UNKNOWN"; status:str="UNKNOWN"; references:list=field(default_factory=list); provenance:dict=field(default_factory=dict); uncertainty:str=""
    def to_dict(self): return asdict(self)
@dataclass
class OptimizationCandidate:
    tenant_id:str; domain:str; category:str; title:str; description:str; priority:str="medium"; score:float=0.0; confidence:float|None=None; outcome_references:list=field(default_factory=list); evidence_references:list=field(default_factory=list); detection_references:list=field(default_factory=list); investigation_references:list=field(default_factory=list); workflow_references:list=field(default_factory=list); provenance:dict=field(default_factory=dict); timestamp:str=field(default_factory=now); advisory:bool=True; requires_human_review:bool=True; uncertainty:str="UNKNOWN"; candidate_id:str=field(default_factory=lambda:str(uuid4()))
    def to_dict(self): return asdict(self)

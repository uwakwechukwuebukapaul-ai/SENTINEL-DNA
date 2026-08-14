from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class HuntingHypothesis:
 organization_id:str; title:str; description:str; source:str; mitre_techniques:list=field(default_factory=list); confidence:float=.8; priority:str="MEDIUM"; status:str="CREATED"; id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=now)
 def public(self): return asdict(self)
@dataclass
class HuntExecution:
 organization_id:str; hypothesis_id:str; query:str; data_sources:list=field(default_factory=list); started_at:str=field(default_factory=now); completed_at:str=""; status:str="RUNNING"; findings_count:int=0; id:str=field(default_factory=lambda:str(uuid4()))
 def public(self): return asdict(self)
@dataclass
class HuntFinding:
 organization_id:str; hunt_id:str; severity:str; entity:str; entity_type:str; description:str; evidence:list=field(default_factory=list); mitre_technique:str=""; confidence:float=.8; id:str=field(default_factory=lambda:str(uuid4())); created_at:str=field(default_factory=now)
 def public(self): return asdict(self)
@dataclass
class GeneratedDetection:
 organization_id:str; finding_id:str; rule_name:str; sigma_rule:dict; severity:str; mitre_mapping:list=field(default_factory=list); approval_status:str="DRAFT"; id:str=field(default_factory=lambda:str(uuid4()))
 def public(self): return asdict(self)

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class IntelligenceRecord:
    tenant_id:str; source_subsystem:str; source_record_id:str; entity_type:str; severity:str="unknown"; confidence:float|None=None; status:str="unknown"; timestamp:str=""; provenance:dict=field(default_factory=dict); requires_human_review:bool=False; data:dict=field(default_factory=dict)
    def to_dict(self): return asdict(self)
@dataclass
class IntelligenceRelationship:
    tenant_id:str; from_type:str; from_id:str; to_type:str; to_id:str; relationship:str; provenance:dict=field(default_factory=dict); created_at:str=field(default_factory=now)
    def to_dict(self): return asdict(self)
@dataclass
class AttentionItem:
    tenant_id:str; source_subsystem:str; source_record_id:str; priority:str="medium"; original_priority:str=""; severity:str="unknown"; rationale:str=""; confidence:float|None=None; provenance:dict=field(default_factory=dict); advisory:bool=True; requires_human_review:bool=True; created_at:str=field(default_factory=now); attention_id:str=field(default_factory=lambda:str(uuid4()))
    def to_dict(self): return asdict(self)
@dataclass
class PlatformSnapshot:
    tenant_id:str; generated_at:str=field(default_factory=now); records:list=field(default_factory=list); relationships:list=field(default_factory=list); attention_queue:list=field(default_factory=list); posture:dict=field(default_factory=dict); availability:dict=field(default_factory=dict); provenance:list=field(default_factory=list)
    def to_dict(self): return asdict(self)

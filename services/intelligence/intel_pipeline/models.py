from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
@dataclass
class IntelligenceSource:
 source_id:str; name:str; feed_type:str; reliability_score:float=.5; ingestion_timestamp:str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat()); metadata:dict=field(default_factory=dict)
 def to_dict(self): return asdict(self)
@dataclass
class NormalizedIndicator:
 indicator_id:str; indicator_type:str; value:str; source_id:str; first_seen:str; last_seen:str; confidence:float; metadata:dict=field(default_factory=dict)
 def to_dict(self): return asdict(self)

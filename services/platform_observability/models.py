from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class PlatformMetric:
    metric_id:str; tenant_id:str; service_name:str; metric_name:str; metric_type:str; value:float; unit:str=""; timestamp:str=field(default_factory=now); status:str="ok"; metadata:dict=field(default_factory=dict)
    def to_dict(self): return asdict(self)
@dataclass
class ServiceHealth:
    service_name:str; tenant_id:str; status:str="unknown"; availability:float=0.0; latency_ms:float=0.0; error_rate:float=0.0; last_checked:str=field(default_factory=now); message:str=""
    def to_dict(self): return asdict(self)

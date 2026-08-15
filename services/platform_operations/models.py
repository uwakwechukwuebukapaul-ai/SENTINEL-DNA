from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class WorkloadSnapshot:
    tenant_id:str; timestamp:str=field(default_factory=now); investigations:int=0; alerts:int=0; ingestion_events:int=0; correlation_events:int=0; hunting_queries:int=0; automation_requests:int=0; copilot_requests:int=0; connector_operations:int=0; metadata:dict=field(default_factory=dict)
    def to_dict(self): return asdict(self)
@dataclass
class CapacitySnapshot:
    tenant_id:str; timestamp:str=field(default_factory=now); service_name:str=""; utilization:float=0.0; throughput:float=0.0; queue_depth:int=0; latency:float=0.0; error_rate:float=0.0; available_capacity:float=1.0; metadata:dict=field(default_factory=dict)
    def to_dict(self): return asdict(self)
@dataclass
class OperationalFinding:
    finding_id:str=field(default_factory=lambda:str(uuid4())); tenant_id:str=""; category:str="capacity"; severity:str="low"; service_name:str=""; title:str=""; explanation:str=""; recommendation:str=""; requires_human_review:bool=True; created_at:str=field(default_factory=now)
    def to_dict(self): return asdict(self)

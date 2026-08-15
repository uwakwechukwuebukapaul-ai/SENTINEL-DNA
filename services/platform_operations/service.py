from .models import WorkloadSnapshot,CapacitySnapshot
from .repository import OperationsRepository
from .workload import WorkloadAnalyzer
from .capacity import CapacityAnalyzer
from .forecasting import OperationalForecaster
from .aggregation import OperationsAggregator
from .recommendations import OperationsRecommendations
class PlatformOperationsService:
    def __init__(self,repository=None,audit=None): self.repository=repository or OperationsRepository(); self.workload=WorkloadAnalyzer(); self.capacity=CapacityAnalyzer(); self.forecaster=OperationalForecaster(); self.aggregator=OperationsAggregator(); self.recommendations=OperationsRecommendations(); self.audit=audit
    def record_workload(self,tenant_id,**kwargs):
        x=WorkloadSnapshot(tenant_id,**kwargs); self.repository.save_workload(x); return x
    def record_capacity(self,tenant_id,service_name,**kwargs):
        x=CapacitySnapshot(tenant_id,service_name=service_name,**kwargs); self.repository.save_capacity(x); return x
    def analyze(self,tenant_id):
        ws=self.repository.list_workloads(tenant_id); cs=self.repository.list_capacities(tenant_id); return {"summary":self.aggregator.summarize(ws,cs),"workload_pressure":[self.workload.pressure(x) for x in ws],"capacity":[self.capacity.evaluate(x) for x in cs]}
    def forecast(self,tenant_id,service_name): return self.forecaster.forecast(self.repository.list_capacities(tenant_id,service_name))
    def generate_findings(self,tenant_id):
        out=[]
        for x in self.repository.list_capacities(tenant_id): out.extend(self.recommendations.from_capacity(tenant_id,x,self.capacity.evaluate(x)))
        return out

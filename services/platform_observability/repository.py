class ObservabilityRepository:
    def __init__(self): self.metrics={}; self.health={}
    def save_metric(self,x): self.metrics[(x.tenant_id,x.metric_id)]=x; return x
    def list_metrics(self,t,service_name=None): return [x for (tenant,_),x in self.metrics.items() if tenant==t and (service_name is None or x.service_name==service_name)]
    def save_health(self,x): self.health[(x.tenant_id,x.service_name)]=x; return x
    def get_health(self,service_name,t): return self.health.get((t,service_name))
    def list_health(self,t): return [x for (tenant,_),x in self.health.items() if tenant==t]

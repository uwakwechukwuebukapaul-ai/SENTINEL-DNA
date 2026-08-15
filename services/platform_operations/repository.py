class OperationsRepository:
    """Stores derived operational snapshots only; raw metrics remain Phase 30.1-owned."""
    def __init__(self): self.workloads={}; self.capacities={}
    def save_workload(self,x): self.workloads.setdefault(x.tenant_id,[]).append(x); return x
    def save_capacity(self,x): self.capacities.setdefault((x.tenant_id,x.service_name),[]).append(x); return x
    def list_workloads(self,t): return self.workloads.get(t,[])
    def list_capacities(self,t,service_name=None): return [x for (tenant,service),items in self.capacities.items() if tenant==t and (service_name is None or service==service_name) for x in items]

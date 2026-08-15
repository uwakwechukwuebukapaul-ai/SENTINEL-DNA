class CommandSurfaceRepository:
    def __init__(self): self.snapshots={}; self.attention={}; self.decisions={}; self.history={}
    def save_snapshot(self, x): self.snapshots[x.tenant_id]=x; self.history.setdefault(x.tenant_id, []).append(x)
    def get_snapshot(self, tenant_id): return self.snapshots.get(tenant_id)
    def get_history(self, tenant_id): return list(self.history.get(tenant_id, []))
    def save_attention(self, tenant_id, xs): self.attention[tenant_id]=list(xs)
    def save_decisions(self, tenant_id, xs): self.decisions[tenant_id]=list(xs)
    def get_attention(self, tenant_id): return list(self.attention.get(tenant_id, []))
    def get_decisions(self, tenant_id): return list(self.decisions.get(tenant_id, []))

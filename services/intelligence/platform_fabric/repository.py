class PlatformFabricRepository:
    def __init__(self): self.snapshots={}; self.records={}; self.relationships={}; self.attention={}
    def save_snapshot(self,x): self.snapshots[(x.tenant_id,x.generated_at)]=x; return x
    def save_records(self,items):
        for x in items:self.records[(x.tenant_id,x.source_subsystem,x.source_record_id)]=x
    def save_relationships(self,items):
        for x in items:self.relationships[(x.tenant_id,x.from_type,x.from_id,x.to_type,x.to_id)]=x
    def save_attention(self,items):
        for x in items:self.attention[(x.tenant_id,x.attention_id)]=x
    def list_snapshots(self,tenant_id): return [x for (t,_),x in self.snapshots.items() if t==tenant_id]
    def list_records(self,tenant_id): return [x for (t,_,_),x in self.records.items() if t==tenant_id]
    def list_relationships(self,tenant_id): return [x for (t,_,_,_,_),x in self.relationships.items() if t==tenant_id]
    def list_attention(self,tenant_id): return [x for (t,_),x in self.attention.items() if t==tenant_id]

class AttentionRepository:
    def __init__(self): self.items={}
    def save(self,item): self.items[(item.tenant_id,item.attention_id)]=item; return item
    def get(self,tenant_id,attention_id): return self.items.get((tenant_id,str(attention_id)))
    def list(self,tenant_id,**filters):
        values=[x for (tenant,_),x in self.items.items() if tenant==tenant_id]
        for key in ("state","attention_type","severity","source_domain","entity_reference","investigation_reference"):
            if filters.get(key): values=[x for x in values if getattr(x,key)==filters[key]]
        return sorted(values,key=lambda x:(self._rank(x.priority),self._rank(x.severity),not x.requires_human_review,x.updated_at,x.attention_id),reverse=True)
    @staticmethod
    def _rank(value): return {"critical":5,"high":4,"medium":3,"low":2,"info":1,"unknown":0}.get(str(value).lower(),0)
    def update_state(self,tenant_id,attention_id,state):
        item=self.get(tenant_id,attention_id)
        if item and state in {"acknowledged","deferred"}: item.state=state; item.updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        return item

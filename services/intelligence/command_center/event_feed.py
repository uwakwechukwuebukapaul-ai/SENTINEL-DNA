from .events import AnalystEvent

class EventRepository:
    def __init__(self): self._events={}; self._ack={}
    def save(self,event): self._events[(event.tenant_id,event.event_id)]=event; return event
    def get(self,tenant_id,event_id): return self._events.get((tenant_id,str(event_id)))
    def list(self,tenant_id,**filters):
        values=[x for (tenant,event),x in self._events.items() if tenant==tenant_id]
        if filters.get("category"): values=[x for x in values if x.category==filters["category"]]
        if filters.get("severity"): values=[x for x in values if x.severity==filters["severity"]]
        if filters.get("source_domain"): values=[x for x in values if x.source_domain==filters["source_domain"]]
        if filters.get("entity_reference"): values=[x for x in values if x.entity_reference==filters["entity_reference"]]
        if filters.get("investigation_id"): values=[x for x in values if x.related.get("investigation_id")==filters["investigation_id"]]
        if filters.get("since"): values=[x for x in values if x.timestamp>filters["since"]]
        if filters.get("acknowledgement"): values=[x for x in values if x.acknowledgement==filters["acknowledgement"]]
        return sorted(values,key=lambda x:(x.timestamp,x.event_id),reverse=True)
    def acknowledge(self,tenant_id,event_id):
        event=self.get(tenant_id,event_id)
        if event: event.acknowledgement="acknowledged"
        return event

class AnalystEventFeed:
    def __init__(self,repository=None): self.repository=repository or EventRepository()
    def record(self, tenant_id, event_type, category, title, **source):
        event=AnalystEvent(tenant_id,event_type,category,title,**source); existing=self.repository.get(tenant_id,event.event_id)
        return existing or self.repository.save(event)
    def events(self,tenant_id,**filters): return self.repository.list(tenant_id,**filters)
    def get(self,tenant_id,event_id): return self.repository.get(tenant_id,event_id)
    def latest(self,tenant_id,limit=20,**filters): return self.events(tenant_id,**filters)[:max(0,int(limit))]
    def history(self,tenant_id,**filters): return self.events(tenant_id,**filters)
    def acknowledge(self,tenant_id,event_id): return self.repository.acknowledge(tenant_id,event_id)
    def copilot_context(self,tenant_id,event_id):
        event=self.get(tenant_id,event_id); return None if not event else {"tenant_id":tenant_id,"event":event.to_dict(),"advisory":True,"requires_human_review":event.requires_human_review,"tts_enabled":False}

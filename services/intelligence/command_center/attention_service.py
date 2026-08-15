from .attention import AttentionItem
from .attention_repository import AttentionRepository

class AnalystAttentionService:
    def __init__(self,event_feed=None,repository=None): self.event_feed=event_feed; self.repository=repository or AttentionRepository()
    def _type(self,event):
        return {"evidence_unavailable":"evidence_unavailable","evidence_insufficient":"insufficient_evidence","risk_increased":"risk_change","compliance_drift":"compliance_drift","governance_review_required":"governance_review","lifecycle_state_changed":"lifecycle_review","capacity_pressure":"operational_pressure","optimization_candidate_created":"optimization_candidate"}.get(event.event_type,"critical_change" if event.severity=="critical" else event.category.lower())
    def _priority(self,event): return event.priority if event.priority!="medium" or event.severity=="unknown" else {"critical":"critical","high":"high","medium":"medium","low":"low","info":"info"}.get(event.severity,"unknown")
    def record_from_event(self,event):
        existing=[x for x in self.repository.list(event.tenant_id) if x.source_domain==event.source_domain and x.source_reference==event.source_reference and x.attention_type==self._type(event)]
        related=(existing[0].related_event_ids if existing else [])
        if event.event_id not in related: related=related+[event.event_id]
        item=AttentionItem(event.tenant_id,event.event_id,self._type(event),self._priority(event),event.severity,event.title,event.summary,
            event.summary or f"{event.source_domain} reported a change requiring analyst review.",event.source_domain,event.source_reference,event.entity_type,event.entity_reference,event.related.get("investigation_id", ""),event.related.get("evidence_references", []),related,event.confidence,event.uncertainty,{**(existing[0].provenance if existing else {}), **event.provenance},event.requires_human_review,True,event.navigation_target,first_seen=existing[0].first_seen if existing else event.timestamp,last_seen=event.timestamp,recurring_count=len(related),authoritative_priority=event.priority)
        if existing: item.attention_id=existing[0].attention_id; item.state=existing[0].state; item.created_at=existing[0].created_at
        return self.repository.save(item)
    def derive(self,tenant_id,**filters):
        if not self.event_feed: return []
        for event in self.event_feed.events(tenant_id,**filters): self.record_from_event(event)
        return self.get_attention_queue(tenant_id)
    def get_attention(self,tenant_id,attention_id): return self.repository.get(tenant_id,attention_id)
    def get_attention_queue(self,tenant_id,**filters): return self.repository.list(tenant_id,**filters)
    def get_attention_history(self,tenant_id,**filters): return self.get_attention_queue(tenant_id,**filters)
    def acknowledge_attention(self,tenant_id,attention_id): return self.repository.update_state(tenant_id,attention_id,"acknowledged")
    def defer_attention(self,tenant_id,attention_id): return self.repository.update_state(tenant_id,attention_id,"deferred")
    def get_related_events(self,tenant_id,attention_id):
        item=self.get_attention(tenant_id,attention_id); return [] if not item or not self.event_feed else [self.event_feed.get(tenant_id,x) for x in item.related_event_ids if self.event_feed.get(tenant_id,x)]
    def get_attention_context(self,tenant_id,attention_id):
        item=self.get_attention(tenant_id,attention_id); return None if not item else {"tenant_id":tenant_id,"attention":item.to_dict(),"related_events":[x.to_dict() for x in self.get_related_events(tenant_id,attention_id)],"advisory":True,"requires_human_review":item.requires_human_review,"tts_enabled":False}

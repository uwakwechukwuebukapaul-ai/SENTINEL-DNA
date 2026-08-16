from .models import NormalizedSecurityEvent, stable_id
class DataIngestionService:
    def __init__(self, normalizer=None, evidence=None, context=None, data_lake=None): self.normalizer,self.evidence,self.context,self.data_lake=normalizer,evidence,context,data_lake
    def normalize(self,tenant_id,source_id,event):
        normalized=self.normalizer.normalize(event) if self.normalizer and hasattr(self.normalizer,"normalize") else dict(event)
        observed=tuple(sorted((str(k),str(v)) for k,v in event.items())); fields=tuple(sorted(str(k) for k in normalized))
        return NormalizedSecurityEvent(tenant_id,stable_id(tenant_id,"event",f"{source_id}:{event.get('event_id',hash(str(event)))}"),str(normalized.get("event_type","unknown")),observed,fields,(("source_id",source_id),),"moderate" if self.normalizer else "insufficient_data",None,True)
    def ingest(self,tenant_id,source_id,event): return self.normalize(tenant_id,source_id,event)

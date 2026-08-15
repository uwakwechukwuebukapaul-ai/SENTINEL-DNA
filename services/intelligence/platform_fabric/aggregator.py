from .models import AttentionItem, PlatformSnapshot
class PlatformAggregator:
    def build(self,tenant_id,records,relationships,availability,prioritizer,provenance):
        queue=[AttentionItem(tenant_id,r.source_subsystem,r.source_record_id,prioritizer.priority(r),r.data.get("priority",""),r.severity,prioritizer.rationale(r,prioritizer.priority(r)),r.confidence,r.provenance,True,True) for r in records if r.severity in {"critical","high","medium"} or r.requires_human_review]
        queue.sort(key=lambda x:(-prioritizer.weights.get(x.priority,0),x.source_subsystem,x.source_record_id))
        return PlatformSnapshot(tenant_id,records=records,relationships=relationships,attention_queue=queue,posture={"record_count":len(records),"attention_count":len(queue)},availability=availability,provenance=provenance.collect(records))

from datetime import datetime, timezone
from .models import EvidenceSummary, Provenance
class EvidenceReportBuilder:
    def build(self,tenant_id,framework_id,evidence,controls,readiness):
        refs=[x.reference for x in evidence if getattr(x,"reference","")]; ids={getattr(x,"control_id","") for x in evidence}; control_ids={getattr(x,"control_id","") for x in controls}; current=datetime.now(timezone.utc)
        expired=[x.reference for x in evidence if getattr(x,"expires_at",None) and datetime.fromisoformat(x.expires_at.replace("Z","+00:00"))<current]
        return EvidenceSummary(tenant_id,framework_id,refs,sum(getattr(x,"available",True) for x in evidence)/len(evidence) if evidence else 0.0,getattr(readiness,"freshness_score",0.0),getattr(readiness,"completeness_score",0.0),getattr(readiness,"completeness_score",0.0),sorted(expired),sorted(control_ids-ids),[x.reference for x in evidence if not getattr(x,"valid",True)],[x.reference for x in evidence if not getattr(x,"available",True)],"attention_required",[Provenance("compliance_monitoring",x.reference,"evidence reference supplied by monitoring") for x in evidence])

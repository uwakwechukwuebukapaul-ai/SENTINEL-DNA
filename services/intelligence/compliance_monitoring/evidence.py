from datetime import datetime, timezone
from uuid import uuid4
from .models import EvidenceRecord
class EvidenceTracker:
    def record(self,tenant_id,framework_id,control_id,reference,source="",**kwargs): return EvidenceRecord(kwargs.pop("evidence_id",str(uuid4())),tenant_id,framework_id,control_id,reference,source,**kwargs)
    def readiness(self,tenant_id,framework_id,controls,evidence):
        now=datetime.now(timezone.utc); total=len(controls); control_ids={x.control_id for x in controls}
        usable=[x for x in evidence if x.tenant_id==tenant_id and x.valid and x.available and (not x.expires_at or datetime.fromisoformat(x.expires_at.replace("Z","+00:00"))>=now)]
        covered={x.control_id for x in usable}; complete=covered & control_ids; freshness=len(usable)/len(evidence) if evidence else 0.0; availability=sum(x.available for x in evidence)/len(evidence) if evidence else 0.0; score=len(complete)/total if total else 0.0
        gaps=[{"control_id":x.control_id,"type":"missing_evidence","requires_human_review":True} for x in controls if x.control_id not in complete]
        from .models import AuditReadiness
        return AuditReadiness("READINESS-"+framework_id,tenant_id,framework_id,len(evidence),len(complete),round((score+freshness+availability)/3,2),gaps, freshness_score=round(freshness,2),completeness_score=round(score,2),availability_score=round(availability,2))

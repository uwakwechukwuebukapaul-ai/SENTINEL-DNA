from .models import EvidenceRecord
class EvidenceTracker:
    def record(self,tenant_id,framework_id,control_id,reference,source=""): return EvidenceRecord(reference,tenant_id,framework_id,control_id,reference,source)
    def readiness(self,tenant_id,framework_id,controls,evidence):
        covered={x.control_id for x in evidence if x.valid and x.tenant_id==tenant_id}; total=len(controls); score=len(covered & {x.control_id for x in controls})/total if total else 0.0
        from .models import AuditReadiness
        return AuditReadiness("READINESS-"+framework_id,tenant_id,framework_id,len(evidence),len(covered),round(score,2),[])

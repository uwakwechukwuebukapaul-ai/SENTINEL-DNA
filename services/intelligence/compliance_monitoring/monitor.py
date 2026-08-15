from uuid import uuid4
from .models import ComplianceMonitorSnapshot
class ComplianceMonitor:
    def snapshot(self,tenant_id,framework_id,controls):
        total=len(controls); compliant=sum(x.status.lower() in {"implemented","compliant","effective","passed"} for x in controls); coverage=compliant/total if total else 0.0
        return ComplianceMonitorSnapshot(str(uuid4()),tenant_id,framework_id,total,compliant,round(coverage,2),"healthy" if coverage>=.8 else "attention_required")

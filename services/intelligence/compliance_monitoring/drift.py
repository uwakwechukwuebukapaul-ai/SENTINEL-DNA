from .models import ComplianceDrift
class DriftDetector:
    def compare(self,tenant_id,framework_id,previous,current):
        old={x.control_id:x for x in previous}; return [ComplianceDrift(tenant_id=tenant_id,framework_id=framework_id,control_id=x.control_id,previous_status=old[x.control_id].status,current_status=x.status,severity="high" if x.status.lower() in {"failed","non_compliant"} else "medium",explanation="Control status changed since the previous observation.",metadata={"category":"deteriorating" if x.status.lower() in {"failed","non_compliant"} else "resolved" if old[x.control_id].status.lower() in {"failed","non_compliant"} else "changed"}) for x in current if x.control_id in old and old[x.control_id].status!=x.status]

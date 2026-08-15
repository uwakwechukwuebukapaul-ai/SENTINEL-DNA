from .models import ComplianceGap
class GapEngine:
    def find(self,tenant_id,framework_id,controls,analyzer):
        return [ComplianceGap(tenant_id=tenant_id,framework_id=framework_id,control_id=x.control_id,severity="high" if x.status=="unknown" else "medium",explanation="Control evidence or implementation is incomplete.",recommendation="Review control ownership and collect auditable evidence.") for x in controls if not analyzer.evaluate(x)]

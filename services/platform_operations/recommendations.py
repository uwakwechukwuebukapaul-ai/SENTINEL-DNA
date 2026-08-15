from .models import OperationalFinding
class OperationsRecommendations:
    def from_capacity(self,tenant_id,snapshot,assessment):
        if assessment["severity"]=="low": return []
        return [OperationalFinding(tenant_id=tenant_id,category="capacity",severity=assessment["severity"],service_name=snapshot.service_name,title="Operational capacity pressure detected",explanation="Utilization or error rate is elevated for this service.",recommendation="Review workload distribution, queue depth, and scaling options.")]

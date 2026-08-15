from .models import ServiceHealth
class HealthEngine:
    def evaluate(self,tenant_id,service_name,metrics):
        errors=[x for x in metrics if x.metric_type=="error_rate"]; latency=[x for x in metrics if x.metric_type=="duration"]; error=max((x.value for x in errors),default=0.0); lat=max((x.value for x in latency),default=0.0); status="healthy" if error<.1 else "degraded" if error<.5 else "unhealthy"
        return ServiceHealth(service_name,tenant_id,status,1.0-error,lat,error)

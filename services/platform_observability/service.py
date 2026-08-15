from .repository import ObservabilityRepository
from .metrics import MetricsCollector
from .health import HealthEngine
from .aggregation import TelemetryAggregator
from .analytics import ObservabilityAnalytics
from .recommendations import ObservabilityRecommendations
class PlatformObservabilityService:
    def __init__(self,repository=None,audit=None):
        self.repository=repository or ObservabilityRepository(); self.collector=MetricsCollector(); self.health_engine=HealthEngine(); self.aggregator=TelemetryAggregator(); self.analytics=ObservabilityAnalytics(); self.recommendations=ObservabilityRecommendations(); self.audit=audit
    def record_metric(self,tenant_id,service_name,metric_name,metric_type,value,unit="",metadata=None):
        metric=self.collector.create(tenant_id,service_name,metric_name,metric_type,value,unit,metadata); self.repository.save_metric(metric); self._audit("platform_metric_recorded",tenant_id,service_name=service_name); return metric
    def check_health(self,tenant_id,service_name):
        health=self.health_engine.evaluate(tenant_id,service_name,self.repository.list_metrics(tenant_id,service_name)); self.repository.save_health(health); return health
    def snapshot(self,tenant_id):
        metrics=self.repository.list_metrics(tenant_id); health=[self.check_health(tenant_id,x) for x in {m.service_name for m in metrics}]; return {"tenant_id":tenant_id,"aggregation":self.aggregator.aggregate(metrics),"health":[x.to_dict() for x in health]}
    def analyze(self,tenant_id):
        metrics=self.repository.list_metrics(tenant_id); return {"trends":self.analytics.trends(metrics),"anomalies":[x.to_dict() for x in self.analytics.anomalies(metrics)]}
    def generate_recommendations(self,tenant_id): return self.recommendations.generate([self.check_health(tenant_id,x) for x in {m.service_name for m in self.repository.list_metrics(tenant_id)}])
    def _audit(self,event,tenant_id,**details):
        if self.audit and hasattr(self.audit,"record"): self.audit.record(event,tenant_id=tenant_id,**details)

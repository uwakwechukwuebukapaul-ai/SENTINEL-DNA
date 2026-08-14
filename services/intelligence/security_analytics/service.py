from uuid import uuid4
from .anomaly import AnomalyEngine
from .forecast import ForecastEngine
from .models import SecurityMetricSnapshot
from .repository import SecurityAnalyticsRepository
from .trend import TrendEngine

class SecurityAnalyticsService:
    def __init__(self, tenant_id=None, repository=None): self.tenant_id=tenant_id; self.repository=repository or SecurityAnalyticsRepository(); self.trend=TrendEngine(); self.anomaly=AnomalyEngine(); self.forecast=ForecastEngine()
    def record_snapshot(self, metrics, timestamp=None): return self.repository.save(SecurityMetricSnapshot(str(uuid4()), self.tenant_id, timestamp or SecurityMetricSnapshot.__dataclass_fields__["timestamp"].default_factory(), {key: float(value) for key,value in metrics.items()}))
    def analyze_trends(self): return self.trend.analyze(self.repository.list(self.tenant_id))
    def detect_anomalies(self): return self.anomaly.detect(self.repository.list(self.tenant_id))
    def generate_forecast(self): return self.forecast.forecast(self.repository.list(self.tenant_id))

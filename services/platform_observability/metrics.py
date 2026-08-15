from uuid import uuid4
from .models import PlatformMetric
class MetricsCollector:
    TYPES={"counter","gauge","duration","rate","error_rate"}
    def create(self,tenant_id,service_name,metric_name,metric_type,value,unit="",metadata=None):
        if metric_type not in self.TYPES: raise ValueError("unsupported_metric_type")
        return PlatformMetric(str(uuid4()),tenant_id,service_name,metric_name,metric_type,float(value),unit,metadata=metadata or {})

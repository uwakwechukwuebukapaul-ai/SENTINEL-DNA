from uuid import uuid4
from .models import SecurityMetricSnapshot, SecurityAnomaly

class AnomalyEngine:
    def detect(self, snapshots: list[SecurityMetricSnapshot]):
        if len(snapshots) < 2: return []
        baseline=snapshots[:-1]; current=snapshots[-1]; result=[]
        for metric, observed in current.metrics.items():
            values=[item.metrics.get(metric,0) for item in baseline]; average=sum(values)/len(values)
            if average and observed > average*1.5: result.append(SecurityAnomaly(str(uuid4()), current.tenant_id, metric, observed, average, "high" if observed > average*2 else "medium", f"{metric} is unusually elevated"))
        return result

from .models import SecurityMetricSnapshot, ForecastResult

class ForecastEngine:
    def forecast(self, snapshots: list[SecurityMetricSnapshot]):
        trends=[]
        if len(snapshots)>1:
            first,last=snapshots[0],snapshots[-1]; trends=[last.metrics.get(k,0)-first.metrics.get(k,0) for k in set(first.metrics)|set(last.metrics)]
        change=round(sum(trends)/len(trends),2) if trends else 0.0; direction="increasing_risk" if change < 0 else "decreasing_risk" if change > 0 else "stable"; return ForecastResult(snapshots[-1].tenant_id if snapshots else None, direction, change, recommended_actions=["review declining posture domains"] if change < 0 else [], confidence=min(1.0,len(snapshots)/5))

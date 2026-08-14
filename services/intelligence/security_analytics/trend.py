from .models import SecurityMetricSnapshot, TrendAnalysis

class TrendEngine:
    def analyze(self, snapshots: list[SecurityMetricSnapshot]):
        if len(snapshots) < 2: return []
        first, last=snapshots[0], snapshots[-1]; keys=set(first.metrics)|set(last.metrics); return [TrendAnalysis(key, "improving" if (last.metrics.get(key,0)-first.metrics.get(key,0)) > 0 else "declining" if last.metrics.get(key,0) < first.metrics.get(key,0) else "stable", round(last.metrics.get(key,0)-first.metrics.get(key,0),2), min(1.0, len(snapshots)/5), f"{key} changed by {round(last.metrics.get(key,0)-first.metrics.get(key,0),2)}") for key in sorted(keys)]

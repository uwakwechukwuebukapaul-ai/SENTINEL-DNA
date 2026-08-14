from time import perf_counter
class MonitoringService:
    def __init__(self): self.metrics = {"system": {"status": "healthy"}, "workers": {}, "connectors": {}, "detection_latency_ms": [], "investigation_latency_ms": [], "ai_latency_ms": []}
    def record_latency(self, category, elapsed_ms):
        key = f"{category}_latency_ms"
        if key not in self.metrics: raise ValueError("invalid_metric_category")
        self.metrics[key].append(float(elapsed_ms)); return elapsed_ms
    def worker(self, name, processed=0, failures=0, queue_depth=0): self.metrics["workers"][name] = {"processed": processed, "failures": failures, "queue_depth": queue_depth, "status": "healthy" if failures == 0 else "degraded"}; return self.metrics["workers"][name]
    def connector(self, connector_id, status, events=0): self.metrics["connectors"][connector_id] = {"status": status, "events": events}; return self.metrics["connectors"][connector_id]
    def snapshot(self):
        value = dict(self.metrics)
        for key in ("detection_latency_ms", "investigation_latency_ms", "ai_latency_ms"):
            values = value[key]; value[key] = {"count": len(values), "average_ms": round(sum(values) / len(values), 2) if values else 0, "max_ms": max(values) if values else 0}
        return value

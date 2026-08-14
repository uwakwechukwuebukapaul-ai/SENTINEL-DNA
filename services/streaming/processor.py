from time import perf_counter
from .models import StreamMetrics
class EventProcessor:
    def __init__(self, queue=None): self.queue = queue; self.metrics = StreamMetrics(); self.events = []; self.alerts = []; self.investigations = []; self.automation_actions = []
    def process(self, event, normalizer=None, detector=None):
        started = perf_counter()
        try:
            if not event.organization_id: raise ValueError("tenant_required")
            payload = normalizer(event.payload) if normalizer else event.payload
            self.events.append(payload); result = detector(payload) if detector else []
            self.alerts.extend(result); self.metrics.events_processed += 1; return result
        except Exception:
            self.metrics.failures += 1; raise
        finally:
            self.metrics.total_latency_ms += (perf_counter() - started) * 1000
            self.metrics.queue_depth = self.queue.depth() if self.queue else 0
    def drain(self, handler, limit=100):
        items = self.queue.consume(limit) if self.queue else []
        for item in items: handler(item)
        self.metrics.queue_depth = self.queue.depth() if self.queue else 0; return len(items)

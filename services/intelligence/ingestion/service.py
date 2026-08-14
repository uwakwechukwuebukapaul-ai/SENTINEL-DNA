from .collectors import SyntheticEventCollector
from .models import IngestionMetrics
from .pipeline import SecurityIngestionPipeline
from .repository import IngestionRepository

class SecurityIngestionService:
    def __init__(self, tenant_id=None, repository=None, collector=None):
        self.tenant_id=tenant_id; self.repository=repository or IngestionRepository(); self.collector=collector or SyntheticEventCollector(tenant_id, "synthetic"); self.pipeline=SecurityIngestionPipeline(repository=self.repository)
    def ingest(self, payload): return self.collector.collect(payload)
    def normalize(self, events): return self.pipeline.process(events, self.tenant_id)
    def route(self, events): return self.normalize(events)
    def metrics(self): return self.pipeline.metrics

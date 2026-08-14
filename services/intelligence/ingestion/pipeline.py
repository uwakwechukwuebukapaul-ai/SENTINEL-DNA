from uuid import uuid4
from .models import IngestionBatch, IngestionMetrics
from .normalizer import SecurityEventNormalizer

class SecurityIngestionPipeline:
    def __init__(self, normalizer=None, repository=None): self.normalizer=normalizer or SecurityEventNormalizer(); self.repository=repository; self.metrics=IngestionMetrics()
    def process(self, events, tenant_id=None):
        normalized=[]; failed=0
        for event in events:
            try:
                item=self.normalizer.normalize(event)
                if item.tenant_id != tenant_id: raise ValueError("event tenant does not match pipeline tenant")
                normalized.append(self.repository.save(item) if self.repository else item)
            except Exception: failed += 1
        self.metrics.received += len(events); self.metrics.normalized += len(normalized); self.metrics.failed += failed; self.metrics.routed += len(normalized)
        for item in normalized: self.metrics.by_category[item.category] = self.metrics.by_category.get(item.category, 0) + 1
        return normalized, IngestionBatch(str(uuid4()), tenant_id, len(events), len(normalized), failed, "partial" if failed else "completed")

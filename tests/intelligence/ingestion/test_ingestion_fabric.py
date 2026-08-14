from services.intelligence.ingestion import APICollector, IngestionRepository, SecurityEventNormalizer, SecurityIngestionService, SyntheticEventCollector, WebhookCollector
from services.intelligence.investigation.investigation_result import InvestigationResult

def test_normalization():
    event = SyntheticEventCollector("tenant-a", "test").collect({"id": "e1", "event_type": "login", "user": "alice"})[0]
    normalized = SecurityEventNormalizer().normalize(event)
    assert normalized.category == "identity" and normalized.event_id == "e1"

def test_collectors():
    assert len(SyntheticEventCollector("t").collect([{"id": "1"}, {"id": "2"}])) == 2
    assert len(WebhookCollector("t").collect({"events": [{"id": "1"}]})) == 1
    assert len(APICollector("t").collect(lambda: [{"id": "1"}])) == 1

def test_tenant_isolation():
    repository = IngestionRepository()
    service = SecurityIngestionService("tenant-a", repository)
    service.normalize(service.ingest({"id": "e1", "event_type": "dns"}))
    assert len(repository.list("tenant-a")) == 1 and repository.list("tenant-b") == []

def test_pipeline_routing_and_failure_handling():
    service = SecurityIngestionService("tenant-a")
    events = service.ingest([{"id": "e1", "event_type": "process"}, {"id": "e2", "event_type": "cloud"}])
    normalized, batch = service.route(events)
    assert len(normalized) == 2 and batch.failed_count == 0 and service.metrics().routed == 2

def test_backward_compatibility():
    result = InvestigationResult()
    assert result.ingestion_context is None and "ingestion_context" in result.to_dict()

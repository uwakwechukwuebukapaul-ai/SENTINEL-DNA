from services.intelligence.data_fabric.adapters import DataFabricIntelligenceAdapters
from services.data_fabric.ingestion import DataIngestionService
def test_adapters_are_advisory_and_tenant_scoped():
    e=DataIngestionService().ingest('t','s',{'event_id':'1'}); r=DataFabricIntelligenceAdapters().evidence_reference('t',e); assert r['tenant_id']=='t' and r['advisory_only']

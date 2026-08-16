from services.data_fabric.ingestion import DataIngestionService
class N:
    def normalize(self,event): return {'event_type':'alert',**event}
def test_normalization_delegates_and_preserves_provenance():
    e=DataIngestionService(N()).ingest('t','s',{'event_id':'1'}); assert e.event_type=='alert'; assert ('source_id','s') in e.provenance

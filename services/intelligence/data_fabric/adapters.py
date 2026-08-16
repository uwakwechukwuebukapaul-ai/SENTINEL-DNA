class DataFabricIntelligenceAdapters:
    def __init__(self,evidence_engine=None,investigation_context=None,data_lake=None,intelligence_fabric=None): self.evidence_engine,self.investigation_context,self.data_lake,self.intelligence_fabric=evidence_engine,investigation_context,data_lake,intelligence_fabric
    def evidence_reference(self,tenant_id,event): return {"tenant_id":tenant_id,"event_id":event.event_id,"integration":"evidence_engine","available":self.evidence_engine is not None,"advisory_only":True}
    def investigation_reference(self,tenant_id,event): return {"tenant_id":tenant_id,"event_id":event.event_id,"integration":"investigation_context","available":self.investigation_context is not None,"advisory_only":True}

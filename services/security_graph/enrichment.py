class GraphEnrichmentService:
 def __init__(self,query_engine): self.query_engine=query_engine
 def enrich(self,entity_id,tenant_id=None):
  related=self.query_engine.find_related_entities(entity_id,tenant_id); return {"related_assets":[x.to_dict() for x in related if x.entity_type=="asset"],"related_campaigns":[x.to_dict() for x in related if x.entity_type=="campaign"],"related_iocs":[x.to_dict() for x in related if x.entity_type=="IOC"],"attack_paths":[]}

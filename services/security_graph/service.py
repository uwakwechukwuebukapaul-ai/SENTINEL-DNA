from .repository import SecurityGraphRepository
from .query_engine import GraphQueryEngine
from .enrichment import GraphEnrichmentService
class GraphEnrichmentService:
 def __init__(self,repository=None): self.repository=repository or SecurityGraphRepository(); self.query=GraphQueryEngine(self.repository); self.enricher=__import__('services.security_graph.enrichment',fromlist=['GraphEnrichmentService']).GraphEnrichmentService(self.query)
 def enrich_investigation(self,entity_id,tenant_id=None): return self.enricher.enrich(entity_id,tenant_id)
 def posture(self,tenant_id=None): return {"total_entities":len(self.repository.list_entities(tenant_id)),"total_relationships":len(self.repository.get_relationships(tenant_id)),"active_campaign_links":sum(1 for r in self.repository.get_relationships(tenant_id) if r.relationship_type in {"uses","associated_with"}),"attack_paths_found":0,"enriched_investigations":0}

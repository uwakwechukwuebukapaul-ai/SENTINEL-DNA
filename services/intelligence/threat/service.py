from .models import ThreatIndicator, ThreatActor, ThreatCampaign
from .repository import ThreatRepository
from .enrichment import ThreatEnrichmentService
class ThreatIntelligenceService:
    def __init__(self, repository=None): self.repository = repository or ThreatRepository(); self.enrichment = ThreatEnrichmentService(self.repository)
    def create_indicator(self, organization_id, data): item = ThreatIndicator(organization_id, data["indicator_type"], data["value"], data.get("source", "analyst"), float(data.get("confidence", 0)), data.get("severity", "MEDIUM"), tags=data.get("tags", []), mitre_mapping=data.get("mitre_mapping", [])); self.repository.indicators[item.id] = item; return item
    def enrich(self, organization_id, value): return self.enrichment.enrich(organization_id, value)
    def actors(self, organization_id): return self.repository.actors_for(organization_id)
    def campaigns(self, organization_id): return self.repository.campaigns_for(organization_id)

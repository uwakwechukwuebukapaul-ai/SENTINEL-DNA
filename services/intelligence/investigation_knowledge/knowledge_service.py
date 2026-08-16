from .models import KnowledgeEvolution, stable_id
from .evolution_analysis import EvolutionAnalysis
class InvestigationKnowledgeService:
    def __init__(self, context_provider=None): self.context_provider=context_provider
    def derive(self, tenant_id, context=None):
        context=context or (self.context_provider(tenant_id) if self.context_provider else {}); a=EvolutionAnalysis().analyze(context)
        return KnowledgeEvolution(stable_id(tenant_id,"investigation-knowledge"),tenant_id,a["maturity"],a["trends"],("associated patterns are advisory",),tuple(context.get("provenance",())),a["confidence"],a["maturity"],True).to_dict()

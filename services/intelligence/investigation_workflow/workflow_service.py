from .models import WorkflowInsight, stable_id
from .workflow_analysis import WorkflowAnalysis
class InvestigationWorkflowService:
    def __init__(self, context_provider=None): self.context_provider=context_provider
    def derive(self, tenant_id, context=None):
        context=context or (self.context_provider(tenant_id) if self.context_provider else {}); a=WorkflowAnalysis().analyze(context)
        return WorkflowInsight(stable_id(tenant_id,"investigation-workflow"),tenant_id,a["transitions"],a["complexity"],("consider process review",),a["confidence"],tuple(context.get("provenance",())),a["confidence"],True).to_dict()

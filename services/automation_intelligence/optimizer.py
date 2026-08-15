from uuid import uuid4
from .models import PlaybookRecommendation
class PlaybookOptimizer:
    def recommend(self, tenant_id, workflow_id, performance):
        if performance.execution_count < 2: return []
        if performance.success_rate < .5: return [PlaybookRecommendation(str(uuid4()),tenant_id,workflow_id,"effectiveness","Historical simulations have a low success rate.","Review sequencing and target selection before proposing playbook changes.",performance.confidence)]
        if performance.approval_rate < .5: return [PlaybookRecommendation(str(uuid4()),tenant_id,workflow_id,"approval","Analysts frequently reject this workflow.","Review rationale, risk classification, and approval evidence with an analyst.",performance.confidence)]
        return [PlaybookRecommendation(str(uuid4()),tenant_id,workflow_id,"optimization","Workflow outcomes are consistently positive.","Consider documenting the successful pattern for human-reviewed playbook improvement.",performance.confidence)]

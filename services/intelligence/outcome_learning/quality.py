from .models import QualityAssessment
class QualityEvaluator:
    def evaluate(self,outcome,evaluator):
        x=evaluator.quality(outcome); return QualityAssessment(outcome.tenant_id,outcome.outcome_id,**x,provenance=outcome.provenance)

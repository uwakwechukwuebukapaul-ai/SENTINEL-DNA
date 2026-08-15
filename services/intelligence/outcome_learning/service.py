from .repository import OutcomeLearningRepository
from .outcomes import OutcomeEvaluator
from .quality import QualityEvaluator
from .patterns import PatternAnalyzer
from .improvements import ImprovementGenerator
class OutcomeLearningService:
    def __init__(self,repository=None,audit=None): self.repository=repository or OutcomeLearningRepository(); self.audit=audit; self.outcomes=OutcomeEvaluator(); self.quality=QualityEvaluator(); self.patterns=PatternAnalyzer(); self.improvements=ImprovementGenerator()
    def _audit(self,event,**data):
        if self.audit and hasattr(self.audit,"record"): self.audit.record(event,**data)
    def record_outcome(self,outcome): self.repository.save_outcome(outcome); self._audit("outcome_recorded",tenant_id=outcome.tenant_id,outcome_id=outcome.outcome_id); return outcome
    def evaluate_outcome_quality(self,tenant_id,outcome_id):
        outcome=next((x for x in self.repository.list_outcomes(tenant_id) if x.outcome_id==outcome_id),None); return self.repository.save_quality(self.quality.evaluate(outcome,self.outcomes)) if outcome else None
    def evaluate_resolution(self,tenant_id,outcome_id):
        outcome=next((x for x in self.repository.list_outcomes(tenant_id) if x.outcome_id==outcome_id),None); return self.outcomes.resolution(outcome) if outcome else "UNKNOWN"
    def analyze_patterns(self,tenant_id):
        items=self.patterns.analyze(tenant_id,self.repository.list_outcomes(tenant_id)); self.repository.save_patterns(items); return items
    def generate_improvement_candidates(self,tenant_id):
        patterns=self.analyze_patterns(tenant_id); items=self.improvements.generate(tenant_id,self.repository.list_outcomes(tenant_id),patterns); self.repository.save_improvements(items); return items
    def get_historical_outcomes(self,tenant_id): return self.repository.list_outcomes(tenant_id)
    def get_quality_history(self,tenant_id): return self.repository.list_quality(tenant_id)
    def get_improvement_candidates(self,tenant_id): return self.repository.list_improvements(tenant_id)

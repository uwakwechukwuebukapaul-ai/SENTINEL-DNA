from .repository import GovernanceDecisionRepository
from .signals import GovernanceSignalBuilder
from .prioritizer import DecisionPrioritizer
from .rationale import DecisionRationale
from .dependencies import DependencyAnalyzer
from .models import DecisionCandidate, ReviewState, DecisionProvenance
class GovernanceDecisionService:
    def __init__(self,repository=None,audit=None): self.repository=repository or GovernanceDecisionRepository(); self.audit=audit; self.signals=GovernanceSignalBuilder(); self.prioritizer=DecisionPrioritizer(); self.rationale=DecisionRationale(); self.dependencies=DependencyAnalyzer()
    def _audit(self,event,**payload):
        if self.audit and hasattr(self.audit,"record"): self.audit.record(event,**payload)
    def generate_signals(self,tenant_id,inputs): return self.signals.build(tenant_id,inputs)
    def generate_candidates(self,tenant_id,signals):
        deps=self.dependencies.analyze(signals); result=[]
        for signal in signals:
            priority=self.prioritizer.priority(signal); related=[x.to_dict() for x in deps if x.from_signal==signal.category or x.to_signal==signal.category]
            item=DecisionCandidate(tenant_id,signal.category,priority,signal.severity,rationale=self.rationale.build(signal,priority),confidence=signal.confidence,evidence_references=signal.evidence_references,source_references=signal.source_references,affected_controls=signal.affected_controls,affected_assets=signal.affected_assets,dependencies=related,provenance=signal.provenance+[DecisionProvenance("governance_decision",signal.category,"deterministic advisory prioritization")]); self.repository.save(item); result.append(item)
        self._audit("governance_decisions_generated",tenant_id=tenant_id,count=len(result)); return sorted(result,key=lambda x:(-self.prioritizer.weights.get(x.priority,0),x.category))
    def decision_queue(self,tenant_id,status=None): self._audit("governance_decisions_retrieved",tenant_id=tenant_id); return self.repository.list(tenant_id,status)
    def historical_decisions(self,tenant_id): return self.repository.list(tenant_id)
    def record_review(self,tenant_id,decision_id,state,reviewer="",note=""):
        if state not in {"pending_review","reviewed","deferred","dismissed","accepted_for_action"}: raise ValueError("invalid review state")
        decision=self.repository.get(tenant_id,decision_id)
        if decision is None: return None
        decision.status=state; review=self.repository.save_review(ReviewState(decision_id,tenant_id,state,reviewer,note)); self._audit("governance_decision_reviewed",tenant_id=tenant_id,decision_id=decision_id,state=state); return review
    def advisory_recommendations(self,tenant_id): return [x for x in self.decision_queue(tenant_id) if x.requires_human_review]

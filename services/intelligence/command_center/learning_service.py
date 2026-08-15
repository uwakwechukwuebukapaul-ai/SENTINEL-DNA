from .learning import AnalystInvestigationLearning, stable_learning_id
LOW_CONFIDENCE_THRESHOLD=.7
LEARNING_PRIORITY={"repeated_disagreement":0,"evidence_gap":1,"unresolved_pattern":2,"human_review_pattern":3,"low_confidence_pattern":4,"uncertainty_pattern":5,"quality_degradation":6,"positive_quality_pattern":7,"insufficient_data":8}
class AnalystInvestigationLearningService:
    def __init__(self, quality_intelligence_service=None): self.quality_intelligence_service=quality_intelligence_service
    def derive(self, tenant_id):
        intelligence=self.quality_intelligence_service.derive(tenant_id) if self.quality_intelligence_service else None
        if not intelligence: return []
        base=dict(tenant_id=tenant_id,investigation_count=intelligence.investigation_count,feedback_count=intelligence.feedback_count,quality_signal_count=intelligence.quality_signal_count,confidence=intelligence.average_confidence,uncertainty=list(intelligence.uncertainty),provenance=dict(intelligence.provenance),contributing_feedback_ids=list(intelligence.contributing_feedback_ids),contributing_investigation_ids=list(intelligence.contributing_investigation_ids),contributing_attention_ids=[],human_review_required=True)
        items=[]
        def add(kind,title,description,severity,focus,extra_uncertainty=()):
            payload=dict(base)
            payload["uncertainty"]=list(dict.fromkeys(base["uncertainty"]+list(extra_uncertainty)))
            payload.update(learning_id=stable_learning_id(tenant_id,kind),learning_type=kind,title=title,description=description,severity=severity,recommended_analyst_focus=focus)
            items.append(AnalystInvestigationLearning(**payload))
        if intelligence.feedback_count==0: add("insufficient_data","Insufficient investigation-quality data","No analyst feedback is available to identify a recurring quality pattern.","medium","collect structured analyst assessments",("insufficient_data",))
        else:
            if intelligence.disagreement_count and intelligence.investigation_count>=2: add("repeated_disagreement","Repeated analyst disagreement","Disagreement recurs across investigation-quality observations.","high","inspect disagreement-producing investigations")
            if intelligence.evidence_insufficient_count and intelligence.investigation_count>=2: add("evidence_gap","Recurring evidence gaps","Evidence insufficiency recurs across investigations.","high","review evidence collection completeness")
            if intelligence.unresolved_count and intelligence.investigation_count>=2: add("unresolved_pattern","Recurring unresolved investigations","Unresolved quality signals recur across investigations.","high","prioritize unresolved investigations for human review")
            if intelligence.human_review_count and intelligence.investigation_count>=2: add("human_review_pattern","Recurring human-review requirement","Human review is repeatedly required by quality signals.","medium","review recurring human-review cases")
            if intelligence.average_confidence is not None and intelligence.average_confidence<LOW_CONFIDENCE_THRESHOLD: add("low_confidence_pattern","Recurring low confidence","Aggregate confidence remains below the documented threshold.","medium","examine investigations with consistently low confidence",("low_confidence",))
            if intelligence.uncertainty: add("uncertainty_pattern","Recurring uncertainty","Quality intelligence contains recurring uncertainty.","medium","review cases with persistent uncertainty")
            if intelligence.trend_direction=="degrading": add("quality_degradation","Quality degradation","The existing quality trend indicates degradation.","high","review degrading quality signals")
        if not items and intelligence.agreement_count==intelligence.feedback_count and intelligence.investigation_count>=2 and not intelligence.uncertainty:
            add("positive_quality_pattern","Consistent supported quality","Available feedback shows consistent agreement without unresolved uncertainty.","low","preserve evidence-backed investigation practices")
        return sorted(items,key=lambda x:(LEARNING_PRIORITY.get(x.learning_type,99),0 if x.severity=="high" else 1 if x.severity=="medium" else 2,x.learning_id))

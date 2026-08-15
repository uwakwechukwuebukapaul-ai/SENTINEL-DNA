from hashlib import sha256
from .quality_intelligence import AnalystQualityIntelligence, QualityAttentionItem
class AnalystQualityIntelligenceService:
    def __init__(self, trend_service=None): self.trend_service=trend_service
    def _item(self, category, priority, reason, trend, uncertainty=None):
        ident=sha256(f"{trend.tenant_id}|{category}".encode()).hexdigest()[:24]
        return QualityAttentionItem(ident,category,priority,reason,list(trend.contributing_investigation_ids or trend.contributing_feedback_ids),trend.provenance,trend.average_confidence,uncertainty or trend.uncertainty,True)
    def derive(self, tenant_id):
        trend=self.trend_service.trend(tenant_id) if self.trend_service else None
        if not trend: return None
        items=[]
        if trend.feedback_count==0: items.append(self._item("insufficient_data","medium","No analyst feedback is available.",trend,["analyst_feedback_unavailable"]))
        if trend.disagreement_count: items.append(self._item("repeated_disagreement","high","Analyst disagreement requires review.",trend,["analyst_disagreement"]))
        if trend.evidence_insufficient_count: items.append(self._item("evidence_insufficiency","high","Evidence insufficiency is recurring.",trend,["evidence_insufficient"]))
        if trend.unresolved_investigation_count: items.append(self._item("unresolved_investigations","high","Unresolved quality signals require review.",trend,["quality_unresolved"]))
        if trend.human_review_required_count: items.append(self._item("human_review_required","medium","Human review remains required.",trend,["human_review_required"]))
        items=sorted(items,key=lambda x:(0 if x.priority=="high" else 1,x.category,x.attention_id))
        state="insufficient_data" if trend.feedback_count==0 else "recurring_concerns" if items else "adequate"
        return AnalystQualityIntelligence(tenant_id,state,trend.trend_direction,trend.investigation_count,trend.feedback_count,trend.quality_signal_count,trend.agreement_count,trend.disagreement_count,trend.unresolved_investigation_count,trend.human_review_required_count,trend.evidence_insufficient_count,trend.average_confidence,list(trend.uncertainty),items,trend.provenance,list(trend.contributing_feedback_ids),list(trend.contributing_investigation_ids),True)

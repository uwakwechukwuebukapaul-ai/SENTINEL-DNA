from services.intelligence.command_center.feedback_service import InvestigationFeedbackService
from services.intelligence.command_center.quality_trend_service import AnalystQualityTrendService
from types import SimpleNamespace
class W:
    def build(self, tenant, investigation): return SimpleNamespace(tenant_id=tenant, investigation={"investigation_id":investigation}, evidence=[], decision={}, events=[], uncertainty="", requires_human_review=True, provenance={"source":"workspace"}) if tenant=="a" else None
class O:
    def derive(self, ws): return SimpleNamespace(outcome_id="out-"+ws.investigation["investigation_id"])
def service(): return InvestigationFeedbackService(W(),O())
def test_empty_trend_is_explicit_and_deterministic():
    feedback=service(); trend=AnalystQualityTrendService(feedback).trend("a"); assert trend.to_dict()==AnalystQualityTrendService(feedback).trend("a").to_dict() and trend.trend_direction=="insufficient_data" and trend.feedback_count==0
def test_trend_aggregates_feedback_and_is_tenant_scoped():
    feedback=service(); feedback.submit("a","i1",{"outcome_agreement":"agree","evidence_sufficiency":"sufficient","recommendation_usefulness":"useful","confidence":.8}); feedback.submit("a","i2",{"outcome_agreement":"disagree","evidence_sufficiency":"insufficient","recommendation_usefulness":"not_useful","confidence":.4})
    trend=AnalystQualityTrendService(feedback).trend("a"); assert trend.investigation_count==2 and trend.agreement_count==1 and trend.disagreement_count==1 and trend.evidence_insufficient_count==1 and trend.trend_direction=="needs_review" and AnalystQualityTrendService(feedback).trend("b").feedback_count==0

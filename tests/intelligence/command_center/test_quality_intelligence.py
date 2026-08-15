from types import SimpleNamespace
from services.intelligence.command_center.quality_intelligence_service import AnalystQualityIntelligenceService
class T:
    def __init__(self, **kw):
        defaults={"tenant_id":"a","trend_direction":"needs_review","investigation_count":2,"feedback_count":2,"quality_signal_count":2,"agreement_count":0,"disagreement_count":2,"unresolved_investigation_count":1,"human_review_required_count":1,"evidence_insufficient_count":1,"average_confidence":.5,"uncertainty":["conflicting_feedback"],"provenance":{"source":"trend"},"contributing_feedback_ids":["f1","f2"],"contributing_investigation_ids":["i1","i2"]}
        defaults.update(kw); self.__dict__.update(defaults)
class S:
    def __init__(self, trend): self.value=trend
    def trend(self, tenant): return self.value
def test_quality_intelligence_is_deterministic_and_preserves_sources():
    result=AnalystQualityIntelligenceService(S(T())).derive("a"); again=AnalystQualityIntelligenceService(S(T())).derive("a")
    assert result.to_dict()==again.to_dict() and result.state=="recurring_concerns" and result.contributing_feedback_ids==["f1","f2"] and result.attention[0].category=="evidence_insufficiency"
def test_empty_quality_data_is_explicit_and_tenant_scoped():
    result=AnalystQualityIntelligenceService(S(T(feedback_count=0,investigation_count=0,quality_signal_count=0,disagreement_count=0,unresolved_investigation_count=0,human_review_required_count=0,evidence_insufficient_count=0,contributing_feedback_ids=[],contributing_investigation_ids=[]))).derive("a")
    assert result.state=="insufficient_data" and result.attention[0].category=="insufficient_data" and result.advisory_only

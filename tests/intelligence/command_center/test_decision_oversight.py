from services.intelligence.command_center.decision_oversight import DecisionOversight
from services.intelligence.command_center.decision_oversight_service import DecisionOversightService
from services.intelligence.command_center.forecast_policy_review_service import ForecastPolicyReviewService

class G:
    def derive(self, tenant_id): return {'governance_status':'insufficient_evidence','uncertainty':['insufficient_history'],'provenance':[]}

def test_oversight_never_fabricates_decisions():
    result=DecisionOversightService(ForecastPolicyReviewService(G())).derive('tenant-a')
    oversight=result['decision_oversight']
    assert oversight['decision_history_status']=='insufficient_decision_history'
    assert result['advisory_only'] is True
    assert oversight['tenant_id']=='tenant-a'

def test_oversight_model_is_immutable_and_deterministic():
    assert DecisionOversight.__dataclass_params__.frozen
    service=DecisionOversightService(ForecastPolicyReviewService(G()))
    assert service.derive('a')==service.derive('a')

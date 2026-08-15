import pytest
from services.intelligence.command_center.forecast_policy_review import ForecastPolicyReview
from services.intelligence.command_center.forecast_policy_review_service import ForecastPolicyReviewService

class G:
    def __init__(self, value): self.value=value
    def derive(self, tenant_id): return dict(self.value, tenant_id=tenant_id)

def test_policy_review_is_deterministic_and_blocks_missing_history():
    value={'governance_status':'insufficient_evidence','uncertainty':['insufficient_history']}
    a=ForecastPolicyReviewService(G(value)).derive('a'); b=ForecastPolicyReviewService(G(value)).derive('a')
    assert a==b and a['policy_review']['policy_readiness']=='insufficient_history'
    assert a['advisory_only'] is True

def test_policy_review_immutable_and_tenant_scoped():
    assert ForecastPolicyReview.__dataclass_params__.frozen
    value={'governance_status':'healthy','provenance':['forecast_governance'],'confidence':'high','evidence_strength':'strong'}
    a=ForecastPolicyReviewService(G(value)).derive('a')['policy_review']
    assert ForecastPolicyReviewService(G(value)).detail('b',a['review_id']) is None

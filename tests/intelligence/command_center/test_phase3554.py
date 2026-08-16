from dataclasses import FrozenInstanceError
import pytest
from services.intelligence.command_center.executive_intelligence_operating_model_service import ExecutiveIntelligenceOperatingModelService
from services.intelligence.command_center.strategic_portfolio_governance_service import StrategicPortfolioGovernanceService
from services.intelligence.command_center.organizational_ai_maturity_service import OrganizationalAIMaturityService
from services.intelligence.command_center.intelligence_adoption_analytics_service import IntelligenceAdoptionAnalyticsService
from services.intelligence.command_center.executive_governance_summary_service import ExecutiveGovernanceSummaryService
from services.intelligence.command_center.executive_intelligence_operating_model import ExecutiveIntelligenceOperatingModel

def test_phase3554_compositions_are_deterministic_and_advisory():
    services=[ExecutiveIntelligenceOperatingModelService(None,None,None,None,None,None),StrategicPortfolioGovernanceService(None,None,None),OrganizationalAIMaturityService(None,None,None,None),IntelligenceAdoptionAnalyticsService(None,None,None,None),ExecutiveGovernanceSummaryService(None,None,None,None)]
    keys=["operating_model","governance","maturity","adoption","summary"]
    for service,key in zip(services,keys):
        a=service.derive("tenant")[key]; b=service.derive("tenant")[key]
        id_key=next(k for k in a if k.endswith("_id")); assert a[id_key]==b[id_key]; assert a["advisory_only"] is True
    with pytest.raises(FrozenInstanceError): ExecutiveIntelligenceOperatingModel("t","i").intelligence_operating_posture="x"

def test_phase3554_insufficient_states_and_noncausal_boundaries():
    operating=ExecutiveIntelligenceOperatingModelService(None,None,None,None,None,None).derive("t")["operating_model"]
    maturity=OrganizationalAIMaturityService(None,None,None,None).derive("t")["maturity"]
    adoption=IntelligenceAdoptionAnalyticsService(None,None,None,None).derive("t")["adoption"]
    assert operating["governance_readiness"]=="insufficient_evidence"
    assert maturity["intelligence_capability_maturity"]=="insufficient_history"
    assert adoption["adoption_readiness"]=="insufficient_evidence"
    assert adoption["advisory_only"] is True

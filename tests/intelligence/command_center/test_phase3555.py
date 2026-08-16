from dataclasses import FrozenInstanceError
import pytest
from services.intelligence.command_center.executive_intelligence_governance_platform_service import ExecutiveIntelligenceGovernancePlatformService
from services.intelligence.command_center.strategic_decision_lifecycle_service import StrategicDecisionLifecycleService
from services.intelligence.command_center.organizational_intelligence_evolution_service import OrganizationalIntelligenceEvolutionService
from services.intelligence.command_center.intelligence_feedback_loop_service import IntelligenceFeedbackLoopService
from services.intelligence.command_center.executive_intelligence_evolution_summary_service import ExecutiveIntelligenceEvolutionSummaryService
from services.intelligence.command_center.executive_intelligence_governance_platform import ExecutiveIntelligenceGovernancePlatform

def test_phase3555_composition_ids_and_advisory_boundaries():
    services=[ExecutiveIntelligenceGovernancePlatformService(None,None,None),StrategicDecisionLifecycleService(None,None,None),OrganizationalIntelligenceEvolutionService(None,None,None,None),IntelligenceFeedbackLoopService(None,None,None,None),ExecutiveIntelligenceEvolutionSummaryService(None,None,None,None)]
    keys=["platform","lifecycle","evolution","feedback","summary"]
    for s,k in zip(services,keys):
        a=s.derive("tenant")[k]; b=s.derive("tenant")[k]; ident=next(x for x in a if x.endswith("_id")); assert a[ident]==b[ident]; assert a["advisory_only"] is True
    with pytest.raises(FrozenInstanceError): ExecutiveIntelligenceGovernancePlatform("t","i").governance_platform_posture="x"

def test_phase3555_insufficient_history_and_noncausal_language():
    p=ExecutiveIntelligenceGovernancePlatformService(None,None,None).derive("t")["platform"]
    l=StrategicDecisionLifecycleService(None,None,None).derive("t")["lifecycle"]
    e=OrganizationalIntelligenceEvolutionService(None,None,None,None).derive("t")["evolution"]
    assert p["governance_platform_posture"]=="insufficient_history"; assert l["evidence_readiness"]=="insufficient_evidence"; assert "causal" in e["maturity_movement_interpretation"]

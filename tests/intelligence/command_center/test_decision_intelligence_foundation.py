from services.intelligence.command_center.decision_intelligence_foundation_service import DecisionIntelligenceFoundationService
def test_decision_foundation_does_not_make_decisions():
    v=DecisionIntelligenceFoundationService(None,None).derive('t')['foundation']; assert v['evidence_to_decision_traceability']=='insufficient_evidence'; assert v['advisory_only'] is True

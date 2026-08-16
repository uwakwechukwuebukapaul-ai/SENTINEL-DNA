from services.intelligence.command_center.governance_intelligence_foundation_service import GovernanceIntelligenceFoundationService
def test_governance_foundation_is_advisory_and_requires_human_oversight():
    v=GovernanceIntelligenceFoundationService(None,None).derive('t')['foundation']; assert v['automation_readiness']=='insufficient_evidence'; assert 'human_review_required' in v['human_oversight_requirements']; assert v['advisory_only']

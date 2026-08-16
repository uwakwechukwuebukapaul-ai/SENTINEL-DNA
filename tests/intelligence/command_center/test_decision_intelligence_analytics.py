from services.intelligence.command_center.decision_intelligence_analytics_service import DecisionIntelligenceAnalyticsService
def test_decision_analytics_preserves_insufficient_evidence():
    v=DecisionIntelligenceAnalyticsService(None,None).derive('t')['analytics']; assert v['evidence_completeness_monitoring']=='insufficient_evidence'; assert v['advisory_only'] is True

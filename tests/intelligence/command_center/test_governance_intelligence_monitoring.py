from services.intelligence.command_center.governance_intelligence_monitoring_service import GovernanceIntelligenceMonitoringService
def test_governance_monitoring_is_advisory_and_non_enforcing():
    v=GovernanceIntelligenceMonitoringService(None,None).derive('t')['monitoring']; assert v['governance_signal_monitoring']=='insufficient_history'; assert 'no_policy_enforcement' in v['oversight_requirement_tracking']; assert v['advisory_only']

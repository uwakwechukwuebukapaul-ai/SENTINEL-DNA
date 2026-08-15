from services.intelligence.command_center.escalation_monitoring_service import EscalationMonitoringService
def test_monitoring_preserves_empty_history(): assert EscalationMonitoringService().derive('a')['monitoring']['escalation_trend']=='insufficient_history'

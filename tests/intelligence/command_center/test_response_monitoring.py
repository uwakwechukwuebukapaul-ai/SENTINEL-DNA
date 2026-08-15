from services.intelligence.command_center.response_monitoring_service import ResponseMonitoringService
def test_response_monitoring_preserves_insufficient_history(): assert ResponseMonitoringService().derive('a')['monitoring']['trend']=='insufficient_history'

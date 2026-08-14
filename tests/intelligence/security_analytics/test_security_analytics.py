from services.intelligence.security_analytics import SecurityAnalyticsRepository, SecurityAnalyticsService
from services.intelligence.investigation.investigation_result import InvestigationResult

def test_trend_calculation():
    service=SecurityAnalyticsService("a"); service.record_snapshot({"posture": 70}); service.record_snapshot({"posture": 80}); assert service.analyze_trends()[0].direction == "improving"

def test_anomaly_detection():
    service=SecurityAnalyticsService("a"); service.record_snapshot({"alerts": 10}); service.record_snapshot({"alerts": 10}); service.record_snapshot({"alerts": 30}); assert service.detect_anomalies()[0].metric == "alerts"

def test_forecast_generation():
    service=SecurityAnalyticsService("a"); service.record_snapshot({"posture": 80}); service.record_snapshot({"posture": 60}); assert service.generate_forecast().risk_direction == "increasing_risk"

def test_tenant_isolation():
    repository=SecurityAnalyticsRepository(); SecurityAnalyticsService("a", repository).record_snapshot({"posture": 70}); assert SecurityAnalyticsService("b", repository).analyze_trends() == []

def test_backward_compatibility():
    result=InvestigationResult(); assert result.security_analytics_context is None and "security_analytics_context" in result.to_dict()

from services.platform_observability import PlatformObservabilityService
def test_metrics_health_and_tenant_isolation():
    s=PlatformObservabilityService(); s.record_metric("t1","gateway","errors","error_rate",.6); s.record_metric("t1","gateway","latency","duration",20); h=s.check_health("t1","gateway"); assert h.status=="unhealthy"; assert s.repository.list_metrics("t2")==[]; assert s.generate_recommendations("t1")[0]["requires_human_review"]
def test_invalid_metric_type_and_snapshot():
    s=PlatformObservabilityService();
    try: s.record_metric("t","x","m","bad",1)
    except ValueError: pass
    else: assert False
    assert s.snapshot("empty")["aggregation"]["metric_count"]==0

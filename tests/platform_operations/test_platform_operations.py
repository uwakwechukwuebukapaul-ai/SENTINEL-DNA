from services.platform_operations import PlatformOperationsService
def test_operations_analysis_and_tenant_isolation():
    s=PlatformOperationsService(); s.record_workload("t1",investigations=2,alerts=3); s.record_capacity("t1","correlation",utilization=.9,error_rate=.1,throughput=10); result=s.analyze("t1"); assert result["summary"]["total_workload"]==5; assert s.generate_findings("t1")[0].requires_human_review; assert s.analyze("t2")["summary"]["workload_snapshots"]==0
def test_forecast_is_deterministic():
    s=PlatformOperationsService(); s.record_capacity("t","api",utilization=.2); s.record_capacity("t","api",utilization=.4); assert s.forecast("t","api")["direction"]=="increasing"

from lab.customer_zero.runner import CustomerZeroRunner
from services.customer_zero.reporting import CustomerZeroReportService
from services.customer_zero.replay import ReplayEngine
def test_report_generation_and_score():
    result = CustomerZeroRunner().run(); report = CustomerZeroReportService().generate("customer-zero-finance", result); assert report.security_score == 97; assert CustomerZeroReportService().executive(report)["security_improvement_score"] == "97%"
def test_replay_is_chronological():
    events = ReplayEngine().generate({"scenario": "Credential Attack", "detections": []}); assert [x.timestamp for x in events] == ["09:01", "09:03", "09:04", "09:05", "09:06"]
def test_report_tenant_identity():
    result = CustomerZeroReportService().generate("org-a", {"scenario": "x", "metrics": {"overall_score": 1}}); assert result.organization_id == "org-a"

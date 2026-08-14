from .models import CustomerZeroReport
from .executive_report import build as executive_build
from .analyst_report import build as analyst_build
class CustomerZeroReportService:
    def generate(self, organization_id, result):
        report = CustomerZeroReport(organization_id, result.get("scenario", "unknown"), result.get("telemetry", []), result.get("detections", []), result.get("investigations", []), result.get("mitre_techniques", []), result.get("ai_analysis", result.get("investigations", [])), result.get("response", {}), result.get("metrics", {}), float(result.get("metrics", {}).get("overall_score", 0))); return report
    def executive(self, report): return executive_build(report)
    def analyst(self, report, timeline=None): return analyst_build(report, timeline)

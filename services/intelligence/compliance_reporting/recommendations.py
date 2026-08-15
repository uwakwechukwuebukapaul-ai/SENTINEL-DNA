from .models import Recommendation
class RecommendationBuilder:
    def build(self,tenant_id,report,trend=None):
        items=[]
        for cid in report.non_compliant_controls+report.insufficient_evidence_controls+report.unknown_controls: items.append(Recommendation(category="control_governance",priority="high" if cid in report.non_compliant_controls else "medium",rationale=f"Observed governance gap for control {cid}.",evidence_references=report.evidence_references,source_references=[report.report_id]))
        if trend and trend.direction=="deteriorating": items.append(Recommendation(category="trend",priority="high",rationale="Observed historical posture deterioration.",source_references=[report.report_id]))
        return items

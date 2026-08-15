from .models import ExecutiveComplianceSummary, Provenance
class ExecutiveReportBuilder:
    def build(self,tenant_id,report,trend=None,business_impact_references=None):
        weaknesses=report.non_compliant_controls+report.unknown_controls+report.insufficient_evidence_controls
        return ExecutiveComplianceSummary(tenant_id,"attention_required" if weaknesses or report.audit_readiness<.8 else "observed_stable",major_weaknesses=weaknesses,significant_gaps=report.unresolved_gap_summary,evidence_readiness=report.evidence_coverage,audit_readiness=report.audit_readiness,major_trends=[trend.to_dict() if hasattr(trend,"to_dict") else trend] if trend else [],recurring_issues=(trend.recurring_gaps if trend else []),business_impact_references=business_impact_references or [],recommended_priorities=["review deteriorating or insufficient-evidence controls"] if weaknesses else [],provenance=[Provenance("compliance_reporting","", "deterministic aggregation of observed report fields")])

from services.intelligence.compliance_governance import Control
from services.intelligence.compliance_monitoring import ComplianceMonitoringService
from services.intelligence.compliance_reporting import ComplianceReportingService
from services.intelligence.investigation.investigation_result import InvestigationResult

def setup_data():
    monitoring=ComplianceMonitoringService(); controls=[Control("c1","f","t","One",status="failed"),Control("c2","f","t","Two",status="implemented")]; readiness=monitoring.audit_readiness("t","f",controls); report=ComplianceReportingService().generate_governance_report("t","f",controls,readiness,[]); return controls,readiness,report
def test_reporting_tenant_isolation_and_generation():
    controls,readiness,report=setup_data(); service=ComplianceReportingService(); service.repository.save_report(report); assert service.historical_reports("other")==[] and report.advisory and not report.certification_claim
def test_executive_control_evidence_trend_and_recommendations():
    controls,readiness,report=setup_data(); service=ComplianceReportingService(); controls_out=service.generate_control_reports("t","f",controls,[],readiness,[]); summary=service.generate_executive_summary("t",report); trend=service.generate_trend_summary("t","f",[]); recommendations=service.generate_recommendations("t",report,trend); evidence=service.generate_evidence_summary("t","f",[],controls,readiness); assert len(controls_out)==2 and summary.audit_readiness==report.audit_readiness and trend.direction=="insufficient_history" and evidence.missing==["c1","c2"] and recommendations[0].requires_human_review
def test_investigation_result_compatibility(): assert InvestigationResult().to_dict()["compliance_monitoring_context"] is None

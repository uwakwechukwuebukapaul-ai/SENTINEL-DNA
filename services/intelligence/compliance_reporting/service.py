from .repository import ComplianceReportingRepository
from .report import GovernanceReportBuilder
from .executive import ExecutiveReportBuilder
from .controls import ControlReportBuilder
from .evidence import EvidenceReportBuilder
from .trends import TrendReportBuilder
from .recommendations import RecommendationBuilder
class ComplianceReportingService:
    def __init__(self,repository=None,audit=None): self.repository=repository or ComplianceReportingRepository(); self.audit=audit; self.reporter=GovernanceReportBuilder(); self.executive=ExecutiveReportBuilder(); self.controls=ControlReportBuilder(); self.evidence=EvidenceReportBuilder(); self.trends=TrendReportBuilder(); self.recommender=RecommendationBuilder()
    def _audit(self,event,**data):
        if self.audit and hasattr(self.audit,"record"): self.audit.record(event,**data)
    def generate_governance_report(self,tenant_id,framework_id,controls,readiness,drifts,period=None,executive_risk_references=None):
        x=self.reporter.build(tenant_id,framework_id,controls,readiness,drifts,period,executive_risk_references); self.repository.save_report(x); self._audit("compliance_governance_report_generated",tenant_id=tenant_id,report_id=x.report_id); return x
    def generate_executive_summary(self,tenant_id,report,trend=None,business_impact_references=None):
        x=self.executive.build(tenant_id,report,trend,business_impact_references); self.repository.save_executive(x); self._audit("compliance_executive_summary_generated",tenant_id=tenant_id); return x
    def generate_control_reports(self,tenant_id,framework_id,controls,drifts=None,readiness=None,history=None):
        xs=self.controls.build(tenant_id,framework_id,controls,drifts,readiness,history); [self.repository.save_control(x) for x in xs]; return xs
    def generate_evidence_summary(self,tenant_id,framework_id,evidence,controls,readiness): return self.evidence.build(tenant_id,framework_id,evidence,controls,readiness)
    def generate_trend_summary(self,tenant_id,framework_id,snapshots,gaps=None):
        x=self.trends.build(tenant_id,framework_id,snapshots,gaps); self.repository.save_trend(x); return x
    def generate_recommendations(self,tenant_id,report,trend=None):
        xs=self.recommender.build(tenant_id,report,trend); [self.repository.save_recommendation(x,tenant_id) for x in xs]; self._audit("compliance_recommendations_generated",tenant_id=tenant_id); return xs
    def historical_reports(self,tenant_id): return self.repository.list_reports(tenant_id)

from .repository import ComplianceGovernanceRepository
from .controls import ControlAnalyzer
from .assessment import AssessmentEngine
from .coverage import CoverageEngine
from .gaps import GapEngine
class ComplianceGovernanceService:
    def __init__(self,repository=None,audit=None): self.repository=repository or ComplianceGovernanceRepository(); self.controls=ControlAnalyzer(); self.assessments=AssessmentEngine(); self.coverage=CoverageEngine(); self.gaps=GapEngine(); self.audit=audit
    def register_framework(self,x): return self.repository.save_framework(x)
    def register_control(self,x): return self.repository.save_control(x)
    def assess(self,tenant_id,framework_id):
        controls=self.repository.list_controls(framework_id,tenant_id); result=self.assessments.assess(tenant_id,framework_id,controls,self.controls); self.repository.save_assessment(result); return result
    def coverage_score(self,tenant_id,framework_id): return self.coverage.calculate(self.repository.list_controls(framework_id,tenant_id))
    def identify_gaps(self,tenant_id,framework_id):
        result=self.gaps.find(tenant_id,framework_id,self.repository.list_controls(framework_id,tenant_id),self.controls)
        for x in result:self.repository.save_gap(x)
        return result

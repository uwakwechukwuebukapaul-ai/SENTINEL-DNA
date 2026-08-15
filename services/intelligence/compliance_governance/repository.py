class ComplianceGovernanceRepository:
    def __init__(self): self.frameworks={}; self.controls={}; self.requirements={}; self.assessments={}; self.gaps={}
    def save_framework(self,x): self.frameworks[(x.tenant_id,x.framework_id)]=x; return x
    def get_framework(self,i,t): return self.frameworks.get((t,i))
    def save_control(self,x): self.controls[(x.tenant_id,x.control_id)]=x; return x
    def list_controls(self,framework_id,t): return [x for (tenant,_),x in self.controls.items() if tenant==t and x.framework_id==framework_id]
    def save_requirement(self,x): self.requirements[(x.tenant_id,x.requirement_id)]=x; return x
    def save_assessment(self,x): self.assessments[(x.tenant_id,x.assessment_id)]=x; return x
    def save_gap(self,x): self.gaps[(x.tenant_id,x.gap_id)]=x; return x
    def list_gaps(self,t,framework_id=None): return [x for (tenant,_),x in self.gaps.items() if tenant==t and (framework_id is None or x.framework_id==framework_id)]

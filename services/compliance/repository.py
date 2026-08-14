class ComplianceRepository:
    def __init__(self): self.assessments={}
    def create_assessment(self,a): self.assessments[a.assessment_id]=a; return a
    def get_assessment(self,i): return self.assessments.get(i)
    def list_assessments(self,tenant_id=None): return [a for a in self.assessments.values() if tenant_id is None or a.tenant_id==tenant_id]
    def update_assessment(self,i,**changes): a=self.assessments[i]; [setattr(a,k,v) for k,v in changes.items() if hasattr(a,k)]; return a

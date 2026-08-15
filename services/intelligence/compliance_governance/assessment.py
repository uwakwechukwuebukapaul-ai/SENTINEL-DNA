from uuid import uuid4
from .models import ComplianceAssessment
class AssessmentEngine:
    def assess(self,tenant_id,framework_id,controls,analyzer):
        total=len(controls); compliant=sum(analyzer.evaluate(x) for x in controls); score=round(compliant/total*100,2) if total else 0.0; return ComplianceAssessment(str(uuid4()),tenant_id,framework_id,score,"compliant" if score>=80 else "partial" if score else "non_compliant",total,compliant)

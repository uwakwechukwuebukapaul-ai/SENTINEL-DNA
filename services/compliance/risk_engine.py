from .models import SecurityRiskScore
class RiskEngine:
 def calculate(self,tenant_id,active_incidents=0,threat_score=0,detection_coverage=100,governance_violations=0,compliance_gaps=0):
  score=round(min(100,active_incidents*10+threat_score*.3+(100-detection_coverage)*.3+governance_violations*10+compliance_gaps*8)); return SecurityRiskScore(tenant_id,score,"low" if score<=30 else "medium" if score<=70 else "high",["compliance gaps"] if compliance_gaps else [],["Prioritize control remediation"] if score>70 else [])

from .models import RiskScore
class EntityRiskEngine:
    def calculate(self, organization_id, entity_id, signals=None, behavior_deviation=0, threat_intelligence=0, exposure=0, history=0, privilege=0):
        signals=signals or []; score=min(100, behavior_deviation+threat_intelligence+exposure+history+privilege); severity="CRITICAL" if score>=85 else "HIGH" if score>=65 else "MEDIUM" if score>=35 else "LOW"; return RiskScore(organization_id,entity_id,score,severity,signals)

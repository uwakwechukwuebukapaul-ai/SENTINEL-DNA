from .models import SecurityDomainScore, SecurityPostureScore

class SecurityPostureScoringEngine:
    DOMAINS=("detection_coverage", "vulnerability_exposure", "attack_surface_risk", "compliance_posture", "incident_trends", "response_capability")
    def calculate(self, tenant_id, signals=None):
        signals=signals or {}; domains=[SecurityDomainScore(domain, max(0,min(100,float(signals.get(domain, 0)))), 1/len(self.DOMAINS), "strong" if float(signals.get(domain,0)) >= 80 else "developing") for domain in self.DOMAINS]; overall=round(sum(item.score*item.weight for item in domains),2); return SecurityPostureScore(tenant_id, overall, domains, [item.domain for item in domains if item.score < 70])

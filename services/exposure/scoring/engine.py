from dataclasses import asdict, dataclass, field

@dataclass
class ExposureRisk:
    score: float; severity: str; vulnerability_id: str; asset_id: str; factors: dict = field(default_factory=dict)
    def public(self): return asdict(self)

class ExposureRiskEngine:
    def calculate(self, vulnerability, asset, threat_correlation=None, active_exploitation=False, business_impact=0, exposure_history=0):
        criticality = {"LOW": 0.55, "MEDIUM": 0.75, "HIGH": 0.9, "CRITICAL": 1.0}.get(str(asset.criticality).upper(), .75)
        score = min(100.0, vulnerability.cvss_score * 10 * criticality + (18 if active_exploitation else 0) + min(10, business_impact) + min(5, exposure_history) + (8 if threat_correlation else 0))
        severity = "CRITICAL" if score >= 85 else "HIGH" if score >= 65 else "MEDIUM" if score >= 35 else "LOW"
        return ExposureRisk(round(score, 2), severity, vulnerability.id, asset.id, {"cvss": vulnerability.cvss_score, "asset_criticality": asset.criticality, "active_exploitation": bool(active_exploitation), "threat_correlation": bool(threat_correlation)})

from .models import RemediationRecommendation, RiskPriority, SecurityExposure

class ExposurePrioritizer:
    def prioritize(self, exposures: list[SecurityExposure]):
        ordered=sorted(exposures, key=lambda item: (item.score, item.business_impact in {"critical", "high"}), reverse=True); return [RiskPriority(item.exposure_id, index, "P1" if item.severity == "critical" or item.business_impact == "critical" else "P2" if item.severity == "high" or item.business_impact == "high" else "P3", f"{item.severity} exposure with {item.business_impact} business impact") for index, item in enumerate(ordered, 1)]
    def recommendations(self, exposures):
        result=[]
        for item in exposures:
            action="review critical asset exposure and reachable attack paths" if item.severity in {"critical", "high"} else "review vulnerability and control coverage"
            result.append(RemediationRecommendation(item.exposure_id, action, "Prioritized from correlated exposure factors"))
        return result

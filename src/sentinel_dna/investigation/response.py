"""Safe, recommendation-only response automation foundation."""
from typing import Any


class ResponseRecommendationEngine:
    def recommend(self, context: Any) -> list[dict[str, str]]:
        suspicious = context.intelligence.get("threat", {}).get("suspicious_iocs", [])
        recommendations = [{"action": f"Block indicator: {indicator}", "approval": "required",
                            "reason": "High-confidence suspicious indicator relationship detected.",
                            "safety": "recommendation_only"} for indicator in suspicious]
        if context.threat_classification.get("classification") == "phishing":
            recommendations.append({"action": "Reset or protect potentially affected identities", "approval": "required",
                                    "reason": "Credential-phishing indicators were mapped to MITRE ATT&CK.",
                                    "safety": "recommendation_only"})
        return recommendations

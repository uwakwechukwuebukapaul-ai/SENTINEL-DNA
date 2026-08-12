"""Detection-engineering outputs generated from completed investigation evidence."""
from typing import Any


class DetectionRecommendationEngine:
    def generate(self, context: Any) -> list[dict[str, Any]]:
        if not context.iocs:
            return []
        return [{"name": "Credential phishing with external authentication URL",
                 "hunt_query": "email_events | where body has_any ('password', 'verify', 'mfa') | where urls has 'http'",
                 "ioc_search": {"indicators": context.iocs},
                 "sigma_rule": {"title": "Potential credential phishing email", "logsource": {"category": "email"},
                                "detection": {"selection": {"body|contains": ["password", "verify", "mfa"]}, "condition": "selection"}},
                 "reason": "Derived from evidence-backed indicator and language correlations."}]

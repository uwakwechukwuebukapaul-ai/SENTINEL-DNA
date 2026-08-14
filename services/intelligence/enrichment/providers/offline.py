from __future__ import annotations
from ..models import EnrichmentResult, Indicator
from .base import EnrichmentProvider

class OfflineEnrichmentProvider(EnrichmentProvider):
    name = "offline"
    _known = {
        ("ip", "203.0.113.50"): (75, ["synthetic", "suspicious-network"], "Synthetic suspicious IP observed"),
        ("domain", "example.invalid"): (70, ["synthetic", "suspicious-domain"], "Synthetic suspicious domain observed"),
        ("url", "https://example.invalid/login"): (70, ["synthetic", "phishing"], "Synthetic phishing URL observed"),
        ("hash", "synthetic-malware-hash"): (90, ["synthetic", "malware"], "Synthetic malware hash observed"),
        ("email", "analyst@example.invalid"): (60, ["synthetic", "phishing"], "Synthetic phishing sender observed"),
    }

    def lookup(self, indicator: Indicator):
        item = self._known.get((indicator.type.lower(), indicator.value.lower()))
        return None if item is None else {"risk_score": item[0], "tags": item[1], "finding": item[2]}

    def enrich(self, indicator: Indicator) -> EnrichmentResult:
        item = self.lookup(indicator) or {"risk_score": 0, "tags": ["unobserved"], "finding": "No offline intelligence match"}
        return EnrichmentResult(indicator, item["risk_score"], max(indicator.confidence, 0.85 if item["risk_score"] else 0.2), item["tags"], [item["finding"]])

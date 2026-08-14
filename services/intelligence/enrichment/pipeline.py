from __future__ import annotations
import re
from typing import Any
from .models import Indicator, EnrichmentResult
from .providers.base import EnrichmentProvider
from .providers.offline import OfflineEnrichmentProvider

class EnrichmentPipeline:
    def __init__(self, provider: EnrichmentProvider | None = None):
        self.provider = provider or OfflineEnrichmentProvider()

    def enrich(self, artifacts: list[dict[str, Any]] | None) -> list[EnrichmentResult]:
        results = []
        for artifact in artifacts or []:
            indicator = self._indicator(artifact)
            if indicator:
                results.append(self.provider.enrich(indicator))
        return results

    @staticmethod
    def _indicator(artifact: dict[str, Any]) -> Indicator | None:
        value = str(artifact.get("value") or artifact.get("data") or "").strip()
        if not value:
            return None
        kind = str(artifact.get("type") or "unknown").lower()
        if "ip" in kind or re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", value): kind = "ip"
        elif "url" in kind or value.startswith("http"): kind = "url"
        elif "email" in kind or "@" in value: kind = "email"
        elif "hash" in kind: kind = "hash"
        elif "domain" in kind: kind = "domain"
        else: kind = "domain" if "." in value else "unknown"
        return Indicator(value, kind, "offline", float(artifact.get("confidence", 0) or 0))

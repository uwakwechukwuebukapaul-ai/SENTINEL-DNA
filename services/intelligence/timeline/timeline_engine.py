"""Investigation timeline generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .timeline_models import InvestigationTimelineEvent


class InvestigationTimelineEngine:
    """Build a chronological, JSON-ready investigation timeline."""

    @staticmethod
    def _timestamp(index: int) -> str:
        return datetime.fromtimestamp(index, timezone.utc).isoformat()

    def generate(self, intelligence: dict[str, Any], alert: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        iocs = intelligence.get("iocs", []) or []
        techniques = intelligence.get("mitre_techniques", []) or []
        findings = [str(item) for item in intelligence.get("findings", []) or []]
        recommendations = intelligence.get("recommendations", []) or []
        severity = intelligence.get("risk_severity", "info")
        events = [
            InvestigationTimelineEvent(self._timestamp(1), "alert_received", "alert_ingestion", "Alert received", severity, iocs),
        ]
        if any("authentication" in item.lower() or "failed" in item.lower() for item in findings):
            events.append(InvestigationTimelineEvent(self._timestamp(2), "authentication_failure", "evidence_analysis", "Authentication failures detected", severity, iocs))
        if any("external ip" in item.lower() or "indicator" in item.lower() for item in findings):
            events.append(InvestigationTimelineEvent(self._timestamp(3), "suspicious_ioc", "ioc_enrichment", "Suspicious external IP identified", severity, iocs))
        for technique in techniques:
            events.append(InvestigationTimelineEvent(self._timestamp(4), "mitre_mapping", "mitre_mapping", f"MITRE {technique} mapped", severity, iocs, [technique]))
        if recommendations:
            events.append(InvestigationTimelineEvent(self._timestamp(5), "recommendation", "recommendations", "Recommended response generated", severity, iocs, techniques, {"recommendations": recommendations}))
        return [event.to_dict() for event in sorted(events, key=lambda item: item.timestamp)]

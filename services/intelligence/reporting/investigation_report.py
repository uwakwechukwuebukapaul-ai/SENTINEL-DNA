"""Generate analyst-ready reports from normalized intelligence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .report_models import InvestigationReport
from services.observability import ObservabilityService
import time


class InvestigationReportGenerator:
    """Materialize a stable report without changing execution contracts."""

    def generate(
        self,
        case_id: str,
        intelligence: Any,
        alert: dict[str, Any] | None = None,
        timeline: list[Any] | None = None,
    ) -> InvestigationReport:
        started = time.perf_counter()
        observer = ObservabilityService()
        data = intelligence.to_dict() if hasattr(intelligence, "to_dict") else dict(intelligence or {})
        alert = alert or {}
        findings = list(data.get("findings", []) or [])
        recommendations = list(data.get("recommendations", []) or [])
        risk = {
            "score": data.get("risk_score", 0),
            "severity": data.get("risk_severity", "unknown"),
        }
        title = str(alert.get("title") or f"Investigation report for {case_id}")
        severity = str(alert.get("severity") or risk["severity"] or "unknown").lower()
        summary = self._summary(case_id, risk, findings, data.get("attack_story"))
        report = InvestigationReport(
            case_id=case_id,
            title=title,
            summary=summary,
            severity=severity,
            risk=risk,
            confidence=float(data.get("confidence", 0.0) or 0.0),
            findings=findings,
            recommendations=recommendations,
            timeline=list(timeline if timeline is not None else data.get("timeline", []) or []),
            mitre=list(data.get("mitre_techniques", []) or []),
            attack_story=data.get("attack_story"),
            iocs=list(data.get("iocs", []) or []),
            evidence_summary=data.get("evidence_summary", {}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        observer.event("REPORT_GENERATED", case_id=case_id, status="completed", duration_ms=round((time.perf_counter()-started)*1000, 2))
        return report

    @staticmethod
    def _summary(case_id: str, risk: dict[str, Any], findings: list[Any], attack_story: Any) -> str:
        if attack_story:
            return str(attack_story)
        return (
            f"Investigation {case_id} completed with "
            f"{risk['severity']} risk (score {risk['score']}) and "
            f"{len(findings)} finding(s)."
        )

"""Provision one explicit, synthetic investigation target per tenant.

The scenario is deliberately persisted through the canonical investigation
repositories. It is not external threat intelligence and never crosses a
tenant boundary. Production deployments keep it disabled unless explicitly
enabled by configuration.
"""

from __future__ import annotations

import hashlib
from typing import Any

from services.intelligence.models.investigation_intelligence import InvestigationIntelligence


class AnalystDemoScenarioService:
    """Idempotently provision the analyst's synthetic investigation target."""

    def __init__(self, intelligence_repository: Any, report_repository: Any) -> None:
        self.intelligence_repository = intelligence_repository
        self.report_repository = report_repository

    @staticmethod
    def case_id_for_tenant(tenant_id: str) -> str:
        digest = hashlib.sha256(str(tenant_id).encode("utf-8")).hexdigest()[:12].upper()
        return f"DEMO-PS-{digest}"

    def ensure_for_tenant(self, tenant_id: str) -> dict[str, Any]:
        tenant_id = str(tenant_id or "").strip()
        if not tenant_id:
            raise ValueError("tenant_id is required")

        case_id = self.case_id_for_tenant(tenant_id)
        existing = self.report_repository.get_by_case_id_for_tenant(case_id, tenant_id)
        if existing:
            return existing

        evidence = [
            {"evidence_id": f"{case_id}-E1", "case_id": case_id, "tenant_id": tenant_id, "type": "process", "source": "synthetic_endpoint_telemetry", "observed_at": "2026-01-15T12:00:00Z", "value": "powershell.exe -EncodedCommand <redacted-demo-payload>", "provenance": {"source": "synthetic_demo", "synthetic": True}},
            {"evidence_id": f"{case_id}-E2", "case_id": case_id, "tenant_id": tenant_id, "type": "process_relationship", "source": "synthetic_endpoint_telemetry", "observed_at": "2026-01-15T12:00:03Z", "value": "winword.exe -> powershell.exe", "provenance": {"source": "synthetic_demo", "synthetic": True}},
            {"evidence_id": f"{case_id}-E3", "case_id": case_id, "tenant_id": tenant_id, "type": "network_connection", "source": "synthetic_proxy_telemetry", "observed_at": "2026-01-15T12:01:10Z", "value": "https://updates.example.invalid/payload.bin", "provenance": {"source": "synthetic_demo", "synthetic": True}},
        ]
        iocs = [{"ioc_id": f"{case_id}-I1", "case_id": case_id, "tenant_id": tenant_id, "type": "domain", "value": "updates.example.invalid", "intelligence_status": "not_queried", "provider": None, "confidence": None, "freshness": None, "provenance": {"source": "synthetic_demo", "synthetic": True}}]
        timeline = [
            {"event_id": f"{case_id}-T1", "case_id": case_id, "tenant_id": tenant_id, "event_type": "alert", "description": "Synthetic endpoint alert created for analyst demonstration.", "timestamp": "2026-01-15T12:00:00Z", "provenance": {"source": "synthetic_demo", "synthetic": True}},
            {"event_id": f"{case_id}-T2", "case_id": case_id, "tenant_id": tenant_id, "event_type": "process_observed", "description": "PowerShell launched by a document process.", "timestamp": "2026-01-15T12:00:03Z", "provenance": {"source": "synthetic_demo", "synthetic": True}},
            {"event_id": f"{case_id}-T3", "case_id": case_id, "tenant_id": tenant_id, "event_type": "network_observed", "description": "The process attempted an outbound connection.", "timestamp": "2026-01-15T12:01:10Z", "provenance": {"source": "synthetic_demo", "synthetic": True}},
        ]
        metadata = {"tenant_id": tenant_id, "investigation_id": case_id, "synthetic": True, "scenario": "suspicious_powershell_execution", "evidence_limitations": ["Synthetic telemetry; no external provider lookup has been performed."]}
        report = {
            "case_id": case_id, "title": "Synthetic alert: suspicious PowerShell execution", "summary": "Synthetic analyst demonstration awaiting canonical investigation execution.", "severity": "high", "risk_score": 0, "risk": {"score": 0, "severity": "unknown", "basis": "Investigation has not run."}, "mitre": [], "findings": [], "recommendations": [], "status": "ready", "evidence": evidence, "timeline": timeline, "relationships": [], "reasoning": None, "confidence": 0, "uncertainty": "Investigation has not run; no conclusion is available.", "tenant_context": {"tenant_id": tenant_id}, "metadata": metadata, "created_at": "2026-01-15T12:00:00Z",
        }
        intelligence = InvestigationIntelligence(risk_score=0, risk_severity="unknown", confidence=0, iocs=iocs, evidence_summary={"count": len(evidence), "items": evidence}, timeline=timeline, metadata=metadata)
        self.intelligence_repository.save(case_id, intelligence)
        return self.report_repository.save(report)

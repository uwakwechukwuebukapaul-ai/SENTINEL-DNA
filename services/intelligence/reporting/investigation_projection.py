"""Versioned, evidence-backed product projection for AI Investigator V1."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


PROJECTION_VERSION = "investigation-projection-v1"


def _dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    if hasattr(value, "__dict__"):
        return {key: item for key, item in vars(value).items() if not key.startswith("_")}
    return {}


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


@dataclass
class InvestigationProjectionV1:
    version: str
    investigation_id: str
    case_id: str
    tenant_id: str | None
    alert_summary: dict[str, Any]
    evidence: list[dict[str, Any]]
    intelligence: dict[str, Any]
    findings: list[dict[str, Any]]
    reasoning: dict[str, Any]
    attack_mapping: list[dict[str, Any]]
    confidence: dict[str, Any]
    decision: dict[str, Any]
    analyst_actions: list[dict[str, Any]]
    provenance: dict[str, Any]
    unavailable_services: list[dict[str, Any]]
    execution_status: dict[str, Any]

    # Compatibility properties for existing callers and templates.
    @property
    def executive_summary(self) -> Any:
        return self.alert_summary.get("summary", "Unavailable")

    @property
    def severity(self) -> Any:
        return self.alert_summary.get("severity", "unknown")

    @property
    def risk(self) -> dict[str, Any]:
        return self.confidence.get("risk", {"score": 0, "severity": "unknown"})

    @property
    def evidence_summary(self) -> dict[str, Any]:
        return {"count": len(self.evidence), "items": self.evidence}

    @property
    def ioc_intelligence(self) -> list[Any]:
        return list(self.intelligence.get("observations", []) or [])

    @property
    def mitre_mappings(self) -> list[dict[str, Any]]:
        return self.attack_mapping

    @property
    def ai_reasoning(self) -> Any:
        return self.reasoning or "Unavailable"

    @property
    def recommendations(self) -> list[dict[str, Any]]:
        return self.analyst_actions

    @property
    def relationships(self) -> list[Any]:
        return list(self.intelligence.get("relationships", []) or [])

    @property
    def data_classification(self) -> str:
        return "synthetic_demo" if self.provenance.get("synthetic") else "production_observed"

    @property
    def timeline(self) -> list[Any]:
        return list(self.intelligence.get("timeline", []) or [])

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # Keep legacy consumers functional while making the versioned fields
        # authoritative for new workspace/report consumers.
        data.update({
            "executive_summary": self.executive_summary,
            "severity": self.severity,
            "risk": self.risk,
            "confidence_score": self.confidence.get("score"),
            "evidence_summary": self.evidence_summary,
            "ioc_intelligence": self.ioc_intelligence,
            "mitre_mappings": self.mitre_mappings,
            "ai_reasoning": self.ai_reasoning,
            "recommendations": self.recommendations,
            "relationships": self.relationships,
            "data_classification": self.data_classification,
            "timeline": self.timeline,
        })
        return data


class InvestigationProjectionBuilder:
    """Build one tenant-scoped, explicit-availability investigation view."""

    _TECHNIQUE_NAMES = {
        "T1059": "Command and Scripting Interpreter",
        "T1059.001": "PowerShell",
        "T1110": "Brute Force",
        "T1566": "Phishing",
        "T1566.002": "Phishing: Spearphishing Link",
    }

    def build(
        self,
        result: Any,
        *,
        alert: Mapping[str, Any] | None = None,
        tenant_id: str | None = None,
    ) -> InvestigationProjectionV1:
        data = _dict(result)
        report = _dict(data.get("report"))
        normalized = _dict(data.get("intelligence")).get("normalized")
        normalized = _dict(normalized)
        if not normalized and report:
            normalized = report
        execution = _dict(data.get("execution"))
        evidence = self._evidence(data, normalized, report)
        evidence_ids = [item["evidence_id"] for item in evidence]

        findings = [self._trace(item, evidence_ids, "finding") for item in _list(data.get("findings") or normalized.get("findings"))]
        reasoning = _dict(data.get("reasoning_report") or data.get("reasoning"))
        reasoning_findings = [self._trace(item, evidence_ids, "reasoning_claim") for item in _list(reasoning.get("findings"))]
        if reasoning_findings:
            reasoning["findings"] = reasoning_findings
        if not reasoning:
            reasoning = self._unavailable("reasoning", "No reasoning report was generated")

        intelligence_status = _dict(normalized.get("metadata")).get("intelligence_status")
        intelligence_status = _dict(intelligence_status)
        observations = list(intelligence_status.get("observations", []) or [])
        intelligence = {
            "observations": [self._intelligence_observation(item, evidence_ids) for item in observations],
            "provider_results": list(intelligence_status.get("provider_results", []) or []),
            "status": intelligence_status.get("disposition", "unavailable"),
            "provenance": _dict(intelligence_status.get("intelligence_provenance")),
            "timeline": list(normalized.get("timeline", []) or []),
            "provider_health": list(intelligence_status.get("provider_health", []) or []),
        }
        unavailable = list(intelligence_status.get("unavailable_providers", []) or [])
        if not observations:
            unavailable.append("No provider observation was available")

        techniques = _list(data.get("mitre") or normalized.get("mitre_techniques") or report.get("mitre"))
        attack_mapping = [self._technique(item, evidence_ids, findings, reasoning) for item in techniques]

        risk = data.get("risk") if isinstance(data.get("risk"), dict) else {"value": data.get("risk", "unknown")}
        score = risk.get("score", normalized.get("risk_score", 0))
        confidence_score = data.get("confidence", normalized.get("confidence", 0))
        try:
            confidence_score = float(confidence_score or 0)
        except (TypeError, ValueError):
            confidence_score = 0.0
        if confidence_score > 1:
            confidence_score /= 100
        confidence = {
            "score": round(confidence_score, 4),
            "basis": "evidence-backed" if evidence_ids else "unavailable",
            "evidence_ids": evidence_ids,
            "risk": {**risk, "score": score},
        }

        decision = _dict(data.get("decision_report"))
        if decision:
            decision["evidence_ids"] = list(decision.get("evidence_ids") or evidence_ids)
        else:
            decision = self._unavailable("decision", "No decision report was generated")
        actions = []
        for action in _list(decision.get("recommended_actions") or data.get("recommendations")):
            actions.append(self._trace({"action": action} if not isinstance(action, dict) else action, evidence_ids, "analyst_action"))

        errors = list(execution.get("errors", []) or [])
        unavailable_services = [{"service": "threat_intelligence", "status": "Unavailable", "reason": "No provider observation was available", "provenance": intelligence.get("provenance", {})}] if not observations else []
        unavailable_services.extend({"service": "threat_intelligence_provider", "status": "Unavailable", "reason": item.get("unavailable_reason") or item.get("reason") or "Provider did not return an observation", "provenance": {"provider": item.get("provider"), "timestamp": item.get("timestamp")}} for item in intelligence.get("provider_health", []) if item.get("status") == "UNAVAILABLE")
        unavailable_services.extend({"service": "runtime", "reason": item.get("error", "Unavailable"), "provenance": {"capability": item.get("capability")}} for item in errors if item.get("status") in {"unavailable", "blocked"})
        alert_data = dict(alert or report.get("alert_summary") or {})
        if not alert_data:
            alert_data = {"summary": report.get("summary", "Unavailable"), "severity": report.get("severity", normalized.get("risk_severity", "unknown"))}
        provenance = {
            "tenant_id": tenant_id or _dict(data.get("tenant_context")).get("tenant_id") or _dict(report.get("tenant_context")).get("tenant_id"),
            "evidence_ids": evidence_ids,
            "intelligence": intelligence.get("provenance", {}),
            "synthetic": bool(_dict(normalized.get("metadata")).get("synthetic")),
        }
        execution_status = {
            "status": execution.get("status", data.get("status", "unknown")),
            "execution_id": execution.get("execution_id") or data.get("execution_id"),
            "created_at": execution.get("created_at"),
            "queued_at": execution.get("queued_at"),
            "correlation_id": execution.get("correlation_id"),
            "state_history": list(execution.get("state_history", []) or []),
            "tasks": list(execution.get("tasks", []) or []),
            "errors": errors,
            "task_summary": {
                "total": len(execution.get("tasks", []) or []),
                "successful": sum(1 for item in execution.get("tasks", []) or [] if item.get("execution_state", item.get("execution_status", "")).upper() == "SUCCESS"),
                "failed": sum(1 for item in execution.get("tasks", []) or [] if item.get("execution_state", item.get("execution_status", "")).upper() == "FAILED"),
                "unavailable": sum(1 for item in execution.get("tasks", []) or [] if item.get("execution_state", item.get("execution_status", "")).upper() == "UNAVAILABLE"),
                "blocked": sum(1 for item in execution.get("tasks", []) or [] if item.get("execution_state", item.get("execution_status", "")).upper() == "BLOCKED"),
            },
            "evidence_collection": {"status": "SUCCESS" if evidence_ids else "UNAVAILABLE", "evidence_count": len(evidence_ids), "evidence_ids": evidence_ids},
            "reasoning": {"status": "SUCCESS" if reasoning and reasoning.get("findings") is not None else "UNAVAILABLE", "evidence_ids": evidence_ids},
            "provider_health": intelligence.get("provider_health", []),
        }
        return InvestigationProjectionV1(
            version=PROJECTION_VERSION,
            investigation_id=str(data.get("investigation_id") or data.get("case_id") or report.get("case_id") or "unknown"),
            case_id=str(data.get("case_id") or report.get("case_id") or "unknown"),
            tenant_id=provenance["tenant_id"],
            alert_summary=alert_data,
            evidence=evidence,
            intelligence=intelligence,
            findings=findings,
            reasoning=reasoning,
            attack_mapping=attack_mapping,
            confidence=confidence,
            decision=decision,
            analyst_actions=actions,
            provenance=provenance,
            unavailable_services=unavailable_services,
            execution_status=execution_status,
        )

    def build_from_read_model(self, view: Any, *, tenant_id: str) -> InvestigationProjectionV1:
        data = _dict(view)
        investigation = _dict(data.get("investigation"))
        report = _dict(data.get("report"))
        intelligence = _dict(data.get("intelligence"))
        return self.build({
            "investigation_id": investigation.get("id"),
            "case_id": investigation.get("case_id"),
            "tenant_context": {"tenant_id": tenant_id},
            "status": investigation.get("status"),
            "report": report,
            "intelligence": {"normalized": intelligence, **intelligence},
            "artifacts": report.get("evidence", []),
            "evidence": report.get("evidence", []),
            "findings": report.get("findings", []),
            "mitre": report.get("mitre", []),
            "reasoning_report": report.get("reasoning"),
            "decision_report": report.get("decision_report"),
            "execution": data.get("execution") or {"status": investigation.get("status", "unknown")},
        }, tenant_id=tenant_id)

    @staticmethod
    def _evidence(data: dict[str, Any], normalized: dict[str, Any], report: dict[str, Any]) -> list[dict[str, Any]]:
        values = data.get("evidence") or data.get("artifacts") or report.get("evidence") or (normalized.get("evidence_summary") or {}).get("items")
        result = []
        for index, item in enumerate(_list(values)):
            value = dict(item) if isinstance(item, dict) else {"value": item}
            value.setdefault("evidence_id", f"EVD-LEGACY-{index + 1}")
            value.setdefault("provenance", {"source": value.get("source", "unknown")})
            result.append(value)
        return result

    @staticmethod
    def _trace(item: Any, evidence_ids: list[str], kind: str) -> dict[str, Any]:
        value = dict(item) if isinstance(item, dict) else {"value": item}
        refs = list(value.get("evidence_refs") or value.get("evidence_ids") or [])
        value["evidence_refs"] = [ref for ref in refs if ref in evidence_ids] or list(evidence_ids)
        value["traceability_status"] = "attached" if value["evidence_refs"] else "unavailable"
        value.setdefault("reasoning_explanation", f"{kind.replace('_', ' ').title()} derived from canonical investigation evidence.")
        return value

    def _technique(self, item: Any, evidence_ids: list[str], findings: list[dict[str, Any]], reasoning: dict[str, Any]) -> dict[str, Any]:
        if isinstance(item, dict):
            technique_id = str(item.get("technique_id") or item.get("id") or item.get("technique") or "unknown")
            name = item.get("name") or self._TECHNIQUE_NAMES.get(technique_id, "Technique name unavailable")
        else:
            technique_id = str(item)
            name = self._TECHNIQUE_NAMES.get(technique_id, "Technique name unavailable")
        refs = sorted({ref for finding in findings for ref in finding.get("evidence_refs", [])}) or list(evidence_ids)
        return {"technique_id": technique_id, "technique_name": name, "supporting_evidence_ids": refs, "confidence": reasoning.get("confidence", 0) if reasoning else 0, "reasoning_explanation": "Technique mapped from evidence-backed investigation reasoning."}

    @staticmethod
    def _intelligence_observation(item: Any, evidence_ids: list[str]) -> dict[str, Any]:
        value = dict(item) if isinstance(item, dict) else {"value": item}
        value.setdefault("status", "available")
        value.setdefault("timestamp", value.get("retrieved_at", "Unavailable"))
        value.setdefault("source", value.get("provider", "Unavailable"))
        value["evidence_ids"] = list(value.get("evidence_ids") or evidence_ids)
        return value

    @staticmethod
    def _unavailable(service: str, reason: str) -> dict[str, Any]:
        return {"status": "Unavailable", "service": service, "reason": reason, "provenance": {"source": "canonical_execution"}}


__all__ = ["InvestigationProjectionV1", "InvestigationProjectionBuilder", "PROJECTION_VERSION"]

"""Canonical analyst-facing investigation read model."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


_SENSITIVE_KEYS = {
    "password", "password_hash", "secret", "token", "access_token",
    "refresh_token", "api_key", "private_key", "credential",
    "authorization", "authorization_capability", "database_path",
    "internal_path", "connection_string",
}


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _clean(item)
            for key, item in value.items()
            if str(key).lower() not in _SENSITIVE_KEYS and not str(key).startswith("_")
        }
    if isinstance(value, (list, tuple, set)):
        return [_clean(item) for item in value]
    return value


def _items(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _sort(items: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: tuple(str(item.get(key, "")) for key in keys))


@dataclass(frozen=True)
class InvestigationReadModel:
    """Immutable snapshot assembled from canonical investigation boundaries."""

    investigation: dict[str, Any]
    summary: dict[str, Any]
    findings: tuple[dict[str, Any], ...]
    recommendations: tuple[dict[str, Any], ...]
    evidence: tuple[dict[str, Any], ...]
    artifacts: tuple[dict[str, Any], ...]
    iocs: tuple[dict[str, Any], ...]
    mitre: tuple[dict[str, Any], ...]
    timeline: tuple[dict[str, Any], ...]
    quality: dict[str, Any]
    feedback: tuple[dict[str, Any], ...]
    provider_observations: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return deepcopy({
            "investigation": self.investigation,
            "summary": self.summary,
            "findings": list(self.findings),
            "recommendations": list(self.recommendations),
            "evidence": list(self.evidence),
            "artifacts": list(self.artifacts),
            "iocs": list(self.iocs),
            "mitre": list(self.mitre),
            "timeline": list(self.timeline),
            "quality": self.quality,
            "feedback": list(self.feedback),
            "provider_observations": list(self.provider_observations),
        })


class InvestigationReadModelBuilder:
    """Build the authorized analyst view without becoming another source of truth."""

    def __init__(self, report_repository, intelligence_repository, quality_repository, feedback_repository):
        self.report_repository = report_repository
        self.intelligence_repository = intelligence_repository
        self.quality_repository = quality_repository
        self.feedback_repository = feedback_repository

    @staticmethod
    def _tenant(report: dict[str, Any], intelligence: dict[str, Any]) -> str | None:
        context = report.get("tenant_context") if isinstance(report, dict) else {}
        metadata = report.get("metadata") if isinstance(report, dict) else {}
        intelligence_metadata = intelligence.get("metadata") if isinstance(intelligence, dict) else {}
        return str((context or {}).get("tenant_id") or (metadata or {}).get("tenant_id") or (intelligence_metadata or {}).get("tenant_id") or "") or None

    @staticmethod
    def _finding(item: Any) -> dict[str, Any]:
        item = _clean(item)
        if not isinstance(item, dict):
            return {"finding": item, "evidence_refs": [], "provenance": {}}
        return {
            "finding_id": item.get("finding_id") or item.get("id"),
            "artifact_id": item.get("artifact_id"),
            "finding": item.get("finding") or item.get("title") or item.get("description") or item,
            "confidence": item.get("confidence", item.get("confidence_score")),
            "evidence_refs": sorted({str(ref) for ref in item.get("evidence_refs", item.get("evidence", [])) if ref}),
            "provenance": item.get("provenance", item.get("source", {})) or {},
            # Preserve classification metadata required by the explainability
            # projection; omitting it silently turns contradictions into
            # supporting factors.
            "contradiction": bool(item.get("contradiction")),
            "contradicting": bool(item.get("contradicting")),
            "is_contradiction": bool(item.get("is_contradiction")),
        }

    @staticmethod
    def _recommendation(item: Any) -> dict[str, Any]:
        item = _clean(item)
        if not isinstance(item, dict):
            return {"recommendation": item, "source": "investigation", "evidence_refs": []}
        return {
            "recommendation_id": item.get("recommendation_id") or item.get("id"),
            "recommendation": item.get("recommendation") or item.get("action") or item.get("description") or item,
            "source": item.get("source", "investigation"),
            "evidence_refs": sorted({str(ref) for ref in item.get("evidence_refs", []) if ref}),
        }

    @staticmethod
    def _ioc(item: Any) -> dict[str, Any]:
        item = _clean(item)
        if not isinstance(item, dict):
            return {"value": item, "ioc_type": "unknown", "provenance": {}}
        result = dict(item)
        result["ioc_id"] = result.get("ioc_id") or result.get("id")
        result["ioc_type"] = result.get("ioc_type") or result.get("type") or "unknown"
        result["provenance"] = result.get("provenance", result.get("source", {})) or {}
        result.pop("type", None)
        return result

    def build(self, case_id: str, tenant_id: str) -> InvestigationReadModel | None:
        report = self.report_repository.get_by_case_id(case_id) or {}
        intelligence = self.intelligence_repository.get_by_case_id(case_id) or {}
        if not report and not intelligence:
            return None
        owner = self._tenant(report, intelligence)
        if not tenant_id or owner != str(tenant_id):
            raise PermissionError("investigation_not_found")

        metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
        intelligence_metadata = intelligence.get("metadata") if isinstance(intelligence.get("metadata"), dict) else {}
        investigation_id = str(metadata.get("investigation_id") or intelligence_metadata.get("investigation_id") or report.get("investigation_id") or case_id)
        quality = self.quality_repository.get_assessment(str(tenant_id), investigation_id)
        quality_data = _clean(quality.to_dict()) if quality else _clean(report.get("quality_assessment") or intelligence_metadata.get("quality_assessment") or {})
        feedback = [
            _clean(item.to_dict()) for item in self.feedback_repository.list_for_investigation(str(tenant_id), investigation_id)
        ]
        for item in feedback:
            item.pop("tenant_id", None)
        feedback = _sort(feedback, ("created_at", "feedback_id"))

        source = {**intelligence, **report}
        findings = _sort([self._finding(item) for item in _items(source.get("findings"))], ("finding_id", "finding"))
        recommendations = _sort([self._recommendation(item) for item in _items(source.get("recommendations"))], ("recommendation_id", "recommendation"))
        evidence = _sort([_clean(item) if isinstance(_clean(item), dict) else {"value": _clean(item)} for item in _items(source.get("evidence"))], ("evidence_id", "id", "reference"))
        artifacts = _sort([_clean(item) if isinstance(_clean(item), dict) else {"value": _clean(item)} for item in _items(source.get("artifacts"))], ("artifact_id", "id", "type"))
        iocs = _sort([self._ioc(item) for item in _items(source.get("iocs"))], ("ioc_id", "value"))
        mitre = []
        for item in _items(source.get("mitre", source.get("mitre_techniques"))):
            clean = _clean(item)
            mitre.append(clean if isinstance(clean, dict) else {"technique_id": str(clean), "name": str(clean), "evidence_refs": []})
        mitre = _sort(mitre, ("technique_id", "name"))
        timeline = _sort([_clean(item) if isinstance(_clean(item), dict) else {"description": _clean(item)} for item in _items(source.get("timeline"))], ("timestamp", "event_id", "description"))

        risk = source.get("risk") if isinstance(source.get("risk"), dict) else {}
        raw_status = str(source.get("status", "created") or "created").lower()
        status = raw_status if raw_status in {"created", "running", "in_progress", "completed", "reviewed", "closed"} else "created"
        if feedback and status == "completed":
            status = "reviewed"
        investigation = _clean({"id": investigation_id, "case_id": str(case_id), "tenant_id": str(tenant_id), "status": status, "created_at": source.get("created_at") or metadata.get("created_at")})
        summary = _clean({"title": source.get("title", ""), "risk": risk.get("score", source.get("risk_score", 0)), "confidence": source.get("confidence", 0), "decision": source.get("decision") or source.get("intelligence_disposition", {}).get("decision") if isinstance(source.get("intelligence_disposition"), dict) else source.get("decision")})
        status_metadata = intelligence_metadata.get("intelligence_status") if isinstance(intelligence_metadata.get("intelligence_status"), dict) else {}
        observations = status_metadata.get("observations") or status_metadata.get("provider_results") or report.get("provider_observations") or []
        return InvestigationReadModel(investigation, summary, tuple(findings), tuple(recommendations), tuple(evidence), tuple(artifacts), tuple(iocs), tuple(mitre), tuple(timeline), quality_data, tuple(feedback), tuple(_clean(item) for item in observations if isinstance(item, dict)))

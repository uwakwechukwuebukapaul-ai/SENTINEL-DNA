"""Tenant-safe analyst experience projections.

This module is deliberately presentation-only. It consumes the canonical
investigation report and produces deterministic, allowlisted sections for the
Analyst Workspace. It does not create or mutate investigation state.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_SECRET_KEYS = {
    "api_key", "access_token", "refresh_token", "secret", "token",
    "password", "credentials", "provider_secret", "raw_provider_payload",
    "raw_provider_response", "prompt", "system_prompt", "hidden_prompt",
}
_PHASES = (
    ("initial_access", "Initial Access"),
    ("execution", "Execution"),
    ("persistence", "Persistence"),
    ("credential_access", "Credential Access"),
    ("lateral_movement", "Lateral Movement"),
    ("impact", "Impact"),
)


def _clean(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _clean(v) for k, v in value.items() if str(k).lower() not in _SECRET_KEYS}
    if isinstance(value, list):
        return [_clean(item) for item in value]
    if isinstance(value, tuple):
        return [_clean(item) for item in value]
    return value


def _owned(item: Any, tenant_id: str, case_id: str) -> bool:
    if not isinstance(item, Mapping):
        return True
    item_tenant = item.get("tenant_id")
    item_case = item.get("case_id")
    return (item_tenant in (None, "", tenant_id)) and (item_case in (None, "", case_id))


def _items(value: Any, tenant_id: str, case_id: str) -> list[Any]:
    if not isinstance(value, list):
        return []
    return [_clean(item) for item in value if _owned(item, tenant_id, case_id)]


def _confidence_level(value: Any) -> str:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return "Unavailable"
    if score >= 0.85:
        return "High"
    if score >= 0.60:
        return "Moderate"
    return "Low"


def _verdict(report: Mapping) -> dict[str, Any]:
    decision = report.get("decision") or report.get("decision_report") or {}
    decision = decision if isinstance(decision, Mapping) else {}
    raw = str(decision.get("verdict") or report.get("verdict") or "needs_review").lower()
    labels = {
        "true_positive": "TRUE POSITIVE",
        "false_positive": "FALSE POSITIVE",
        "suspicious": "SUSPICIOUS",
        "needs_review": "NEEDS REVIEW",
        "insufficient_evidence": "NEEDS REVIEW",
        "benign": "BENIGN",
    }
    confidence = decision.get("confidence", report.get("confidence"))
    evidence = decision.get("evidence_summary") or {}
    return {
        "value": raw,
        "label": labels.get(raw, "NEEDS REVIEW"),
        "severity": decision.get("severity") or report.get("severity") or "UNKNOWN",
        "confidence": confidence,
        "confidence_level": _confidence_level(confidence),
        "evidence_count": evidence.get("count", len(report.get("evidence", []) or [])),
        "uncertainty": report.get("uncertainty") or "Not recorded",
        "rationale": decision.get("rationale") or report.get("summary") or "Not recorded",
        "recommended_actions": _items(decision.get("recommended_actions"), "", ""),
    }


def _reasoning(report: Mapping, tenant_id: str, case_id: str) -> list[dict[str, Any]]:
    raw = report.get("reasoning") or report.get("reasoning_report") or {}
    raw = raw if isinstance(raw, Mapping) else {}
    findings = raw.get("findings") or report.get("findings") or []
    chain = []
    for finding in findings:
        if not isinstance(finding, Mapping) or not _owned(finding, tenant_id, case_id):
            continue
        evidence = finding.get("evidence_refs") or finding.get("evidence_references") or []
        chain.append({
            "observation": finding.get("title") or finding.get("observation") or "Observation recorded",
            "evidence": [str(ref) for ref in evidence if isinstance(ref, (str, int))],
            "reasoning": finding.get("reasoning") or finding.get("description") or raw.get("summary") or "Reasoning not recorded",
            "impact": finding.get("impact") or finding.get("severity") or "Unknown",
            "confidence": finding.get("confidence", raw.get("confidence")),
        })
    if not chain and raw.get("summary"):
        chain.append({"observation": "Investigation conclusion", "evidence": [], "reasoning": raw["summary"], "impact": "Unknown", "confidence": raw.get("confidence")})
    return _clean(chain)


def project_analyst_experience(
    report: Mapping[str, Any] | None,
    *,
    tenant_id: str,
    case_id: str,
    actor_id: str | None = None,
    correlation_id: str | None = None,
    provider_observations: list[Mapping[str, Any]] | None = None,
    feedback_history: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return the complete safe presentation contract for one investigation."""
    report = report if isinstance(report, Mapping) else {}
    tenant_id, case_id = str(tenant_id or ""), str(case_id or "")
    if not tenant_id or not case_id:
        return {}
    metadata = report.get("metadata") if isinstance(report.get("metadata"), Mapping) else {}
    alert = {
        "case_id": report.get("case_id") or case_id,
        "title": report.get("title") or "Security investigation",
        "summary": report.get("summary") or "No alert summary recorded.",
        "severity": report.get("severity") or (report.get("risk") or {}).get("severity", "UNKNOWN"),
        "status": report.get("status") or "UNKNOWN",
        "timestamp": report.get("created_at"),
        "indicators": _items(report.get("indicators") or report.get("iocs"), tenant_id, case_id),
        "affected_assets": _items(report.get("affected_assets"), tenant_id, case_id),
        "affected_users": _items(report.get("affected_users"), tenant_id, case_id),
    }
    evidence = _items(report.get("evidence") or report.get("artifacts"), tenant_id, case_id)
    intelligence = _clean(report.get("threat_intelligence") or {})
    observations = [_clean(item) for item in (provider_observations or []) if _owned(item, tenant_id, case_id)]
    attack_story = _clean(report.get("attack_story") or {})
    phase_values = {str(value).lower().replace(" ", "_") for value in (attack_story.get("phases", []) if isinstance(attack_story, Mapping) else [])}
    phases = [{"key": key, "label": label, "supported": key in phase_values} for key, label in _PHASES]
    mitre = _items(report.get("mitre"), tenant_id, case_id)
    return {
        "identity": {"tenant_id": tenant_id, "case_id": case_id, "actor_id": actor_id, "correlation_id": correlation_id or metadata.get("correlation_id")},
        "alert": _clean(alert),
        "investigation": {"status": report.get("status") or "UNKNOWN", "duration": metadata.get("duration_ms") or metadata.get("duration")},
        "evidence": evidence,
        "threat_intelligence": {"summary": intelligence, "observations": observations},
        "attack_reconstruction": {"summary": attack_story, "phases": phases, "timeline": _items(report.get("timeline"), tenant_id, case_id)},
        "mitre": mitre,
        "reasoning": _reasoning(report, tenant_id, case_id),
        "verdict": _verdict(report),
        "report": _clean(dict(report)),
        "analyst_decision": {"history": [_clean(item) for item in (feedback_history or []) if _owned(item, tenant_id, case_id)]},
    }


__all__ = ["project_analyst_experience"]

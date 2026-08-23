"""Authorized service boundary for immutable analyst outcome events."""

from __future__ import annotations

from typing import Any

from .analyst_feedback import AnalystFeedback

SENSITIVE_KEYS = {"token", "access_token", "refresh_token", "password", "secret", "credential", "authorization", "authorization_capability", "api_key", "private_key", "database_path"}

def _sanitize(value: Any):
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if str(key).lower() not in SENSITIVE_KEYS}
    if isinstance(value, (list, tuple, set)): return [_sanitize(item) for item in value]
    return value

class AnalystFeedbackService:
    """Create server-authored append-only analyst feedback."""
    def __init__(self, repository, audit_service=None): self.repository, self.audit_service = repository, audit_service
    def record(self, investigation_id: str, case_id: str, tenant_id: str, analyst_id: str, payload: dict[str, Any], report: dict[str, Any], previous_state: str | None = None) -> AnalystFeedback:
        if not tenant_id or not analyst_id: raise PermissionError("analyst_identity_required")
        if not isinstance(payload, dict): raise ValueError("malformed_payload")
        if set(payload) - {"decision", "disposition", "reason", "finding_id", "recommendation_id"}: raise ValueError("invalid_feedback_fields")
        requested_disposition = str(payload.get("disposition") or payload.get("decision") or "").strip().lower().replace(" ", "_")
        aliases = {"confirmed_threat": "accepted", "benign": "false_positive", "requires_review": "escalated", "false_positive": "false_positive", "closed": "accepted"}
        canonical_decision = aliases.get(requested_disposition, requested_disposition)
        report = report if isinstance(report, dict) else {}
        finding_id = payload.get("finding_id")
        if finding_id:
            valid = {str(item.get("finding_id")) for item in report.get("findings", []) or [] if isinstance(item, dict) and item.get("finding_id")}
            if str(finding_id) not in valid: raise ValueError("finding_not_found")
        recommendation_id = payload.get("recommendation_id")
        if recommendation_id:
            valid = {str(item.get("recommendation_id")) for item in report.get("recommendations", []) or [] if isinstance(item, dict) and item.get("recommendation_id")}
            if valid and str(recommendation_id) not in valid: raise ValueError("recommendation_not_found")
        evidence_refs, artifact_refs = set(), set()
        quality = report.get("quality_assessment") if isinstance(report.get("quality_assessment"), dict) else {}
        evidence_refs.update(str(item) for item in quality.get("evidence_refs", []) or [] if item)
        artifact_refs.update(str(item) for item in quality.get("artifact_refs", []) or [] if item)
        for item in report.get("evidence", report.get("artifacts", [])) or []:
            if isinstance(item, dict):
                evidence_refs.update(str(item[key]) for key in ("evidence_id", "reference", "id") if item.get(key))
                artifact_refs.update(str(item["artifact_id"]) for _ in (0,) if item.get("artifact_id"))
        feedback = AnalystFeedback(investigation_id=str(investigation_id), case_id=str(case_id), tenant_id=str(tenant_id), analyst_id=str(analyst_id), decision=canonical_decision, reason=payload.get("reason", ""), finding_id=str(finding_id) if finding_id else None, recommendation_id=str(recommendation_id) if recommendation_id else None, metadata=_sanitize({"source": "analyst_feedback_boundary", "disposition": requested_disposition, "previous_state": previous_state or "unassigned", "new_state": requested_disposition}), evidence_refs=sorted(evidence_refs), artifact_refs=sorted(artifact_refs))
        saved = self.repository.save(feedback)
        if self.audit_service is not None:
            self.audit_service.record("ANALYST_FEEDBACK_RECORDED", case_id=str(case_id), user_id=str(analyst_id), details={"investigation_id": str(investigation_id), "tenant_id": str(tenant_id), "decision": saved.decision})
        return saved

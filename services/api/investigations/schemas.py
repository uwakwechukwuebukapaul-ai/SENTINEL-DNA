"""Small request/response helpers for the investigation API."""

from __future__ import annotations

from typing import Any


def investigation_request(payload: Any) -> tuple[str | None, dict[str, Any], list[dict[str, Any]], str | None]:
    if not isinstance(payload, dict):
        return None, {}, [], "request_body_required"
    case_id = payload.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        return None, {}, [], "case_id_required"
    alert = payload.get("alert") or {}
    artifacts = payload.get("artifacts") or []
    if not isinstance(alert, dict) or not isinstance(artifacts, list):
        return None, {}, [], "alert_and_artifacts_must_be_objects"
    return case_id, alert, artifacts, None


def investigation_response(result: Any) -> dict[str, Any]:
    data = result.to_dict() if hasattr(result, "to_dict") else dict(result)
    return {
        "case_id": data.get("case_id"),
        "status": data.get("status"),
        "risk": data.get("risk"),
        "confidence": data.get("confidence"),
        "findings": data.get("findings", []),
        "recommendations": data.get("recommendations", []),
        "mitre": data.get("mitre", []),
        "attack_story": data.get("attack_story"),
    }

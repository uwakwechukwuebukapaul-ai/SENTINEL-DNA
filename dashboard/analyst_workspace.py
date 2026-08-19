"""Thin analyst-facing view over the canonical investigation repository."""
from __future__ import annotations
from flask import Blueprint, current_app, render_template
from services.core.security_context import authorize_investigation
from services.core.serialization import serialize

analyst_workspace = Blueprint("analyst_workspace", __name__, url_prefix="/workspace/analyst")

@analyst_workspace.get("/<case_id>")
def investigation_workspace(case_id: str):
    coordinator = current_app.container.require("investigation_coordinator")
    intelligence = coordinator.intelligence_repository.get_by_case_id(case_id)
    report = coordinator.get_report_by_case_id(case_id)

    authorization_payload = serialize(intelligence) or serialize(report) or {}
    if report and isinstance(report, dict):
        tenant_context = report.get("tenant_context") or {}
        if isinstance(tenant_context, dict) and tenant_context.get("tenant_id"):
            authorization_payload = dict(authorization_payload)
            metadata = dict(authorization_payload.get("metadata") or {})
            metadata.setdefault("tenant_id", tenant_context["tenant_id"])
            authorization_payload["metadata"] = metadata

    allowed, error = authorize_investigation(authorization_payload, write=False)
    if not allowed:
        status = 401 if error == "authentication_required" else 403
        return render_template("error.html", message="Investigation not found."), status

    if intelligence is None and report is None:
        return render_template("error.html", message="Investigation not found."), 404
    intelligence = serialize(intelligence) or {}
    report = serialize(report) or {}
    from flask import g
    security_context = getattr(g, "security_context", None)
    read_model = None
    if security_context is not None and callable(getattr(coordinator, "get_investigation_view", None)):
        try:
            read_model = coordinator.get_investigation_view(case_id, security_context) or {}
        except (LookupError, PermissionError, AttributeError, ValueError):
            read_model = None
    tenant_id = getattr(security_context, "tenant_id", None) or (report.get("tenant_context") or {}).get("tenant_id")
    feedback_history, quality_analytics, evidence_quality, quality_assessment = [], {}, {}, {}
    if tenant_id:
        try:
            feedback_history = (read_model or {}).get("feedback") or coordinator.get_feedback(case_id, str(tenant_id))
            quality_analytics = {"daily": coordinator.get_feedback_analytics(str(tenant_id), case_id=case_id, granularity="daily"), "weekly": coordinator.get_feedback_analytics(str(tenant_id), case_id=case_id, granularity="weekly")}
            evidence_quality = coordinator.get_evidence_linked_quality(case_id, str(tenant_id))
            if security_context is not None and callable(getattr(coordinator, "get_quality_assessment", None)):
                quality_assessment = (read_model or {}).get("quality") or coordinator.get_quality_assessment(case_id, security_context) or {}
        except (LookupError, AttributeError, ValueError):
            pass
    metadata = dict(report.get("metadata") or {})
    metadata.setdefault("tenant_id", tenant_id or "Unavailable")
    return render_template(
        "investigation_workspace.html",
        case_id=case_id,
        intelligence=intelligence,
        report=report,
        metadata=metadata,
        feedback_history=feedback_history,
        quality_analytics=quality_analytics,
        evidence_quality=evidence_quality,
        quality_assessment=quality_assessment,
        read_model=read_model or {},
        correlation_id=(intelligence.get("metadata") or {}).get("correlation_id", "Unavailable"),
        tenant_id=(intelligence.get("metadata") or {}).get("tenant_id", "Unavailable"),
    )

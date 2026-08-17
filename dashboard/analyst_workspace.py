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
    return render_template(
        "investigation_workspace.html",
        case_id=case_id,
        intelligence=intelligence,
        report=report,
        correlation_id=(intelligence.get("metadata") or {}).get("correlation_id", "Unavailable"),
        tenant_id=(intelligence.get("metadata") or {}).get("tenant_id", "Unavailable"),
    )

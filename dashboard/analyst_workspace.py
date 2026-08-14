"""Thin analyst-facing view over the canonical investigation repository."""
from __future__ import annotations
from flask import Blueprint, current_app, render_template
from services.core.serialization import serialize

analyst_workspace = Blueprint("analyst_workspace", __name__, url_prefix="/workspace/analyst")

@analyst_workspace.get("/<case_id>")
def investigation_workspace(case_id: str):
    coordinator = current_app.container.require("investigation_coordinator")
    intelligence = coordinator.intelligence_repository.get_by_case_id(case_id)
    report = coordinator.get_report_by_case_id(case_id)
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

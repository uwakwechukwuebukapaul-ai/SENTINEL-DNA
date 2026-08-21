"""Thin analyst-facing view over the canonical investigation repository."""
from __future__ import annotations
from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from services.core.security_context import authorize_investigation, request_context
from services.core.serialization import serialize
from services.intelligence.workspace.v2 import AnalystWorkspaceV2Builder
from services.intelligence.reporting.ai_investigator_report import AIInvestigatorReportService

analyst_workspace = Blueprint("analyst_workspace", __name__, url_prefix="/workspace/analyst")
workspace_entry_blueprint = Blueprint("workspace_entry", __name__, url_prefix="/workspace")


def _entry_context():
    """Resolve the authenticated canonical principal for the workspace entry page."""
    context = request_context()
    actor_id = session.get("actor_id") or (session.get("canonical_principal") or {}).get("actor_id")
    if not context.user_id or not context.tenant_id or not actor_id:
        return None
    authority = current_app.container.require("canonical_authority")
    tenant, identity, membership = authority.resolve(str(context.tenant_id), str(actor_id))
    if membership.role.lower() not in {"admin", "soc_manager", "analyst", "viewer"}:
        return None
    return {
        "analyst": {"actor_id": identity.actor_id, "name": identity.display_name or identity.email, "email": identity.email, "role": membership.role},
        "tenant": {"id": tenant.tenant_id, "name": tenant.name},
        "tenant_id": tenant.tenant_id,
    }


@workspace_entry_blueprint.get("/", endpoint="workspace_entry")
def workspace_entry():
    try:
        principal = _entry_context()
    except (LookupError, PermissionError, ValueError):
        principal = None
    if principal is None:
        return render_template("error.html", message="Authentication and tenant membership are required."), 401
    coordinator = current_app.container.require("investigation_coordinator")
    snapshot = coordinator.get_workspace_snapshot(principal["tenant_id"])
    return render_template("workspace_v2.html", **principal, **snapshot)


def _csrf_valid() -> bool:
    expected = session.get("csrf_token")
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    return bool(expected and supplied and supplied == expected)


def _detail_projection(coordinator, investigation_id: str, tenant_id: str) -> dict | None:
    report = coordinator.get_report_by_case_id(investigation_id, tenant_id)
    intelligence = coordinator.intelligence_repository.get_by_case_id(investigation_id)
    if report is None and intelligence is None:
        return None
    intelligence = serialize(intelligence) or {}
    report = serialize(report) or {}
    owner = (report.get("tenant_context") or {}).get("tenant_id") or (report.get("metadata") or {}).get("tenant_id")
    intel_owner = (intelligence.get("metadata") or {}).get("tenant_id")
    if (owner and str(owner) != str(tenant_id)) or (intel_owner and str(intel_owner) != str(tenant_id)):
        return None
    read_model = {}
    context = request_context()
    if callable(getattr(coordinator, "get_investigation_view", None)):
        try:
            read_model = coordinator.get_investigation_view(investigation_id, context) or {}
        except (LookupError, PermissionError, AttributeError, ValueError):
            read_model = {}
    result = read_model.get("result") or read_model.get("investigation") or {}
    bundle = result.get("intelligence") if isinstance(result, dict) else {}
    bundle = bundle if isinstance(bundle, dict) else {}
    evidence = report.get("evidence") or result.get("evidence") or intelligence.get("evidence") or intelligence.get("artifacts") or []
    iocs = report.get("iocs") or result.get("indicators") or intelligence.get("iocs") or []
    relationships = report.get("relationships") or result.get("relationships") or intelligence.get("relationships") or []
    mitre = report.get("mitre") or result.get("mitre") or intelligence.get("mitre_techniques") or []
    risk = report.get("risk") if isinstance(report.get("risk"), dict) else {}
    return {
        "id": investigation_id,
        "status": report.get("status") or result.get("status") or intelligence.get("status", "unknown"),
        "risk_score": risk.get("score", report.get("risk_score", result.get("risk_score", intelligence.get("risk_score", 0)))),
        "confidence": report.get("confidence", result.get("confidence", intelligence.get("confidence", 0))),
        "findings": report.get("findings") or result.get("findings") or intelligence.get("findings") or [],
        "evidence": evidence if isinstance(evidence, list) else [evidence],
        "iocs": iocs if isinstance(iocs, list) else [iocs],
        "relationships": relationships if isinstance(relationships, list) else [relationships],
        "mitre": mitre if isinstance(mitre, list) else [mitre],
        "reasoning": report.get("reasoning_report") or result.get("reasoning_report") or result.get("reasoning") or bundle.get("reasoning_report") or "No AI reasoning report is available.",
        "recommendations": report.get("recommendations") or result.get("recommendations") or intelligence.get("recommendations") or [],
        "report": report,
        "intelligence": intelligence,
        "result": result,
        "read_model": read_model,
    }


@workspace_entry_blueprint.route("/investigation/<investigation_id>", methods=["GET"])
def investigation_detail(investigation_id: str):
    try:
        principal = _entry_context()
    except (LookupError, PermissionError, ValueError):
        principal = None
    if principal is None:
        return render_template("error.html", message="Authentication and tenant membership are required."), 401
    coordinator = current_app.container.require("investigation_coordinator")
    detail = _detail_projection(coordinator, investigation_id, principal["tenant_id"])
    if detail is None:
        return render_template("error.html", message="Investigation not found."), 404
    return render_template("investigation_detail_v3.html", **principal, investigation=detail, csrf_token=session.get("csrf_token"))


@workspace_entry_blueprint.get("/investigation/<investigation_id>/report")
def investigation_report(investigation_id: str):
    try:
        principal = _entry_context()
    except (LookupError, PermissionError, ValueError):
        principal = None
    if principal is None:
        return render_template("error.html", message="Authentication and tenant membership are required."), 401
    coordinator = current_app.container.require("investigation_coordinator")
    report = AIInvestigatorReportService().build(
        coordinator, investigation_id, principal["tenant_id"], request_context()
    )
    if report is None:
        return render_template("error.html", message="Investigation not found."), 404
    return render_template("investigation_report_v4.html", **principal, report=report.to_dict())


@workspace_entry_blueprint.post("/investigation/<investigation_id>/start")
def start_investigation(investigation_id: str):
    if not _csrf_valid():
        return {"error": "csrf_validation_failed"}, 403
    try:
        principal = _entry_context()
    except (LookupError, PermissionError, ValueError):
        principal = None
    if principal is None:
        return {"error": "authentication_required"}, 401
    if principal["analyst"]["role"].lower() not in {"admin", "soc_manager", "analyst"}:
        return {"error": "forbidden"}, 403
    coordinator = current_app.container.require("investigation_coordinator")
    detail = _detail_projection(coordinator, investigation_id, principal["tenant_id"])
    if detail is None:
        return {"error": "investigation_not_found"}, 404
    coordinator.investigate(
        case_id=investigation_id,
        alert={"case_id": investigation_id, "source": "analyst_workspace"},
        artifacts=detail["evidence"],
        tenant_id=principal["tenant_id"],
        actor_id=principal["analyst"]["actor_id"],
        correlation_id=request_context().correlation_id,
    )
    return redirect(url_for("workspace_entry.investigation_detail", investigation_id=investigation_id))

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

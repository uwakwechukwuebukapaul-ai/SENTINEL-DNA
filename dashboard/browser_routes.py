"""Canonical browser entrypoints for the analyst investigation workflow."""
from __future__ import annotations

from functools import wraps
from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for
from services.core.security_context import authorize_investigation, request_context
from services.intelligence.reporting.ai_investigator_report import AIInvestigatorReportService
from services.intelligence.reporting.investigation_projection import InvestigationProjectionBuilder

browser = Blueprint("browser", __name__)


def _principal():
    context = request_context()
    if not context.user_id or not context.actor_id or not context.tenant_id or context.error:
        return None
    try:
        tenant, identity, membership = current_app.container.require("canonical_authority").resolve(context.tenant_id, context.actor_id)
    except (LookupError, PermissionError, ValueError):
        return None
    user = current_app.container.require("auth_service").get_by_id(context.user_id)
    return {"analyst": {"actor_id": identity.actor_id, "name": identity.display_name or identity.email, "email": identity.email, "role": membership.role, "age": user.age() if user else None, "age_verified": bool(user and user.date_of_birth), "phone_verified": bool(user and user.phone_verified_at)}, "tenant": {"id": tenant.tenant_id, "name": tenant.name}, "tenant_id": tenant.tenant_id}


def _authenticated(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        principal = _principal()
        if principal is None:
            return jsonify({"error": "authentication_required"}), 401
        return view(principal, *args, **kwargs)
    return wrapped


@browser.get("/login")
def login_page():
    return redirect(url_for("browser.home")) if _principal() else render_template("login.html")


@browser.get("/signup")
def signup_page():
    return redirect(url_for("browser.home")) if _principal() else render_template("signup.html")

@browser.get("/forgot-password")
def forgot_password_page():
    return redirect(url_for("browser.home")) if _principal() else render_template("forgot_password.html")


@browser.get("/")
@_authenticated
def home(principal):
    _ensure_demo_scenario(principal["tenant_id"])
    snapshot = current_app.container.require("investigation_coordinator").get_workspace_snapshot(principal["tenant_id"])
    return render_template("browser_dashboard.html", **principal, **snapshot)


@browser.get("/profile")
@_authenticated
def profile(principal):
    return render_template("profile.html", **principal)


@browser.get("/workspace/")
@_authenticated
def workspace(principal):
    _ensure_demo_scenario(principal["tenant_id"])
    snapshot = current_app.container.require("investigation_coordinator").get_workspace_snapshot(principal["tenant_id"])
    return render_template("workspace_v2.html", **principal, **snapshot)


def _detail(investigation_id):
    return current_app.container.require("investigation_coordinator").get_investigation_view(investigation_id, request_context())


def _ensure_demo_scenario(tenant_id):
    if current_app.config.get("DEMO_DATA_ENABLED"):
        current_app.container.require("analyst_demo_scenario").ensure_for_tenant(tenant_id)


@browser.get("/workspace/investigation/<investigation_id>")
@_authenticated
def investigation_detail(principal, investigation_id):
    try:
        detail = _detail(investigation_id)
    except (LookupError, PermissionError, ValueError):
        detail = None
    if not detail:
        return render_template("error.html", message="Investigation not found."), 404
    projection = InvestigationProjectionBuilder().build_from_read_model(
        detail,
        tenant_id=principal["tenant_id"],
    )
    return render_template(
        "investigation_detail_v3.html",
        **principal,
        investigation={"id": investigation_id, "projection": projection.to_dict(), **detail},
        csrf_token=session.get("csrf_token"),
    )


@browser.get("/workspace/investigation/<investigation_id>/report")
@_authenticated
def investigation_report(principal, investigation_id):
    report = AIInvestigatorReportService().build(current_app.container.require("investigation_coordinator"), investigation_id, principal["tenant_id"], request_context())
    if report is None:
        return render_template("error.html", message="Investigation not found."), 404
    return render_template("investigation_report_v4.html", **principal, report=report.to_dict())


@browser.post("/workspace/investigation/<investigation_id>/start")
def start_investigation(investigation_id):
    expected = session.get("csrf_token")
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    if not expected or supplied != expected:
        return jsonify({"error": "csrf_validation_failed"}), 403
    principal = _principal()
    if principal is None:
        return jsonify({"error": "authentication_required"}), 401
    if str(principal["analyst"]["role"]).lower() not in {"admin", "soc_manager", "analyst"}:
        return jsonify({"error": "forbidden"}), 403
    try:
        detail = _detail(investigation_id)
    except (LookupError, PermissionError, ValueError):
        detail = None
    if not detail:
        return jsonify({"error": "investigation_not_found"}), 404
    demo_service = current_app.container.get("analyst_demo_scenario")
    if current_app.config.get("DEMO_DATA_ENABLED") and demo_service and str(investigation_id) == demo_service.case_id_for_tenant(principal["tenant_id"]):
        demo_input = demo_service.investigation_input_for_tenant(principal["tenant_id"])
        allowed, error = authorize_investigation(
            {"metadata": demo_input["alert"].get("metadata") or {}}, write=True
        )
        if not allowed:
            return jsonify({"error": error}), 403
        current_app.container.require("investigation_coordinator").investigate(
            case_id=demo_input["case_id"],
            alert=demo_input["alert"],
            artifacts=demo_input["artifacts"],
            evidence=demo_input["evidence"],
            iocs=demo_input["iocs"],
            tenant_id=principal["tenant_id"],
            actor_id=principal["analyst"]["actor_id"],
            correlation_id=request_context().correlation_id,
        )
        _record_pilot_investigation_audit(
            principal["tenant_id"], principal["analyst"]["actor_id"],
            investigation_id, demo_input["alert"].get("metadata") or {}, request_context(),
        )
        return redirect(url_for("browser.investigation_detail", investigation_id=investigation_id))
    report = detail.get("report") or {}
    intelligence = detail.get("intelligence") or {}
    metadata = report.get("metadata") or intelligence.get("metadata") or {}
    allowed, error = authorize_investigation({"metadata": metadata}, write=True)
    if not allowed:
        return jsonify({"error": error}), 403
    evidence_summary = intelligence.get("evidence_summary") if isinstance(intelligence.get("evidence_summary"), dict) else {}
    evidence = report.get("evidence") or intelligence.get("evidence") or evidence_summary.get("items") or []
    iocs = report.get("iocs") or intelligence.get("iocs") or []
    timeline = report.get("timeline") or intelligence.get("timeline") or []
    current_app.container.require("investigation_coordinator").investigate(case_id=investigation_id, alert={"case_id": investigation_id, "source": "analyst_workspace", "title": report.get("title"), "severity": report.get("severity"), "metadata": metadata}, artifacts=evidence, evidence=evidence, iocs=iocs, timeline=timeline, tenant_id=principal["tenant_id"], actor_id=principal["analyst"]["actor_id"], correlation_id=request_context().correlation_id)
    _record_pilot_investigation_audit(
        principal["tenant_id"], principal["analyst"]["actor_id"],
        investigation_id, metadata, request_context(),
    )
    return redirect(url_for("browser.investigation_detail", investigation_id=investigation_id))


def _record_pilot_investigation_audit(tenant_id, actor_id, case_id, metadata, context):
    if not context.pilot_authorization_id:
        return
    current_app.container.require("audit_service").record(
        "PILOT_INVESTIGATION_EXECUTED",
        case_id=case_id,
        tenant_id=tenant_id,
        actor_id=actor_id,
        correlation_id=context.correlation_id,
        resource_type="pilot_authorization",
        resource_id=context.pilot_authorization_id,
        operation="investigate",
        outcome="success",
        details={"scenario_id": metadata.get("scenario_id") or metadata.get("scenario")},
    )

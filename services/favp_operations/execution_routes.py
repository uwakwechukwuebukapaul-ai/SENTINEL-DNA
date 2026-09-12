"""Opt-in HTTP boundary for FAVP execution readiness and validation."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from services.auth.permissions import permission_required
from services.core.security_context import request_context
from .execution import FAVPExecutionError


def create_favp_execution_blueprint():
    blueprint = Blueprint("favp_execution_api", __name__, url_prefix="/api/favp/execution")

    def service():
        result = current_app.container.get("favp_execution")
        if result is None:
            raise FAVPExecutionError("favp_execution_disabled")
        return result

    def trusted_context():
        context = request_context()
        if context.error:
            return None, (jsonify({"error": context.error}), 403)
        if not context.tenant_id or not context.actor_id:
            return None, (jsonify({"error": "tenant_access_denied"}), 403)
        return context, None

    def body():
        value = request.get_json(silent=True)
        if not isinstance(value, dict):
            raise FAVPExecutionError("json_object_required")
        for field in ("tenant_id", "actor_ref", "profile_id", "participant_id", "session_id"):
            value.pop(field, None)
        return value

    def handle(call, status=200):
        try:
            return jsonify(call()), status
        except FAVPExecutionError as exc:
            code = str(exc)
            return jsonify({"error": code}), 404 if code.endswith("_not_found") else 400

    @blueprint.get("/readiness")
    @permission_required("pilot:read")
    def readiness():
        _context, failure = trusted_context()
        if failure:
            return failure
        return handle(lambda: service().readiness())

    @blueprint.post("/activation-check")
    @permission_required("pilot:manage")
    def activation_check():
        _context, failure = trusted_context()
        if failure:
            return failure
        return handle(lambda: service().readiness())

    @blueprint.get("/launch-readiness")
    @permission_required("pilot:read")
    def launch_readiness():
        _context, failure = trusted_context()
        if failure:
            return failure
        return handle(lambda: service().launch_readiness(tenant_id=_context.tenant_id))

    @blueprint.get("/scenarios")
    @permission_required("pilot:read")
    def scenarios():
        _context, failure = trusted_context()
        if failure:
            return failure
        return handle(lambda: {"scenarios": service().list_scenarios()})

    @blueprint.post("/profiles")
    @permission_required("pilot:manage")
    def create_profile():
        context, failure = trusted_context()
        if failure:
            return failure
        return handle(lambda: service().create_profile(tenant_id=context.tenant_id, actor_ref=context.actor_id, **body()), 201)

    @blueprint.patch("/profiles/<profile_id>/compliance")
    @permission_required("pilot:manage")
    def compliance(profile_id):
        context, failure = trusted_context()
        if failure:
            return failure
        return handle(lambda: service().update_compliance(tenant_id=context.tenant_id, profile_id=profile_id, actor_ref=context.actor_id, **body()))

    @blueprint.post("/profiles/<profile_id>/transition")
    @permission_required("pilot:manage")
    def transition(profile_id):
        context, failure = trusted_context()
        if failure:
            return failure
        return handle(lambda: service().transition_profile(tenant_id=context.tenant_id, profile_id=profile_id, actor_ref=context.actor_id, **body()))

    @blueprint.post("/profiles/<profile_id>/revoke")
    @permission_required("pilot:manage")
    def revoke(profile_id):
        context, failure = trusted_context()
        if failure:
            return failure
        return handle(lambda: service().revoke_profile(tenant_id=context.tenant_id, profile_id=profile_id, actor_ref=context.actor_id))

    @blueprint.post("/profiles/<profile_id>/sessions")
    @permission_required("validation:execute")
    def start_session(profile_id):
        context, failure = trusted_context()
        if failure:
            return failure
        manager = bool(set(context.roles).intersection({"admin", "soc_manager"}))
        return handle(lambda: service().start_session(tenant_id=context.tenant_id, profile_id=profile_id, actor_ref=context.actor_id, manager=manager, **body()), 201)

    @blueprint.post("/sessions/<session_id>/review")
    @permission_required("validation:execute")
    def review(session_id):
        context, failure = trusted_context()
        if failure:
            return failure
        manager = bool(set(context.roles).intersection({"admin", "soc_manager"}))
        return handle(lambda: service().submit_review(tenant_id=context.tenant_id, session_id=session_id, actor_ref=context.actor_id, manager=manager, **body()), 201)

    @blueprint.post("/sessions/<session_id>/evidence-validation")
    @permission_required("pilot:manage")
    def evidence_validation(session_id):
        context, failure = trusted_context()
        if failure:
            return failure
        return handle(lambda: service().validate_evidence(tenant_id=context.tenant_id, session_id=session_id, actor_ref=context.actor_id, **body()), 201)

    @blueprint.get("/profiles/<profile_id>/workspace")
    @permission_required("pilot:read")
    def workspace(profile_id):
        context, failure = trusted_context()
        if failure:
            return failure
        manager = bool(set(context.roles).intersection({"admin", "soc_manager"}))
        return handle(lambda: service().workspace(tenant_id=context.tenant_id, profile_id=profile_id, actor_ref=context.actor_id, manager=manager))

    @blueprint.get("/dashboard")
    @permission_required("pilot:read")
    def dashboard():
        context, failure = trusted_context()
        if failure:
            return failure
        return handle(lambda: service().progress_dashboard(tenant_id=context.tenant_id))

    @blueprint.get("/reports/organization")
    @permission_required("pilot:read")
    def organization_report():
        context, failure = trusted_context()
        if failure:
            return failure
        return handle(lambda: service().organization_summary(tenant_id=context.tenant_id))

    @blueprint.get("/reports/final-template")
    @permission_required("pilot:read")
    def final_template():
        context, failure = trusted_context()
        if failure:
            return failure
        return handle(lambda: service().final_report_template(tenant_id=context.tenant_id))

    @blueprint.get("/profiles/<profile_id>/report")
    @permission_required("pilot:read")
    def individual_report(profile_id):
        context, failure = trusted_context()
        if failure:
            return failure
        manager = bool(set(context.roles).intersection({"admin", "soc_manager"}))
        return handle(lambda: service().individual_report(tenant_id=context.tenant_id, profile_id=profile_id, actor_ref=context.actor_id, manager=manager))

    return blueprint


favp_execution_api = create_favp_execution_blueprint()

__all__ = ["create_favp_execution_blueprint", "favp_execution_api"]

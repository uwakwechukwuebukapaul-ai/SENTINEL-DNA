"""Opt-in HTTP boundary for FAVP operations.

The blueprint is intentionally not registered by default.  Deployments must
enable ``SENTINEL_DNA_FAVP_OPERATIONS_ENABLED=1`` in a non-production
environment.  The route never handles credentials, browser sessions, or
production/customer evidence.
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from services.auth.permissions import permission_required
from services.core.security_context import request_context

from .service import FAVPOperationsError


def create_favp_blueprint():
    blueprint = Blueprint("favp_operations_api", __name__, url_prefix="/api/favp")

    def service():
        instance = current_app.container.get("favp_operations")
        if instance is None:
            raise FAVPOperationsError("favp_operations_disabled")
        return instance

    def context():
        value = request_context()
        if value.error:
            return None, (jsonify({"error": value.error}), 403)
        if not value.tenant_id or not value.actor_id:
            return None, (jsonify({"error": "tenant_access_denied"}), 403)
        return value, None

    def payload():
        value = request.get_json(silent=True)
        if not isinstance(value, dict):
            raise FAVPOperationsError("json_object_required")
        return value

    def operator_payload():
        value = payload()
        # Tenant and actor identity always come from the trusted request
        # context, never from JSON supplied by the caller.
        for field in ("tenant_id", "actor_ref", "participant_id"):
            value.pop(field, None)
        return value

    def handle(call, status=200):
        try:
            return jsonify(call()), status
        except FAVPOperationsError as exc:
            code = str(exc)
            return jsonify({"error": code}), 404 if code.endswith("_not_found") else 400

    @blueprint.get("/scenarios")
    @permission_required("pilot:read")
    def scenarios():
        return handle(lambda: {"scenarios": service().list_scenarios()})

    @blueprint.get("/organizations")
    @permission_required("pilot:read")
    def organizations():
        context_value, failure = context()
        if failure:
            return failure
        return handle(lambda: {"organizations": service().repository.list_organizations(context_value.tenant_id)})

    @blueprint.post("/organizations")
    @permission_required("pilot:manage")
    def create_organization():
        context_value, failure = context()
        if failure:
            return failure
        return handle(lambda: service().create_organization(tenant_id=context_value.tenant_id, actor_ref=context_value.actor_id, **operator_payload()), 201)

    @blueprint.get("/participants")
    @permission_required("pilot:read")
    def participants():
        context_value, failure = context()
        if failure:
            return failure
        return handle(lambda: {"participants": service().repository.list_participants(context_value.tenant_id)})

    @blueprint.post("/participants")
    @permission_required("pilot:manage")
    def create_participant():
        context_value, failure = context()
        if failure:
            return failure
        return handle(lambda: service().create_participant(tenant_id=context_value.tenant_id, actor_ref=context_value.actor_id, **operator_payload()), 201)

    @blueprint.post("/participants/<participant_id>/transition")
    @permission_required("pilot:manage")
    def transition(participant_id):
        context_value, failure = context()
        if failure:
            return failure
        return handle(lambda: service().transition_participant(tenant_id=context_value.tenant_id, participant_id=participant_id, actor_ref=context_value.actor_id, **operator_payload()))

    @blueprint.post("/participants/<participant_id>/invitations")
    @permission_required("pilot:manage")
    def invitation(participant_id):
        context_value, failure = context()
        if failure:
            return failure
        return handle(lambda: service().record_invitation(tenant_id=context_value.tenant_id, participant_id=participant_id, actor_ref=context_value.actor_id, **operator_payload()), 201)

    @blueprint.post("/participants/<participant_id>/requirements")
    @permission_required("pilot:manage")
    def requirements(participant_id):
        context_value, failure = context()
        if failure:
            return failure
        return handle(lambda: service().update_participation_requirements(tenant_id=context_value.tenant_id, participant_id=participant_id, actor_ref=context_value.actor_id, **operator_payload()))

    @blueprint.post("/participants/<participant_id>/scenarios")
    @permission_required("pilot:manage")
    def assign_scenario(participant_id):
        context_value, failure = context()
        if failure:
            return failure
        return handle(lambda: service().assign_scenario(tenant_id=context_value.tenant_id, participant_id=participant_id, actor_ref=context_value.actor_id, **operator_payload()), 201)

    @blueprint.get("/participants/<participant_id>/workspace")
    @permission_required("pilot:read")
    def workspace(participant_id):
        context_value, failure = context()
        if failure:
            return failure
        manager = set(context_value.roles).intersection({"admin", "soc_manager"})
        return handle(lambda: service().workspace(tenant_id=context_value.tenant_id, participant_id=participant_id, actor_identity_ref=None if manager else context_value.actor_id))

    @blueprint.post("/participants/<participant_id>/results")
    @permission_required("validation:execute")
    def result(participant_id):
        context_value, failure = context()
        if failure:
            return failure
        participant = service().repository.get_participant(context_value.tenant_id, participant_id)
        if not participant:
            return jsonify({"error": "participant_not_found"}), 404
        if not set(context_value.roles).intersection({"admin", "soc_manager"}) and context_value.actor_id not in {participant_id, participant.get("actor_identity_ref")}:
            return jsonify({"error": "participant_workspace_forbidden"}), 403
        return handle(lambda: service().record_result(tenant_id=context_value.tenant_id, participant_id=participant_id, actor_ref=context_value.actor_id, **operator_payload()), 201)

    @blueprint.post("/participants/<participant_id>/feedback")
    @permission_required("validation:execute")
    def feedback(participant_id):
        context_value, failure = context()
        if failure:
            return failure
        participant = service().repository.get_participant(context_value.tenant_id, participant_id)
        if not participant:
            return jsonify({"error": "participant_not_found"}), 404
        if not set(context_value.roles).intersection({"admin", "soc_manager"}) and context_value.actor_id not in {participant_id, participant.get("actor_identity_ref")}:
            return jsonify({"error": "participant_workspace_forbidden"}), 403
        return handle(lambda: service().record_feedback(tenant_id=context_value.tenant_id, participant_id=participant_id, actor_ref=context_value.actor_id, **operator_payload()), 201)

    @blueprint.get("/kpis")
    @permission_required("pilot:read")
    def kpis():
        context_value, failure = context()
        if failure:
            return failure
        return handle(lambda: service().kpis(tenant_id=context_value.tenant_id))

    @blueprint.get("/report")
    @permission_required("pilot:read")
    def report():
        context_value, failure = context()
        if failure:
            return failure
        return handle(lambda: service().report(tenant_id=context_value.tenant_id, generated_by=context_value.actor_id))

    return blueprint


favp_operations_api = create_favp_blueprint()

__all__ = ["create_favp_blueprint", "favp_operations_api"]

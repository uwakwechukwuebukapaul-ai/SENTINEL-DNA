"""HTTP boundary for the controlled analyst pilot overlay."""

from __future__ import annotations

from urllib.parse import urlparse

from flask import Blueprint, current_app, jsonify, request

from services.auth.permissions import permission_required
from services.auth.routes import _csrf_ok
from services.core.security_context import request_context
from services.pilot_management.authorization import PilotAuthorizationError
from services.pilot_management.provisioning import PilotProvisioningError

from .service import ControlledAnalystPilotError


controlled_analyst_pilot_api = Blueprint(
    "controlled_analyst_pilot_api",
    __name__,
    url_prefix="/api/controlled-analyst-pilot",
)


def _service():
    return current_app.container.require("controlled_analyst_pilot_service")


def _context(*, manager: bool = False):
    context = request_context()
    if not context.user_id:
        return None, (jsonify({"error": "authentication_required"}), 401)
    if context.error:
        return None, (jsonify({"error": context.error}), 403)
    if not context.tenant_id or not context.actor_id:
        return None, (jsonify({"error": "tenant_access_denied"}), 403)
    if manager and not set(context.roles).intersection({"admin", "soc_manager"}):
        return None, (jsonify({"error": "forbidden"}), 403)
    return context, None


def _csrf():
    origin = request.headers.get("Origin")
    if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
        return False
    referer = request.headers.get("Referer")
    if referer:
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc and f"{parsed.scheme}://{parsed.netloc}".rstrip("/") != request.host_url.rstrip("/"):
            return False
    return bool(request.headers.get("X-CSRF-Token") and _csrf_ok())


def _payload():
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else None


def _error(exc: ControlledAnalystPilotError):
    text = str(exc)
    status = 404 if text.endswith("_not_found") else 400
    return jsonify({"error": text}), status


@controlled_analyst_pilot_api.post("/onboard")
@permission_required("pilot:manage")
def onboard():
    if not _csrf():
        return jsonify({"error": "csrf_validation_failed"}), 403
    context, failure = _context(manager=True)
    if failure:
        return failure
    payload = _payload()
    if payload is None:
        return jsonify({"error": "json_object_required"}), 400
    try:
        account = current_app.container.require("pilot_account_provisioning_service").provision(
            manager_tenant_id=context.tenant_id,
            provisioned_by=context.actor_id,
            username=payload.get("username"),
            email=payload.get("email"),
            display_name=payload.get("display_name"),
            tenant_name=payload.get("tenant_name"),
            expires_at=payload.get("expires_at"),
            approved_scenarios=payload.get("approved_scenarios"),
            audit_correlation_id=context.correlation_id,
            activation_expires_at=payload.get("activation_expires_at"),
        )
        tenant = _service().onboard_provisioned_account(
            provisioning_id=account.provisioning_id,
            manager_tenant_id=context.tenant_id,
            actor_id=context.actor_id,
            correlation_id=context.correlation_id,
            display_name=payload.get("tenant_name"),
        )
    except ControlledAnalystPilotError as exc:
        if "account" in locals():
            _compensate_onboarding(account, context)
        return _error(exc)
    except (PilotProvisioningError, PilotAuthorizationError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        # The account provision is compensatable if the overlay registration
        # fails.  Cleanup failure is intentionally not exposed to the client.
        try:
            if "account" in locals():
                current_app.container.require("pilot_account_provisioning_service").revoke(
                    provisioning_id=account.provisioning_id,
                    manager_tenant_id=context.tenant_id,
                    revoked_by=context.actor_id,
                    reason="controlled pilot overlay onboarding failed",
                    audit_correlation_id=context.correlation_id,
                )
        except Exception:
            pass
        raise exc
    return jsonify({"account": account.to_dict(include_activation_token=True), "tenant": tenant.to_dict()}), 201


def _compensate_onboarding(account, context) -> None:
    try:
        current_app.container.require("pilot_account_provisioning_service").revoke(
            provisioning_id=account.provisioning_id,
            manager_tenant_id=context.tenant_id,
            revoked_by=context.actor_id,
            reason="controlled pilot overlay onboarding failed",
            audit_correlation_id=context.correlation_id,
        )
    except Exception:
        current_app.logger.warning("controlled pilot onboarding compensation failed", exc_info=True)


@controlled_analyst_pilot_api.get("/current")
@permission_required("pilot:read")
def current():
    context, failure = _context()
    if failure:
        return failure
    tenant = _service().tenant_state(context.tenant_id)
    if tenant is None or tenant.analyst_id != context.actor_id:
        return jsonify({"error": "pilot_tenant_not_found"}), 404
    return jsonify(tenant.to_dict())


@controlled_analyst_pilot_api.post("/feedback")
@permission_required("pilot:feedback")
def capture_feedback():
    if not _csrf():
        return jsonify({"error": "csrf_validation_failed"}), 403
    context, failure = _context()
    if failure:
        return failure
    payload = _payload()
    if payload is None:
        return jsonify({"error": "json_object_required"}), 400
    try:
        feedback = _service().capture_feedback(
            tenant_id=context.tenant_id,
            analyst_id=context.actor_id,
            case_id=payload.pop("case_id", None),
            investigation_id=payload.pop("investigation_id", None),
            payload=payload,
            correlation_id=context.correlation_id,
        )
    except ControlledAnalystPilotError as exc:
        return _error(exc)
    return jsonify(feedback), 201


@controlled_analyst_pilot_api.get("/feedback")
@permission_required("pilot:feedback:read")
def list_feedback():
    context, failure = _context()
    if failure:
        return failure
    analyst_id = context.actor_id if "analyst" in context.roles else request.args.get("analyst_id")
    try:
        return jsonify({"feedback": _service().list_feedback(context.tenant_id, analyst_id=analyst_id, limit=request.args.get("limit", 100))})
    except (ControlledAnalystPilotError, ValueError) as exc:
        return _error(ControlledAnalystPilotError(str(exc)))


@controlled_analyst_pilot_api.post("/reviews")
@permission_required("pilot:review")
def submit_review():
    if not _csrf():
        return jsonify({"error": "csrf_validation_failed"}), 403
    context, failure = _context()
    if failure:
        return failure
    payload = _payload()
    if payload is None:
        return jsonify({"error": "json_object_required"}), 400
    try:
        review = _service().submit_review(
            tenant_id=context.tenant_id,
            analyst_id=context.actor_id,
            case_id=payload.get("case_id"),
            investigation_id=payload.get("investigation_id"),
            decision=payload.get("decision"),
            comments=payload.get("comments"),
            correlation_id=context.correlation_id,
        )
    except ControlledAnalystPilotError as exc:
        return _error(exc)
    return jsonify(review.to_dict()), 201


@controlled_analyst_pilot_api.get("/reviews")
@permission_required("pilot:review:read")
def list_reviews():
    context, failure = _context()
    if failure:
        return failure
    return jsonify({"reviews": [item.to_dict() for item in _service().list_reviews(context.tenant_id, limit=request.args.get("limit", 100))]})


@controlled_analyst_pilot_api.post("/reviews/<review_id>/transition")
@permission_required("pilot:review:manage")
def transition_review(review_id: str):
    if not _csrf():
        return jsonify({"error": "csrf_validation_failed"}), 403
    context, failure = _context(manager=True)
    if failure:
        return failure
    payload = _payload()
    if payload is None:
        return jsonify({"error": "json_object_required"}), 400
    try:
        review = _service().transition_review(review_id, actor_id=context.actor_id, decision=payload.get("decision"), comments=payload.get("comments"), correlation_id=context.correlation_id)
    except ControlledAnalystPilotError as exc:
        return _error(exc)
    return jsonify(review.to_dict())


@controlled_analyst_pilot_api.post("/reviews/<review_id>/reopen")
@permission_required("pilot:review:manage")
def reopen_review(review_id: str):
    if not _csrf():
        return jsonify({"error": "csrf_validation_failed"}), 403
    context, failure = _context(manager=True)
    if failure:
        return failure
    payload = _payload() or {}
    try:
        review = _service().reopen_review(review_id, actor_id=context.actor_id, reason=payload.get("reason"), correlation_id=context.correlation_id)
    except ControlledAnalystPilotError as exc:
        return _error(exc)
    return jsonify(review.to_dict())


@controlled_analyst_pilot_api.post("/reviews/<review_id>/withdraw")
@permission_required("pilot:review:manage")
def withdraw_review(review_id: str):
    if not _csrf():
        return jsonify({"error": "csrf_validation_failed"}), 403
    context, failure = _context(manager=True)
    if failure:
        return failure
    payload = _payload() or {}
    try:
        review = _service().withdraw_review(review_id, actor_id=context.actor_id, reason=payload.get("reason"), correlation_id=context.correlation_id)
    except ControlledAnalystPilotError as exc:
        return _error(exc)
    return jsonify(review.to_dict())


@controlled_analyst_pilot_api.get("/audit")
@permission_required("pilot:audit:read")
def audit():
    context, failure = _context(manager=True)
    if failure:
        return failure
    return jsonify({"events": _service().list_audit(context.tenant_id, limit=request.args.get("limit", 100))})


@controlled_analyst_pilot_api.post("/tenants/<tenant_id>/suspend")
@permission_required("pilot:manage")
def suspend(tenant_id: str):
    return _tenant_transition(tenant_id, "suspend")


@controlled_analyst_pilot_api.post("/tenants/<tenant_id>/resume")
@permission_required("pilot:manage")
def resume(tenant_id: str):
    return _tenant_transition(tenant_id, "resume")


def _tenant_transition(tenant_id: str, action: str):
    if not _csrf():
        return jsonify({"error": "csrf_validation_failed"}), 403
    context, failure = _context(manager=True)
    if failure:
        return failure
    try:
        tenant = getattr(_service(), action)(tenant_id, actor_id=context.actor_id, correlation_id=context.correlation_id)
    except ControlledAnalystPilotError as exc:
        return _error(exc)
    return jsonify(tenant.to_dict())


__all__ = ["controlled_analyst_pilot_api"]

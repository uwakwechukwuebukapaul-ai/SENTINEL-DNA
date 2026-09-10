from flask import Blueprint, current_app, jsonify, request
from urllib.parse import urlparse
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
from services.core.security_context import request_context
from services.auth.routes import _csrf_ok
from database.portability import integrity_error
from .authorization import PilotAuthorizationError
from .provisioning import PilotProvisioningError

pilot_management_api = Blueprint("pilot_management_api", __name__, url_prefix="/api/pilots")

pilot_authorization_api = Blueprint(
    "pilot_authorization_api", __name__, url_prefix="/api/pilot-authorizations"
)

pilot_provisioning_api = Blueprint(
    "pilot_provisioning_api", __name__, url_prefix="/api/pilot-provisioning"
)


def _manager_context():
    context = request_context()
    if not context.user_id:
        return None, (jsonify({"error": "authentication_required"}), 401)
    if context.error:
        return None, (jsonify({"error": context.error}), 403)
    if not context.tenant_id or not context.actor_id:
        return None, (jsonify({"error": "tenant_access_denied"}), 403)
    if not set(context.roles).intersection({"admin", "soc_manager"}):
        return None, (jsonify({"error": "forbidden"}), 403)
    return context, None


def _pilot_service():
    return current_app.container.require("pilot_authorization_service")


def _provisioning_service():
    return current_app.container.require("pilot_account_provisioning_service")


def _pilot_csrf_ok():
    """Require the existing synchronizer token and reject cross-origin writes."""
    origin = request.headers.get("Origin")
    if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
        return False
    referer = request.headers.get("Referer")
    if referer:
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc and f"{parsed.scheme}://{parsed.netloc}".rstrip("/") != request.host_url.rstrip("/"):
            return False
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    # The legacy JSON compatibility branch intentionally used by some older
    # APIs is not sufficient for account provisioning or revocation.
    if not supplied:
        return False
    return _csrf_ok()


@pilot_management_api.get("")
@permission_required("pilot:manage")
@tenant_required
def listing(): return jsonify({"pilots": current_app.container.get("pilot_management_service").list(current_organization().organization_id)})


@pilot_authorization_api.post("")
@permission_required("pilot:manage")
def create_authorization():
    if not _pilot_csrf_ok():
        return jsonify({"error": "csrf_validation_failed"}), 403
    context, failure = _manager_context()
    if failure:
        return failure
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "json_object_required"}), 400
    try:
        authorization = _pilot_service().create(
            analyst_id=payload.get("analyst_id"),
            tenant_id=context.tenant_id,
            authorized_by=context.actor_id,
            expires_at=payload.get("expires_at"),
            approved_scenarios=payload.get("approved_scenarios"),
            audit_correlation_id=context.correlation_id,
        )
    except PilotAuthorizationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(authorization.to_dict()), 201


@pilot_authorization_api.get("")
@permission_required("pilot:manage")
def list_authorizations():
    context, failure = _manager_context()
    if failure:
        return failure
    return jsonify({
        "authorizations": [
            item.to_dict() for item in _pilot_service().list_for_tenant(context.tenant_id)
        ]
    })


@pilot_authorization_api.get("/current")
@permission_required("pilot:read")
def current_authorization():
    context = request_context()
    if not context.user_id:
        return jsonify({"error": "authentication_required"}), 401
    if context.error:
        return jsonify({"error": context.error}), 403
    if not context.tenant_id or not context.actor_id:
        return jsonify({"error": "tenant_access_denied"}), 403
    authorization = _pilot_service().active_for(context.actor_id, context.tenant_id)
    if authorization is None:
        return jsonify({"error": "pilot_authorization_required"}), 403
    return jsonify(authorization.to_dict())


@pilot_authorization_api.post("/<authorization_id>/revoke")
@permission_required("pilot:manage")
def revoke_authorization(authorization_id: str):
    if not _pilot_csrf_ok():
        return jsonify({"error": "csrf_validation_failed"}), 403
    context, failure = _manager_context()
    if failure:
        return failure
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "json_object_required"}), 400
    try:
        authorization = _pilot_service().revoke(
            authorization_id,
            tenant_id=context.tenant_id,
            revoked_by=context.actor_id,
            reason=payload.get("reason"),
            audit_correlation_id=context.correlation_id,
        )
    except PilotAuthorizationError as exc:
        return jsonify({"error": str(exc)}), 404 if "not_found" in str(exc) else 400
    return jsonify(authorization.to_dict())


@pilot_authorization_api.get("/<authorization_id>/scenarios")
@permission_required("pilot:read")
def authorization_scenarios(authorization_id: str):
    context = request_context()
    if context.error or not context.tenant_id:
        return jsonify({"error": context.error or "tenant_access_denied"}), 403
    authorization = _pilot_service().get(
        authorization_id, tenant_id=context.tenant_id
    )
    if authorization is None:
        return jsonify({"error": "pilot_authorization_not_found"}), 404
    if context.actor_id != authorization.analyst_id and not set(context.roles).intersection({"admin", "soc_manager"}):
        return jsonify({"error": "forbidden"}), 403
    return jsonify({
        "authorization_id": authorization.authorization_id,
        "approved_scenarios": list(authorization.approved_scenarios),
    })


@pilot_provisioning_api.post("")
@permission_required("pilot:manage")
def provision_pilot_account():
    if not _pilot_csrf_ok():
        return jsonify({"error": "csrf_validation_failed"}), 403
    context, failure = _manager_context()
    if failure:
        return failure
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "json_object_required"}), 400
    try:
        result = _provisioning_service().provision(
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
    except (PilotProvisioningError, PilotAuthorizationError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        if integrity_error(exc):
            return jsonify({"error": "duplicate_account_identifier"}), 409
        raise
    # The one-time token is returned once to the already authenticated manager
    # for protected-channel transfer. It is never persisted or audited.
    return jsonify(result.to_dict(include_activation_token=True)), 201


@pilot_provisioning_api.get("")
@permission_required("pilot:manage")
def list_pilot_accounts():
    context, failure = _manager_context()
    if failure:
        return failure
    return jsonify({
        "accounts": [
            item.to_dict()
            for item in _provisioning_service().list_for_manager(context.tenant_id)
        ]
    })


@pilot_provisioning_api.get("/<provisioning_id>")
@permission_required("pilot:manage")
def get_pilot_account(provisioning_id: str):
    context, failure = _manager_context()
    if failure:
        return failure
    result = _provisioning_service().get(
        provisioning_id, manager_tenant_id=context.tenant_id
    )
    if result is None:
        return jsonify({"error": "pilot_account_not_found"}), 404
    return jsonify(result.to_dict())


@pilot_provisioning_api.post("/<provisioning_id>/revoke")
@permission_required("pilot:manage")
def revoke_pilot_account(provisioning_id: str):
    if not _pilot_csrf_ok():
        return jsonify({"error": "csrf_validation_failed"}), 403
    context, failure = _manager_context()
    if failure:
        return failure
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"error": "json_object_required"}), 400
    try:
        result = _provisioning_service().revoke(
            provisioning_id=provisioning_id,
            manager_tenant_id=context.tenant_id,
            revoked_by=context.actor_id,
            reason=payload.get("reason"),
            audit_correlation_id=context.correlation_id,
        )
    except PilotProvisioningError as exc:
        return jsonify({"error": str(exc)}), 404 if "not_found" in str(exc) else 400
    except PilotAuthorizationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result.to_dict())


@pilot_provisioning_api.post("/activate")
def activate_pilot_account():
    if not _pilot_csrf_ok():
        return jsonify({"error": "csrf_validation_failed"}), 403
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "json_object_required"}), 400
    try:
        result = _provisioning_service().activate(
            token=payload.get("activation_token"),
            password=payload.get("password"),
            audit_correlation_id=request.headers.get("X-Correlation-ID") or "activation",
        )
    except PilotProvisioningError:
        # Unknown, expired, consumed, and revoked tokens share one response.
        return jsonify({"error": "activation_invalid"}), 400
    return jsonify({"status": "activated", "account": result.to_dict()}), 200

"""Authentication REST endpoints."""

from flask import Blueprint, current_app, jsonify, request, session
from sqlite3 import IntegrityError

from database.errors import DatabaseError
from .auth_service import AuthService
from .security import csrf_token


def _canonical_membership(user):
    authority = current_app.container.require("canonical_authority")
    identity = authority.identities.get_by_email(user.email)
    if identity is None:
        identity = authority.identities.create(user.email, display_name=user.username, actor_id=f"user-{user.id}")
    memberships = [m for m in authority.memberships.list_for_actor(identity.actor_id) if m.status == "active"]
    if not memberships:
        tenant = authority.tenants.create(f"{user.username} workspace", tenant_id=f"tenant-{user.id}")
        memberships = [authority.memberships.add(tenant.tenant_id, identity.actor_id, "analyst")]
    return identity, sorted(memberships, key=lambda item: item.tenant_id)[0]

auth_api = Blueprint("auth_api", __name__, url_prefix="/api/auth")


def _service() -> AuthService:
    return current_app.container.get("auth_service")


@auth_api.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    try:
        user = _service().register(data.get("username", ""), data.get("email", ""), data.get("password", ""), "analyst")
    except IntegrityError:
        return jsonify({"error": "user_exists"}), 409
    except DatabaseError as exc:
        if not isinstance(exc.__cause__, IntegrityError):
            raise
        return jsonify({"error": "user_exists"}), 409
    except ValueError:
        return jsonify({"error": "invalid_registration"}), 400
    try:
        _canonical_membership(user)
    except Exception:
        return jsonify({"error": "canonical_membership_initialization_failed"}), 500
    return jsonify(user.public()), 201


@auth_api.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    user = _service().authenticate(data.get("username", ""), data.get("password", ""))
    if not user:
        current_app.container.get("audit_service").record("FAILED_LOGIN", details={"username": data.get("username", "")})
        return jsonify({"error": "invalid_credentials"}), 401
    session.clear()
    session["user_id"] = user.id
    identity, membership = _canonical_membership(user)
    session["actor_id"] = identity.actor_id
    session["organization_id"] = membership.tenant_id
    session["canonical_principal"] = {"actor_id": identity.actor_id, "tenant_id": membership.tenant_id}
    session["csrf_token"] = csrf_token()
    current_app.container.get("audit_service").record("USER_LOGIN", user_id=user.id)
    payload = user.public()
    payload["csrf_token"] = session["csrf_token"]
    return jsonify(payload)


@auth_api.get("/csrf")
def csrf():
    if "csrf_token" not in session:
        session["csrf_token"] = csrf_token()
    return jsonify({"csrf_token": session["csrf_token"]})


@auth_api.post("/logout")
def logout():
    expected = session.get("csrf_token")
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    if not expected or supplied != expected:
        return jsonify({"error": "csrf_validation_failed"}), 403
    current_app.container.get("audit_service").record("USER_LOGOUT", user_id=session.get("user_id"))
    session.clear()
    return jsonify({"status": "logged_out"})


@auth_api.get("/me")
def me():
    user = _service().get_by_id(session.get("user_id"))
    if not user:
        return jsonify({"error": "authentication_required"}), 401
    return jsonify(user.public())

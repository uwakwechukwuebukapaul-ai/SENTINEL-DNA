"""Authentication REST endpoints."""

from flask import Blueprint, current_app, jsonify, request, session
from sqlite3 import IntegrityError

from .auth_service import AuthService

auth_api = Blueprint("auth_api", __name__, url_prefix="/api/auth")


def _service() -> AuthService:
    return current_app.container.get("auth_service")


@auth_api.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    try:
        user = _service().register(data.get("username", ""), data.get("email", ""), data.get("password", ""), data.get("role", "analyst"))
    except IntegrityError:
            return jsonify({"error": "user_exists"}), 409
    except ValueError:
        return jsonify({"error": "invalid_registration"}), 400
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
    current_app.container.get("audit_service").record("USER_LOGIN", user_id=user.id)
    return jsonify(user.public())


@auth_api.post("/logout")
def logout():
    current_app.container.get("audit_service").record("USER_LOGOUT", user_id=session.get("user_id"))
    session.clear()
    return jsonify({"status": "logged_out"})


@auth_api.get("/me")
def me():
    user = _service().get_by_id(session.get("user_id"))
    if not user:
        return jsonify({"error": "authentication_required"}), 401
    return jsonify(user.public())

"""Explicitly disabled-by-default Flask boundary for Entra OIDC."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from flask import Blueprint, current_app, g, jsonify, redirect, request, session

from services.auth.routes import REMEMBER_COOKIE, _csrf_ok, _login_session
from services.auth.security import csrf_token

from .entra_oidc import (
    EntraBindingRepository,
    EntraDiscovery,
    EntraJwtValidator,
    EntraOidcConfig,
    EntraOidcError,
    EntraTokenClient,
    ExternalSecretReferenceResolver,
    begin_transaction,
    consume_transaction,
)


def create_entra_blueprint() -> Blueprint | None:
    """Build the route only when an operator explicitly enables Entra OIDC."""
    if os.getenv("SENTINEL_DNA_ENTRA_OIDC_ENABLED", "0") != "1":
        return None
    try:
        config = EntraOidcConfig.from_environment()
        config.validate()
    except EntraOidcError:
        return None
    # Keep the concrete Entra flow under the enterprise identity namespace.
    # The generic enterprise blueprint remains responsible for provider
    # discovery and other provider adapters; it must not own these literal
    # Entra callback URLs.
    bp = Blueprint("entra_auth", __name__, url_prefix="/auth/enterprise/entra")

    secret_provider = ExternalSecretReferenceResolver()

    @bp.get("/login")
    def login():
        try:
            EntraDiscovery(config).validate()
            return redirect(begin_transaction(session, config))
        except Exception:
            return jsonify({"error": "authentication_unavailable"}), 503

    @bp.get("/callback")
    def callback():
        try:
            transaction = consume_transaction(session, request.args.get("state", ""))
            if request.args.get("error"):
                raise EntraOidcError("entra_provider_authentication_failed")
            code = str(request.args.get("code") or "").strip()
            if not code:
                raise EntraOidcError("entra_code_missing")
            token = EntraTokenClient(config, secret_provider).exchange(code, transaction["verifier"])
            verified = EntraJwtValidator(config).validate(token["id_token"], transaction["nonce"])
            binding = EntraBindingRepository().resolve(verified.identity)
            auth = current_app.container.require("auth_service")
            candidate = auth.get_by_id(binding["user_id"])
            user = auth.session_user(candidate.id, candidate.session_version) if candidate else None
            if user is None or not user.is_active or user.actor_id is None:
                raise EntraOidcError("entra_local_user_denied")
            authority = current_app.container.require("canonical_authority")
            tenant_id = user.tenant_id
            if not tenant_id:
                raise EntraOidcError("entra_local_tenant_missing")
            tenant, identity, membership = authority.resolve(tenant_id, user.actor_id)
            if identity.status != "active" or membership.status != "active":
                raise EntraOidcError("entra_local_membership_denied")
            _login_session(user, auth_method="entra_oidc")
            session["canonical_principal"].update({
                "identity": {
                    "issuer": verified.identity.issuer,
                    "tenant_id": verified.identity.tenant_id,
                    "object_id": verified.identity.object_id,
                    "subject_id": verified.identity.subject_id,
                },
                "roles": sorted(verified.roles),
            })
            return redirect("/")
        except Exception:
            return jsonify({"error": "authentication_failed"}), 401

    @bp.post("/logout")
    def logout():
        if not _csrf_ok():
            return jsonify({"error": "csrf_validation_failed"}), 403
        remembered = session.get("persistent_session_id")
        if remembered:
            current_app.container.require("auth_service").revoke_persistent_session(remembered)
        g.clear_remember_cookie = True
        session.clear()
        return jsonify({"status": "logged_out"})

    return bp

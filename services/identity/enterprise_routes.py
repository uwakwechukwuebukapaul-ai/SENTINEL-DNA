"""Configuration-gated browser endpoints for Entra, Okta, and Google Workspace."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, redirect, request, session

from services.auth.routes import _login_session, _audit
from .enterprise_providers import ProviderTenantTrustService


_PROVIDER_NAMES = {
    "entra": "Microsoft Entra ID",
    "okta": "Okta",
    "google": "Google Workspace",
}


def _operational_provider(provider: str, flow) -> dict | None:
    """Return public metadata only for a wired and locally valid OIDC flow."""
    provider = str(provider).strip().lower()
    if provider not in _PROVIDER_NAMES:
        return None
    if not callable(getattr(flow, "begin", None)) or not callable(getattr(flow, "complete", None)):
        return None
    configuration = getattr(flow, "configuration", None)
    if configuration is None or not callable(getattr(configuration, "validate", None)):
        return None
    try:
        configuration.validate()
    except Exception:
        return None
    health_check = getattr(flow, "health_check", None)
    if callable(health_check):
        try:
            if not health_check():
                return None
        except Exception:
            return None
    return {"id": provider, "name": _PROVIDER_NAMES[provider], "start_url": f"/auth/enterprise/{provider}/start"}


def operational_providers(flows) -> list[dict]:
    """Build login metadata from the configured enterprise flow registry."""
    if not isinstance(flows, dict):
        return []
    return [
        available
        for provider, flow in flows.items()
        if (available := _operational_provider(provider, flow)) is not None
    ]


def create_enterprise_identity_blueprint() -> Blueprint:
    bp = Blueprint("enterprise_identity", __name__, url_prefix="/auth/enterprise")

    @bp.get("/providers")
    def providers():
        return jsonify({"providers": operational_providers(current_app.config.get("ENTERPRISE_OIDC_FLOWS", {}))})

    @bp.get("/<provider>/start")
    def start(provider: str):
        provider = provider.lower()
        flows = current_app.config.get("ENTERPRISE_OIDC_FLOWS", {})
        flow = flows.get(provider)
        if flow is None:
            return jsonify({"error": "identity_provider_unavailable"}), 503
        try:
            location, state, nonce = flow.begin()
            session["enterprise_oidc"] = {"provider": provider, "state": state, "nonce": nonce}
            _audit("enterprise_oidc_started", method=f"{provider}_oidc", outcome="started")
            return redirect(location)
        except Exception:
            return jsonify({"error": "identity_provider_unavailable"}), 503

    @bp.get("/<provider>/callback")
    def callback(provider: str):
        transaction = session.pop("enterprise_oidc", None)
        flows = current_app.config.get("ENTERPRISE_OIDC_FLOWS", {})
        flow = flows.get(provider.lower())
        if not transaction or flow is None or transaction.get("provider") != provider.lower():
            return jsonify({"error": "authentication_failed"}), 401
        try:
            principal = flow.complete(request.args, transaction)
            auth = current_app.container.require("auth_service")
            # Provider subjects must be explicitly linked to a local identity;
            # email similarity is never sufficient for enterprise login.
            resolver = getattr(flow, "resolve_bound_user", None)
            user = resolver(auth, principal) if callable(resolver) else auth.identity_user(principal.provider, principal.external_subject or principal.subject)
            if user is None or not user.is_active:
                raise ValueError("local_identity_not_bound")
            if not user.tenant_id:
                raise ValueError("local_tenant_missing")
            ProviderTenantTrustService(auth.db).require(
                principal.provider,
                flow.configuration.issuer,
                principal.tenant_id,
                user.tenant_id,
            )
            _audit("enterprise_oidc_success", user_id=user.id, method=f"{provider.lower()}_oidc", outcome="success")
            return redirect("/") if _login_session(user, auth_method=f"{provider.lower()}_oidc") else (jsonify({"error": "authentication_failed"}), 401)
        except Exception:
            _audit("enterprise_oidc_failed", method=f"{provider.lower()}_oidc", outcome="failure", reason="provider_validation_failed")
            return jsonify({"error": "authentication_failed"}), 401

    return bp

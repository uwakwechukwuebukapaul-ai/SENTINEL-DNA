"""Configuration-gated Flask OIDC routes."""
from __future__ import annotations
import os
from flask import Blueprint, current_app, redirect, request, session, jsonify
from .oidc_config import OidcRuntimeConfiguration, OidcSecretProvider
from .oidc_browser import OidcAuthorizationCodeFlow, OidcBrowserConfiguration, OidcBrowserError

class OidcRouteConfiguration:
    @classmethod
    def from_environment(cls):
        configuration = OidcRuntimeConfiguration.from_environment()
        return configuration if configuration.is_ready(OidcSecretProvider(), production=os.getenv("SENTINEL_DNA_ENV", "development") == "production") else None

def create_oidc_blueprint(flow: OidcAuthorizationCodeFlow | None):
    if flow is None: return None
    bp = Blueprint("oidc_auth", __name__, url_prefix="/auth/oidc")
    @bp.get("/login")
    def login():
        try: return redirect(flow.begin(session))
        except Exception: return jsonify({"error": "authentication_unavailable"}), 503
    @bp.get("/callback")
    def callback():
        try:
            flow.complete(session, request.args)
            return redirect("/")
        except OidcBrowserError: return jsonify({"error": "authentication_failed"}), 401
        except Exception: return jsonify({"error": "authentication_failed"}), 401
    @bp.post("/logout")
    def logout():
        flow.logout(session)
        return jsonify({"status": "logged_out"})
    return bp

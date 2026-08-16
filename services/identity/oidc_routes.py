"""Configuration-gated Flask OIDC routes."""
from __future__ import annotations
import os
from flask import Blueprint, current_app, redirect, request, session, jsonify
from .oidc_browser import OidcAuthorizationCodeFlow, OidcBrowserConfiguration, OidcBrowserError

class OidcRouteConfiguration:
    REQUIRED = ("OIDC_AUTHORIZATION_ENDPOINT", "OIDC_REDIRECT_URI", "OIDC_CLIENT_ID")
    @classmethod
    def from_environment(cls):
        values = {name: os.getenv(name, "").strip() for name in cls.REQUIRED}
        return values if all(values.values()) else None

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


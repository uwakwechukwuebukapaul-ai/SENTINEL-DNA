"""
Sentinel DNA Application Factory.

Bootstraps enterprise services
and API layers.
"""

import logging
import os
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, g, request, send_from_directory, session
from jinja2 import ChoiceLoader, FileSystemLoader


from config.runtime import RuntimeConfig
from database.connection import database



def create_app():

    app = Flask(
        __name__
    )
    runtime_config = RuntimeConfig.from_environment()
    runtime_config.validate()
    app.config.update(ENVIRONMENT=runtime_config.environment, DEBUG=runtime_config.debug, SECRET_KEY=runtime_config.secret_key, SESSION_COOKIE_SECURE=runtime_config.secure_cookies, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", PERMANENT_SESSION_LIFETIME=timedelta(days=30), SESSION_REFRESH_EACH_REQUEST=False, AUTH_LEGACY_JSON_COMPAT=runtime_config.environment != "production", DEMO_DATA_ENABLED=os.getenv("SENTINEL_DNA_DEMO_DATA", "0" if runtime_config.environment == "production" else "1") == "1", PILOT_ACCESS_REQUIRED=runtime_config.pilot_access_required, CONFIG_SOURCE_CLASSIFICATION=runtime_config.config_source_classification, DATABASE_TARGET_CLASSIFICATION=runtime_config.database_target_classification)
    if runtime_config.environment == "production":
        app.config.update(PROPAGATE_EXCEPTIONS=False, TRAP_HTTP_EXCEPTIONS=False)
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    database.database_path = runtime_config.database_path

    # Reuse the existing Analyst Workspace blueprint without importing the
    # separate dashboard application or duplicating workspace logic.
    from dashboard.analyst_workspace import analyst_workspace

    app.jinja_loader = ChoiceLoader(
        [
            app.jinja_loader,
            FileSystemLoader(str(Path(__file__).resolve().parent.parent / "dashboard" / "templates")),
        ]
    )


    # ==================================
    # SERVICE CONTAINER
    # ==================================

    from services.core.application_container import build_container
    app.container = build_container()
    # OIDC routes remain disabled until a concrete verifier, token client,
    # provider-tenant trust, and identity-binding wiring are supplied.
    app.config["OIDC_ROUTES_ENABLED"] = False
    from services.automation import automation_api
    from services.integrations import integrations_api
    from services.detection import detection_api
    from services.adversary import adversary_api
    from services.validation import validation_api
    from services.tenancy import tenancy_api
    from services.connectors import connectors_api
    from services.streaming import streaming_api
    from services.intelligence.reasoning import reasoning_api
    from services.intelligence.chat import chat_api
    from services.governance.routes import governance_api
    from services.marketplace.routes import marketplace_api
    from services.incidents.routes import incidents_api
    from services.api_management.routes import api_management_api
    from services.billing.routes import billing_api
    from services.mssp.routes import mssp_api
    from services.compliance.routes import compliance_api
    from services.mlops.routes import mlops_api
    from services.monitoring.routes import monitoring_api
    from services.customer_success.routes import customer_success_api
    from services.product_analytics.routes import product_analytics_api
    from services.pilot_reports.routes import pilot_reports_api
    from services.pilot_management.routes import (
        pilot_authorization_api,
        pilot_management_api,
        pilot_provisioning_api,
    )
    from services.support.routes import support_api
    from services.exercises.routes import exercise_api
    from services.auth import auth_api
    from services.audit import audit_api
    from services.auth.routes import enforce_current_session, restore_persistent_session
    from services.core.pilot_boundary import enforce_pilot_analyst_boundary
    from dashboard.browser_routes import browser
    app.register_blueprint(auth_api)
    app.register_blueprint(audit_api)
    app.register_blueprint(browser)
    app.register_blueprint(automation_api)
    app.register_blueprint(integrations_api)
    app.register_blueprint(detection_api)
    app.register_blueprint(adversary_api)
    app.register_blueprint(validation_api)
    app.register_blueprint(tenancy_api)
    app.register_blueprint(connectors_api)
    app.register_blueprint(streaming_api)
    app.register_blueprint(reasoning_api)
    app.register_blueprint(chat_api)
    app.register_blueprint(governance_api)
    app.register_blueprint(marketplace_api)
    app.register_blueprint(incidents_api)
    app.register_blueprint(api_management_api)
    app.register_blueprint(billing_api)
    app.register_blueprint(mssp_api); app.register_blueprint(compliance_api); app.register_blueprint(mlops_api)
    app.register_blueprint(monitoring_api)
    app.register_blueprint(customer_success_api)
    app.register_blueprint(product_analytics_api)
    app.register_blueprint(pilot_reports_api)
    app.register_blueprint(pilot_management_api)
    app.register_blueprint(pilot_authorization_api)
    app.register_blueprint(pilot_provisioning_api)
    app.register_blueprint(support_api)
    app.register_blueprint(exercise_api)

    @app.before_request
    def restore_authentication_cookie():
        restore_persistent_session()

    @app.before_request
    def enforce_authentication_epoch():
        enforce_current_session()

    @app.before_request
    def enforce_pilot_boundary():
        return enforce_pilot_analyst_boundary()


    # ==================================
    # API BLUEPRINTS
    # ==================================

    from services.api.investigations import (
        investigation_bp,
        register_compatibility_routes,
    )


    app.register_blueprint(
        investigation_bp
    )


    register_compatibility_routes(
        app
    )

    from services.api.investigations.routes import _execute_investigation

    @app.post("/api/investigations/run")
    def run_investigation_compatibility():
        payload = request.get_json(silent=True) or {}
        if not payload.get("case_id"):
            return jsonify({"status": "completed", "success": True, "case_id": None}), 200
        return _execute_investigation()


    from services.api.soc import soc_api
    app.register_blueprint(soc_api)
    app.register_blueprint(analyst_workspace)

    @app.get("/workspace/dashboard/static/<path:filename>")
    def dashboard_static(filename: str):
        return send_from_directory(
            Path(__file__).resolve().parent.parent / "dashboard" / "static",
            filename,
        )


    # ==================================
    # HEALTH CHECK
    # ==================================

    @app.route("/")
    def home():

        return {

            "status": "running",

            "service": "Sentinel DNA",

            "version": "1.0",

        }

    @app.get("/health")
    def health():
        try:
            if not database.health_check():
                raise RuntimeError("database health check failed")
            return {"status": "ok", "service": "sentinel-dna", "database": "ok"}
        except Exception:
            return {"status": "degraded", "database": "unavailable"}, 503

    @app.get("/ready")
    def ready():
        try:
            app.container.validate_required(("investigation_coordinator", "investigation_orchestrator", "audit_service", "audit_read_service"))
            if not database.health_check():
                raise RuntimeError("database health check failed")
            return {"status": "ready", "database": "ok", "services": "registered"}
        except Exception:
            return {"status": "not_ready"}, 503

    @app.after_request
    def add_runtime_headers(response):
        from services.auth.routes import REMEMBER_COOKIE
        if getattr(g, "remember_cookie", None):
            response.set_cookie(REMEMBER_COOKIE, g.remember_cookie, max_age=30 * 24 * 60 * 60, httponly=True, secure=bool(app.config.get("SESSION_COOKIE_SECURE")), samesite="Lax", path="/")
        if getattr(g, "clear_remember_cookie", False):
            response.delete_cookie(REMEMBER_COOKIE, path="/")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        context = getattr(g, "security_context", None)
        correlation_id = getattr(context, "correlation_id", None) or request.headers.get("X-Correlation-ID") or str(uuid4())
        response.headers.setdefault("X-Correlation-ID", correlation_id)
        return response


    return app

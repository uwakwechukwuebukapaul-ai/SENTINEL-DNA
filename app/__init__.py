"""
Sentinel DNA Application Factory.

Bootstraps enterprise services
and API layers.
"""

from flask import Flask, jsonify, request


from services.core.application_container import (
    build_container,
)
from config.runtime import RuntimeConfig
from database.connection import database



def create_app():

    app = Flask(
        __name__
    )
    runtime_config = RuntimeConfig.from_environment()
    runtime_config.validate()
    app.config.update(ENVIRONMENT=runtime_config.environment, DEBUG=runtime_config.debug, SECRET_KEY=runtime_config.secret_key, SESSION_COOKIE_SECURE=runtime_config.secure_cookies)


    # ==================================
    # SERVICE CONTAINER
    # ==================================

    app.container = build_container()
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
    from services.pilot_management.routes import pilot_management_api
    from services.support.routes import support_api
    from services.exercises.routes import exercise_api
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
    app.register_blueprint(pilot_management_api); app.register_blueprint(support_api)
    app.register_blueprint(exercise_api)


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


    from services.api.dashboard.routes import (
        dashboard_bp,
    )


    app.register_blueprint(
        dashboard_bp
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
            with database.session() as connection:
                connection.execute("SELECT 1").fetchone()
            return {"status": "ok", "service": "sentinel-dna", "database": "ok"}
        except Exception:
            return {"status": "degraded", "database": "unavailable"}, 503

    @app.get("/ready")
    def ready():
        try:
            app.container.validate_required(("investigation_coordinator", "investigation_orchestrator", "audit_service"))
            with database.session() as connection:
                connection.execute("SELECT 1").fetchone()
            return {"status": "ready", "database": "ok", "services": "registered"}
        except Exception:
            return {"status": "not_ready"}, 503


    return app

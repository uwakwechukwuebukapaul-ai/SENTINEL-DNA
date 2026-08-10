"""
Sentinel DNA Application Factory.

Bootstraps enterprise services
and API layers.
"""

from flask import Flask


from services.core.application_container import (
    build_container,
)



def create_app():

    app = Flask(
        __name__
    )


    # ==================================
    # SERVICE CONTAINER
    # ==================================

    app.container = build_container()


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


    return app
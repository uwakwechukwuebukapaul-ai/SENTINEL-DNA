"""
Sentinel DNA Application Entry Point.

Registers API and platform services.
"""

from __future__ import annotations

from flask import Flask


def create_app() -> Flask:
    """
    Application factory.
    """

    app = Flask(
        __name__
    )


    # ==================================
    # API BLUEPRINTS
    # ==================================

    from services.api.investigations import (
        investigation_bp,
        register_compatibility_routes,
    )

    from services.api.dashboard.routes import (
        dashboard_bp,
    )


    # Investigation API

    app.register_blueprint(
        investigation_bp
    )


    register_compatibility_routes(
        app
    )


    # Dashboard API

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



# ==================================
# DEVELOPMENT SERVER
# ==================================

if __name__ == "__main__":

    app = create_app()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )
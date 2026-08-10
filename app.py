"""
Sentinel DNA Application Entry Point.

Registers API and platform services.
"""

from flask import Flask

from services.api.investigations import (
    investigation_bp,
)


def create_app():

    app = Flask(
        __name__
    )


    # ==================================
    # API BLUEPRINTS
    # ==================================

    app.register_blueprint(
        investigation_bp
    )


    # ==================================
    # HEALTH CHECK
    # ==================================

    @app.route("/")
    def home():

        return {
            "status": "running",
            "service": "Sentinel DNA",
            "version": "1.0"
        }


    return app



app = create_app()



if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )
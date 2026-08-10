"""
Investigation API Package.

Exports investigation blueprint
and compatibility routes.
"""

from flask import Flask

from .routes import (
    investigation_bp,
    run_investigation,
)


def register_compatibility_routes(
    app: Flask,
):
    """
    Register legacy endpoint.

    Keeps backwards compatibility
    with older API clients.
    """

    @app.route(
        "/investigate",
        methods=[
            "POST",
        ],
    )
    def investigate():

        return run_investigation()



__all__ = [
    "investigation_bp",
    "register_compatibility_routes",
]
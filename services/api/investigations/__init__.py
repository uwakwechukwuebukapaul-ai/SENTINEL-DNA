"""
Sentinel DNA Investigation API Package.

Exports the canonical investigation blueprint
and the legacy root compatibility endpoint.
"""

from __future__ import annotations

from flask import Flask

from .routes import (
    investigation_bp,
    run_investigation,
)


def register_compatibility_routes(
    app: Flask,
) -> None:
    """
    Register the legacy root investigation endpoint.

    Historical clients may call:

        POST /investigate

    The endpoint delegates to the canonical investigation
    API implementation.
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
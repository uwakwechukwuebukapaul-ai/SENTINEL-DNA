"""
Sentinel DNA Investigation API package.

Exports:
- Canonical investigation blueprint
- Legacy compatibility blueprint
- Registration helper
"""

from .routes import (
    investigations_api,
    legacy_investigation_api,
)


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

# Older modules/tests expect:
#
# from services.api.investigations import investigation_bp
#
# Keep alias alive.

investigation_bp = investigations_api



# ============================================================
# BLUEPRINT REGISTRATION
# ============================================================


def register_compatibility_routes(
    app,
):
    """
    Register investigation API routes.

    Supports:
        POST /api/investigations
        POST /investigate

    Safe for repeated application initialization.
    """

    blueprints = [
        investigations_api,
        legacy_investigation_api,
    ]


    for blueprint in blueprints:

        if blueprint.name not in app.blueprints:

            app.register_blueprint(
                blueprint
            )



# ============================================================
# PUBLIC EXPORTS
# ============================================================


__all__ = [
    "investigation_bp",
    "investigations_api",
    "legacy_investigation_api",
    "register_compatibility_routes",
]
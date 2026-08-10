"""
Sentinel DNA Investigation API.

Provides investigation execution endpoints.
"""

from flask import (
    Blueprint,
    request,
    jsonify,
)


investigation_bp = Blueprint(
    "investigations",
    __name__,
    url_prefix="/api/investigations",
)


def _handle_investigation():
    """
    Shared investigation request handler.
    """

    payload = request.get_json(
        silent=True
    ) or {}


    return jsonify(
        {
            "status": "received",
            "investigation": payload,
        }
    ), 200



# =================================================
# PRIMARY API ENDPOINT
# =================================================

@investigation_bp.route(
    "/run",
    methods=[
        "POST",
    ],
)
def run_investigation():

    return _handle_investigation()



# =================================================
# LEGACY COMPATIBILITY ENDPOINT
# =================================================

def register_compatibility_routes(app):
    """
    Register legacy endpoint.

    Keeps older integrations working:
    POST /investigate
    """

    @app.route(
        "/investigate",
        methods=[
            "POST",
        ],
    )
    def investigate():

        return _handle_investigation()
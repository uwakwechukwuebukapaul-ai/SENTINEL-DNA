"""
Stable REST endpoints for Sentinel DNA investigations.

Supports:
- Canonical API:
    POST /api/investigations
    GET  /api/investigations/<case_id>

- Legacy compatibility:
    POST /investigate

Architecture:
Client
  |
  v
API Blueprint
  |
  v
Investigation Coordinator
  |
  v
Investigation Pipeline
"""

from __future__ import annotations


from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
)


from .schemas import (
    investigation_request,
    investigation_response,
)
from services.core.serialization import serialize
from services.core.security_context import authorize_investigation


# ============================================================
# BLUEPRINTS
# ============================================================


investigations_api = Blueprint(
    "investigations_api",
    __name__,
    url_prefix="/api/investigations",
)


legacy_investigation_api = Blueprint(
    "legacy_investigation_api",
    __name__,
)


# ============================================================
# DEPENDENCY ACCESS
# ============================================================


def _coordinator():

    return current_app.container.get(
        "investigation_coordinator"
    )


# ============================================================
# REQUEST HANDLER
# ============================================================


def _execute_investigation():

    payload = request.get_json(
        silent=True
    ) or {}

    allowed, error = authorize_investigation(payload, write=True)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403


    case_id, alert, artifacts, error = investigation_request(
        payload
    )


    if error:

        return jsonify(
            {
                "error": error,
            }
        ), 400


    result = _coordinator().investigate(
        case_id=case_id,
        alert=alert,
        artifacts=artifacts,
    )


    return jsonify(
        investigation_response(
            result
        )
    ), 200



# ============================================================
# CANONICAL API
# ============================================================


@investigations_api.post("")
def create_investigation():

    return _execute_investigation()


@investigations_api.get(
    "/<case_id>"
)
def get_investigation(
    case_id: str,
):

    coordinator = _coordinator()


    intelligence = (
        coordinator
        .intelligence_repository
        .get_by_case_id(
            case_id
        )
    )

    allowed, error = authorize_investigation(_serialize(intelligence), write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403


    report = (
        coordinator
        .get_report_by_case_id(
            case_id
        )
    )


    if intelligence is None and report is None:

        return jsonify(
            {
                "error": "investigation_not_found"
            }
        ), 404


    return jsonify(
        {
            "case_id": case_id,

            "intelligence":
                _serialize(intelligence),

            "timeline":
                (
                    _serialize(
                        intelligence
                    )
                    or {}
                ).get(
                    "timeline",
                    []
                ),

            "report":
                _serialize(report),
        }
    )



@investigations_api.get(
    "/<case_id>/report"
)
def get_investigation_report(
    case_id: str,
):

    report = (
        _coordinator()
        .get_report_by_case_id(
            case_id
        )
    )


    if report is None:

        return jsonify(
            {
                "error": "report_not_found"
            }
        ),404

    allowed, error = authorize_investigation(_serialize(report), write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403


    return jsonify(
        _serialize(report)
    )



@investigations_api.get(
    "/<case_id>/timeline"
)
def get_investigation_timeline(
    case_id: str,
):

    intelligence = (
        _coordinator()
        .intelligence_repository
        .get_by_case_id(
            case_id
        )
    )


    if intelligence is None:

        return jsonify(
            {
                "error":
                    "investigation_not_found"
            }
        ),404

    allowed, error = authorize_investigation(_serialize(intelligence), write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403


    data = _serialize(
        intelligence
    )


    return jsonify(
        {
            "case_id": case_id,

            "timeline":
                data.get(
                    "timeline",
                    []
                ),
        }
    )



# ============================================================
# LEGACY COMPATIBILITY
# ============================================================


@legacy_investigation_api.post(
    "/investigate"
)
def legacy_investigate():

    return _execute_investigation()



# ============================================================
# SERIALIZATION SUPPORT
# ============================================================


def _serialize(value):
    return serialize(value)



# ============================================================
# APP REGISTRATION HELPER
# ============================================================


def register_compatibility_routes(
    app,
):

    """
    Register legacy routes.

    Keeps old Sentinel DNA clients working.
    """

    app.register_blueprint(
        legacy_investigation_api
    )

"""
Investigation API Routes.

REST interface for Sentinel DNA investigations.
"""

from flask import (
    Blueprint,
    jsonify,
    request,
)

from .controller import (
    InvestigationController,
)

from .schemas import (
    InvestigationRequest,
)


investigation_bp = Blueprint(
    "investigations",
    __name__,
    url_prefix="/api/investigations",
)


controller = InvestigationController()


@investigation_bp.route(
    "/run",
    methods=["POST"],
)
def run_investigation():

    try:

        payload = request.get_json(
            silent=True
        ) or {}


        schema = InvestigationRequest(
            payload
        )


        schema.validate()


        result = controller.run(
            artifacts=schema.artifacts,
            case_id=schema.case_id,
        )


        return jsonify(
            result
        ), 200


    except ValueError as exc:

        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 400


    except Exception as exc:

        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 500
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
    session,
)


from .schemas import (
    investigation_request,
    investigation_response,
)
from services.core.serialization import serialize
from services.core.security_context import authorize_investigation
from services.core.security_context import request_context
from services.observability import ObservabilityService
import time


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


def _investigation_execution_failure(observer: ObservabilityService, case_id: str, exc: Exception):
    """Return a safe API error while keeping failure details internal."""
    try:
        context = request_context()
        observer.event(
            "investigation_api_failed",
            case_id=case_id,
            operation="investigate",
            component="api",
            status="failed",
            error_type=type(exc).__name__,
            correlation_id=context.correlation_id,
            tenant_id=context.tenant_id,
        )
    except Exception:
        pass
    return jsonify({"error": {"code": "INVESTIGATION_EXECUTION_FAILED", "message": "Investigation execution failed"}}), 500


# ============================================================
# REQUEST HANDLER
# ============================================================


def _execute_investigation():
    started = time.perf_counter()
    observer = ObservabilityService()

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


    security_context = request_context()
    try:
        result = _coordinator().investigate(
            case_id=case_id,
            alert=alert,
            artifacts=artifacts,
            correlation_id=security_context.correlation_id,
<<<<<<< HEAD
            tenant_id=security_context.tenant_id,
            actor_id=getattr(security_context, "actor_id", None) or getattr(security_context, "user_id", None),
=======
>>>>>>> 71a3dc4 (ops: harden production runtime for investigator v2)
        )
    except PermissionError:
        raise
    except Exception as exc:
        return _investigation_execution_failure(observer, case_id, exc)


    observer.event("investigation_api_completed", case_id=case_id, operation="investigate", component="api", status="completed", duration_ms=round((time.perf_counter() - started) * 1000, 2), correlation_id=security_context.correlation_id, tenant_id=security_context.tenant_id)
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


@investigations_api.get("/<case_id>/view")
def get_investigation_view(case_id: str):
    """Return the canonical, tenant-scoped analyst investigation view."""
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id:
        return jsonify({"error": "organization_context_required"}), 403
    try:
        view = _coordinator().get_investigation_view(case_id, context)
    except PermissionError:
        return jsonify({"error": "investigation_not_found"}), 404
    if view is None:
        return jsonify({"error": "investigation_not_found"}), 404
    return jsonify(view)


@investigations_api.get("/<case_id>/metrics")
def get_investigation_metrics(case_id: str):
    """Return read-only investigation-quality outcome metrics."""
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id:
        return jsonify({"error": "organization_context_required"}), 403
    try:
        metrics = _coordinator().get_investigation_metrics(case_id, context)
    except PermissionError:
        return jsonify({"error": "investigation_not_found"}), 404
    except ValueError:
        return jsonify({"error": "investigation_metrics_unavailable"}), 503
    if metrics is None:
        return jsonify({"error": "investigation_not_found"}), 404
    return jsonify(metrics)


@investigations_api.post("/<case_id>/feedback")
def submit_investigation_feedback(case_id: str):
    context = request_context()
    analyst_id = getattr(context, "actor_id", None) or session.get("actor_id") or getattr(context, "user_id", None)
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=True)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id or not analyst_id:
        return jsonify({"error": "analyst_identity_required"}), 403
    try:
        feedback = _coordinator().submit_feedback(
            case_id, request.get_json(silent=True) or {},
            tenant_id=str(context.tenant_id), analyst_id=str(analyst_id),
        )
    except LookupError:
        return jsonify({"error": "investigation_not_found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"success": True, "feedback": feedback.to_dict()}), 201


@investigations_api.get("/<case_id>/feedback")
def get_investigation_feedback(case_id: str):
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id:
        return jsonify({"error": "organization_context_required"}), 403
    try:
        feedback = _coordinator().get_feedback(case_id, str(context.tenant_id))
    except LookupError:
        return jsonify({"error": "investigation_not_found"}), 404
    return jsonify({"case_id": case_id, "feedback": feedback})


@investigations_api.get("/feedback/analytics")
def get_feedback_analytics():
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id:
        return jsonify({"error": "organization_context_required"}), 403
    allowed_filters = {"start", "end", "case_id", "investigation_id", "granularity"}
    if set(request.args) - allowed_filters:
        return jsonify({"error": "invalid_feedback_analytics_filter"}), 400
    try:
        payload = _coordinator().get_feedback_analytics(
            str(context.tenant_id), start=request.args.get("start"), end=request.args.get("end"),
            case_id=request.args.get("case_id"), investigation_id=request.args.get("investigation_id"),
            granularity=request.args.get("granularity", "daily"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    payload.pop("tenant_id", None)
    return jsonify(payload)


@investigations_api.get("/<case_id>/quality/evidence")
def get_evidence_linked_quality(case_id: str):
    """Return authorized, descriptive evidence-linked analyst outcome associations."""
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id:
        return jsonify({"error": "organization_context_required"}), 403
    allowed_filters = {"decision", "evidence_type", "finding_type", "recommendation_type", "limit"}
    if set(request.args) - allowed_filters:
        return jsonify({"error": "invalid_quality_filter"}), 400
    try:
        limit = int(request.args.get("limit", "50"))
        payload = _coordinator().get_evidence_linked_quality(
            case_id,
            str(context.tenant_id),
            decision=request.args.get("decision"),
            evidence_type=request.args.get("evidence_type"),
            finding_type=request.args.get("finding_type"),
            recommendation_type=request.args.get("recommendation_type"),
            limit=limit,
        )
    except LookupError:
        return jsonify({"error": "investigation_not_found"}), 404
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_quality_filter"}), 400
    return jsonify(payload)



# ============================================================
# LEGACY COMPATIBILITY
# ============================================================


@investigations_api.get("/<investigation_id>/quality")
def get_investigation_quality(investigation_id: str):
    """Return the authorized durable quality assessment for an investigation."""
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id:
        return jsonify({"error": "organization_context_required"}), 403
    getter = getattr(_coordinator(), "get_quality_assessment", None)
    if not callable(getter):
        return jsonify({"error": "investigation_quality_unavailable"}), 503
    try:
        quality = getter(investigation_id, context)
    except PermissionError:
        return jsonify({"error": "forbidden"}), 403
    except Exception:
        return jsonify({"error": "investigation_quality_unavailable"}), 500
    if quality is None:
        return jsonify({"error": "investigation_not_found"}), 404
    return jsonify({"quality_assessment": quality})


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

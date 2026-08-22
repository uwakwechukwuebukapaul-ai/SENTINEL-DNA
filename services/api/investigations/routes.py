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
    Response,
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
            tenant_id=security_context.tenant_id,
            actor_id=getattr(security_context, "actor_id", None) or getattr(security_context, "user_id", None),
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


@investigations_api.post("/<case_id>/collaboration")
def add_investigation_collaboration(case_id: str):
    context = request_context()
    actor_id = getattr(context, "actor_id", None) or session.get("actor_id") or getattr(context, "user_id", None)
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=True)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id or not actor_id:
        return jsonify({"error": "analyst_identity_required"}), 403
    try:
        event = _coordinator().add_collaboration_event(case_id, request.get_json(silent=True) or {}, tenant_id=str(context.tenant_id), actor_id=str(actor_id))
    except LookupError:
        return jsonify({"error": "investigation_not_found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    event.pop("tenant_id", None)
    return jsonify({"success": True, "event": event}), 201


@investigations_api.get("/<case_id>/collaboration")
def get_investigation_collaboration(case_id: str):
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id:
        return jsonify({"error": "organization_context_required"}), 403
    try:
        events = _coordinator().get_collaboration(case_id, str(context.tenant_id))
    except LookupError:
        return jsonify({"error": "investigation_not_found"}), 404
    for event in events:
        event.pop("tenant_id", None)
    return jsonify({"version": "analyst-collaboration-v1", "case_id": case_id, "events": events})


@investigations_api.post("/<case_id>/notes")
def add_analyst_note(case_id: str):
    context = request_context(); actor_id = getattr(context, "actor_id", None) or session.get("actor_id") or getattr(context, "user_id", None)
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=True)
    if not allowed: return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id or not actor_id: return jsonify({"error": "analyst_identity_required"}), 403
    payload = request.get_json(silent=True) or {}
    payload["event_kind"] = "note" if payload.get("event_kind") == "handoff" else payload.get("event_kind", "note")
    try:
        event = _coordinator().add_collaboration_event(case_id, payload, tenant_id=str(context.tenant_id), actor_id=str(actor_id))
    except LookupError: return jsonify({"error": "investigation_not_found"}), 404
    except ValueError as exc: return jsonify({"error": str(exc)}), 400
    event.pop("tenant_id", None)
    return jsonify({"success": True, "event": event}), 201


@investigations_api.post("/<case_id>/decision")
def post_analyst_decision(case_id: str):
    return submit_investigation_feedback(case_id)


@investigations_api.get("/<case_id>/audit-timeline")
def get_investigation_audit_timeline(case_id: str):
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    try:
        timeline = _coordinator().get_audit_timeline(case_id, context)
    except LookupError:
        return jsonify({"error": "investigation_not_found"}), 404
    return jsonify({"version": "investigation-audit-timeline-v1", "case_id": case_id, "events": timeline})


@investigations_api.get("/<case_id>/evidence-review")
def get_evidence_review(case_id: str):
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id:
        return jsonify({"error": "organization_context_required"}), 403
    try:
        reviews = _coordinator().get_evidence_reviews(case_id, str(context.tenant_id))
    except LookupError:
        return jsonify({"error": "investigation_not_found"}), 404
    return jsonify({"version": "evidence-review-v1", "case_id": case_id, "reviews": reviews})


@investigations_api.get("/review-queue")
def get_review_queue():
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id:
        return jsonify({"error": "organization_context_required"}), 403
    states = [item for item in request.args.get("states", "").split(",") if item] or None
    return jsonify({"version": "evidence-review-queue-v1", "items": _coordinator().get_review_queue(str(context.tenant_id), states=states, priority=request.args.get("priority"), assigned_to=request.args.get("assigned_to"))})


@investigations_api.post("/<case_id>/evidence-review")
def post_evidence_review(case_id: str):
    context = request_context()
    actor_id = getattr(context, "actor_id", None) or session.get("actor_id") or getattr(context, "user_id", None)
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=True)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id or not actor_id:
        return jsonify({"error": "analyst_identity_required"}), 403
    payload = request.get_json(silent=True) or {}
    try:
        review = _coordinator().review_evidence(case_id, payload.get("evidence_id"), payload.get("new_state", "reviewed"), payload.get("reason", ""), tenant_id=str(context.tenant_id), actor_id=str(actor_id), priority=payload.get("priority", "normal"), assigned_to=payload.get("assigned_to"), review_deadline=payload.get("review_deadline"))
    except LookupError:
        return jsonify({"error": "investigation_not_found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    review.pop("tenant_id", None)
    return jsonify({"success": True, "review": review}), 201


@investigations_api.get("/<case_id>/assignments")
def get_case_assignments(case_id: str):
    context = request_context(); allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed: return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    try: items = _coordinator().get_assignments(case_id, str(context.tenant_id))
    except LookupError: return jsonify({"error": "investigation_not_found"}), 404
    return jsonify({"version": "case-assignment-v1", "case_id": case_id, "assignments": items})


@investigations_api.post("/<case_id>/assignment")
def post_case_assignment(case_id: str):
    context = request_context(); actor_id = getattr(context, "actor_id", None) or session.get("actor_id") or getattr(context, "user_id", None)
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=True)
    if not allowed: return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id or not actor_id: return jsonify({"error": "analyst_identity_required"}), 403
    try: event = _coordinator().assign_case(case_id, request.get_json(silent=True) or {}, tenant_id=str(context.tenant_id), actor_id=str(actor_id))
    except LookupError: return jsonify({"error": "investigation_not_found"}), 404
    except ValueError as exc: return jsonify({"error": str(exc)}), 400
    event.pop("tenant_id", None); return jsonify({"success": True, "assignment": event}), 201


@investigations_api.get("/<case_id>/sla")
def get_case_sla(case_id: str):
    context = request_context(); allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed: return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    try: value = _coordinator().case_lifecycle_repository.latest_sla(case_id, tenant_id=str(context.tenant_id))
    except Exception: value = None
    return jsonify({"version": "investigation-sla-v1", "case_id": case_id, "sla": value})


@investigations_api.post("/<case_id>/escalation")
def post_case_escalation(case_id: str):
    context = request_context(); actor_id = getattr(context, "actor_id", None) or session.get("actor_id") or getattr(context, "user_id", None)
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=True)
    if not allowed: return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id or not actor_id: return jsonify({"error": "analyst_identity_required"}), 403
    try: event = _coordinator().escalate_case(case_id, request.get_json(silent=True) or {}, tenant_id=str(context.tenant_id), actor_id=str(actor_id))
    except LookupError: return jsonify({"error": "investigation_not_found"}), 404
    except ValueError as exc: return jsonify({"error": str(exc)}), 400
    event.pop("tenant_id", None); return jsonify({"success": True, "escalation": event}), 201


@investigations_api.get("/<case_id>/compliance-export")
def get_compliance_export(case_id: str):
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    try:
        export = _coordinator().get_compliance_export(case_id, context)
    except (LookupError, PermissionError):
        return jsonify({"error": "investigation_not_found"}), 404
    if export is None:
        return jsonify({"error": "investigation_not_found"}), 404
    return jsonify(export)


@investigations_api.post("/<case_id>/closure")
def post_case_closure(case_id: str):
    context = request_context()
    actor_id = getattr(context, "actor_id", None) or session.get("actor_id") or getattr(context, "user_id", None)
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=True)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id or not actor_id:
        return jsonify({"error": "analyst_identity_required"}), 403
    payload = request.get_json(silent=True) or {}
    try:
        event = _coordinator().change_case_lifecycle(case_id, payload.get("state", "closed"), payload.get("reason", ""), tenant_id=str(context.tenant_id), actor_id=str(actor_id))
    except LookupError:
        return jsonify({"error": "investigation_not_found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    event.pop("tenant_id", None)
    return jsonify({"success": True, "lifecycle": event}), 201


@investigations_api.post("/<case_id>/report-approval")
def post_report_approval(case_id: str):
    context = request_context()
    actor_id = getattr(context, "actor_id", None) or session.get("actor_id") or getattr(context, "user_id", None)
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=True)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id or not actor_id:
        return jsonify({"error": "analyst_identity_required"}), 403
    payload = request.get_json(silent=True) or {}
    requested_state = str(payload.get("state", "analyst_reviewed"))
    if requested_state in {"approved", "rejected"} and not set(context.roles).intersection({"admin", "soc_manager"}):
        return jsonify({"error": "approval_authorization_required"}), 403
    try:
        event = _coordinator().approve_report(case_id, requested_state, payload.get("reason", ""), tenant_id=str(context.tenant_id), actor_id=str(actor_id))
    except LookupError:
        return jsonify({"error": "investigation_not_found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    event.pop("tenant_id", None)
    return jsonify({"success": True, "approval": event}), 201


def _workflow_v3():
    return _coordinator().analyst_workflow_v3


@investigations_api.get("/queue")
def get_analyst_workflow_queue():
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    try:
        page = int(request.args.get("page", 1)); page_size = int(request.args.get("page_size", 25))
        filters = {key: request.args.get(key) for key in ("status", "severity", "workflow_state", "sla_state", "escalation_state", "contradiction_state", "intelligence_freshness", "priority") if request.args.get(key)}
        filters["unassigned"] = request.args.get("unassigned")
        filters["mitre"] = request.args.get("mitre")
        return jsonify(_workflow_v3().queue(str(context.tenant_id), page=page, page_size=page_size, filters=filters))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@investigations_api.get("/<case_id>/workflow")
def get_analyst_workflow(case_id: str):
    context = request_context(); allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed: return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    try: return jsonify(_workflow_v3().workflow(case_id, str(context.tenant_id)))
    except (LookupError, PermissionError): return jsonify({"error": "investigation_not_found"}), 404


@investigations_api.get("/<case_id>/readiness")
def get_analyst_workflow_readiness(case_id: str):
    context = request_context(); allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed: return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    try: return jsonify(_workflow_v3().readiness(case_id, str(context.tenant_id)))
    except (LookupError, PermissionError): return jsonify({"error": "investigation_not_found"}), 404


@investigations_api.get("/<case_id>/evidence-priorities")
def get_evidence_priorities(case_id: str):
    context = request_context(); allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed: return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    try: return jsonify(_workflow_v3().evidence_priorities(case_id, str(context.tenant_id)))
    except (LookupError, PermissionError): return jsonify({"error": "investigation_not_found"}), 404


@investigations_api.post("/<case_id>/claim")
def claim_analyst_workflow_case(case_id: str):
    context = request_context(); actor_id = getattr(context, "actor_id", None) or session.get("actor_id")
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=True)
    if not allowed: return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    try: event = _workflow_v3().claim(case_id, str(context.tenant_id), str(actor_id), (request.get_json(silent=True) or {}).get("reason", ""))
    except (LookupError, PermissionError) as exc: return jsonify({"error": str(exc)}), 404 if isinstance(exc, LookupError) else 403
    event.pop("tenant_id", None); return jsonify({"success": True, "assignment": event}), 201


@investigations_api.post("/<case_id>/release")
def release_analyst_workflow_case(case_id: str):
    context = request_context(); actor_id = getattr(context, "actor_id", None) or session.get("actor_id")
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=True)
    if not allowed: return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    try: event = _workflow_v3().release(case_id, str(context.tenant_id), str(actor_id), (request.get_json(silent=True) or {}).get("reason", ""))
    except LookupError: return jsonify({"error": "investigation_not_found"}), 404
    event.pop("tenant_id", None); return jsonify({"success": True, "assignment": event}), 201


@investigations_api.get("/<case_id>/review-history")
def get_analyst_review_history(case_id: str):
    context = request_context(); allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed: return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    try:
        return jsonify({"version": "analyst-review-history-v1", "case_id": case_id, "evidence": _coordinator().get_evidence_reviews(case_id, str(context.tenant_id)), "audit": _coordinator().get_audit_timeline(case_id, context)})
    except LookupError: return jsonify({"error": "investigation_not_found"}), 404


@investigations_api.get("/<case_id>/approval")
def get_analyst_approval(case_id: str):
    context = request_context(); allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed: return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if _coordinator().get_report_by_case_id(case_id, str(context.tenant_id)) is None: return jsonify({"error": "investigation_not_found"}), 404
    history = [item for item in _coordinator().case_lifecycle_repository.list_for_case(case_id, tenant_id=str(context.tenant_id)) if item.get("event_kind") == "report_approval"]
    return jsonify({"version": "investigation-approval-v1", "case_id": case_id, "current": history[-1] if history else {"state": "not_required"}, "history": history})


@investigations_api.post("/<case_id>/approval/request")
def request_analyst_approval(case_id: str):
    return post_report_approval(case_id)


@investigations_api.get("/<case_id>/evidence/<evidence_id>")
def get_evidence_drilldown(case_id: str, evidence_id: str):
    """Return one evidence item and only the conclusions that cite it."""
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id:
        return jsonify({"error": "organization_context_required"}), 403
    try:
        payload = _coordinator().get_evidence_drilldown(case_id, evidence_id, context)
    except PermissionError:
        return jsonify({"error": "investigation_not_found"}), 404
    if payload is None:
        return jsonify({"error": "evidence_not_found"}), 404
    payload.pop("tenant_id", None)
    return jsonify(payload)


@investigations_api.get("/<case_id>/explainability")
def get_investigation_explainability(case_id: str):
    """Return auditable decision factors without private model reasoning."""
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id:
        return jsonify({"error": "organization_context_required"}), 403
    try:
        payload = _coordinator().get_investigation_explainability(case_id, context)
    except (PermissionError, LookupError):
        return jsonify({"error": "investigation_not_found"}), 404
    if payload is None:
        return jsonify({"error": "investigation_not_found"}), 404
    payload.pop("tenant_id", None)
    return jsonify(payload)


@investigations_api.get("/<case_id>/decision-support")
def get_investigation_decision_support(case_id: str):
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id:
        return jsonify({"error": "organization_context_required"}), 403
    try:
        payload = _coordinator().get_investigation_explainability(case_id, context)
    except (PermissionError, LookupError):
        return jsonify({"error": "investigation_not_found"}), 404
    if payload is None:
        return jsonify({"error": "investigation_not_found"}), 404
    return jsonify({"version": "investigation-decision-support-v1", "case_id": case_id, "decision_support": payload.get("decision_support", {})})


@investigations_api.get("/productivity")
def get_investigation_productivity():
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id:
        return jsonify({"error": "organization_context_required"}), 403
    try:
        payload = _coordinator().get_investigation_productivity(context)
    except PermissionError:
        return jsonify({"error": "organization_context_required"}), 403
    payload.pop("tenant_id", None)
    return jsonify(payload)


def _authorized_investigation_projection(case_id: str, operation: str):
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return None, (jsonify({"error": error}), 401 if error == "authentication_required" else 403)
    if not context.tenant_id:
        return None, (jsonify({"error": "organization_context_required"}), 403)
    try:
        value = getattr(_coordinator(), operation)(case_id, context)
    except (PermissionError, LookupError, ValueError):
        return None, (jsonify({"error": "investigation_not_found"}), 404)
    if value is None:
        return None, (jsonify({"error": "investigation_not_found"}), 404)
    return value, None


@investigations_api.get("/<case_id>/evidence-graph")
def get_evidence_graph(case_id: str):
    payload, error = _authorized_investigation_projection(case_id, "get_evidence_graph")
    return error if error else jsonify(payload)


@investigations_api.get("/<case_id>/evidence-graph-workspace")
def get_evidence_graph_workspace(case_id: str):
    payload, error = _authorized_investigation_projection(case_id, "get_evidence_graph_workspace")
    return error if error else jsonify(payload)


@investigations_api.get("/<case_id>/evidence-compare")
def compare_evidence(case_id: str):
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id:
        return jsonify({"error": "organization_context_required"}), 403
    evidence_a, evidence_b = request.args.get("evidence_a"), request.args.get("evidence_b")
    if not evidence_a or not evidence_b or evidence_a == evidence_b:
        return jsonify({"error": "two_distinct_evidence_ids_required"}), 400
    try:
        return jsonify(_coordinator().compare_evidence(case_id, evidence_a, evidence_b, context))
    except (PermissionError, LookupError, ValueError):
        return jsonify({"error": "evidence_not_found"}), 404


@investigations_api.get("/<case_id>/contradictions")
def get_contradictions(case_id: str):
    payload, error = _authorized_investigation_projection(case_id, "get_contradictions")
    return error if error else jsonify(payload)


@investigations_api.get("/<case_id>/report-export")
def get_report_export(case_id: str):
    payload, error = _authorized_investigation_projection(case_id, "get_report_export")
    return error if error else jsonify(payload)


@investigations_api.get("/<case_id>/report-export-v2")
def get_report_export_v2(case_id: str):
    payload, error = _authorized_investigation_projection(case_id, "get_report_v2")
    return error if error else jsonify(payload)


@investigations_api.get("/<case_id>/report-export-v2/pdf")
def get_report_export_v2_pdf(case_id: str):
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id:
        return jsonify({"error": "organization_context_required"}), 403
    try:
        payload = _coordinator().get_report_v2_pdf(case_id, context)
    except (PermissionError, LookupError, ValueError):
        return jsonify({"error": "investigation_not_found"}), 404
    return Response(payload, mimetype="application/pdf", headers={"Content-Disposition": f"attachment; filename=sentinel-dna-{case_id}-report-v2.pdf"})


@investigations_api.post("/<case_id>/contradictions/<contradiction_id>/review")
def review_contradiction(case_id: str, contradiction_id: str):
    context = request_context()
    actor_id = getattr(context, "actor_id", None) or session.get("actor_id") or getattr(context, "user_id", None)
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=True)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id or not actor_id:
        return jsonify({"error": "analyst_identity_required"}), 403
    payload = request.get_json(silent=True) or {}
    try:
        event = _coordinator().review_contradiction(case_id, contradiction_id, str(payload.get("state") or "reviewed"), str(payload.get("reason") or ""), tenant_id=str(context.tenant_id), actor_id=str(actor_id))
    except LookupError:
        return jsonify({"error": "contradiction_not_found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    event.pop("tenant_id", None)
    return jsonify({"success": True, "review": event}), 201


@investigations_api.get("/<case_id>/providers")
def get_provider_observations(case_id: str):
    """Return provider-neutral, redacted observations for an authorized case."""
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
    if not view:
        return jsonify({"error": "investigation_not_found"}), 404
    return jsonify({"version": "provider-observations-v1", "case_id": case_id, "providers": view.get("provider_observations", [])})


@investigations_api.get("/executions/compare")
def compare_investigations():
    """Compare two tenant-owned execution snapshots without raw evidence leakage."""
    context = request_context()
    allowed, error = authorize_investigation({"metadata": {"tenant_id": context.tenant_id}}, write=False)
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id:
        return jsonify({"error": "organization_context_required"}), 403
    execution_a = request.args.get("execution_a")
    execution_b = request.args.get("execution_b")
    if not execution_a or not execution_b:
        return jsonify({"error": "execution_ids_required"}), 400
    try:
        payload = _coordinator().compare_execution_projections(execution_a, execution_b, context)
    except PermissionError:
        return jsonify({"error": "organization_context_required"}), 403
    if payload is None:
        return jsonify({"error": "execution_not_found"}), 404
    return jsonify(payload)


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

from flask import Blueprint, current_app, jsonify, render_template, request, session
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
from .models import StreamEvent
from .queue import EventQueue
from .processor import EventProcessor
streaming_api = Blueprint("streaming_api", __name__)
_queue = EventQueue(); _processor = EventProcessor(_queue)
def _csrf(): return session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token")
@streaming_api.post("/api/streaming/events")
@permission_required("streaming:publish")
@tenant_required
def publish():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    event = StreamEvent(current_organization().organization_id, (request.get_json(silent=True) or {}).get("payload", {})); _queue.publish(event)
    current_app.container.get("audit_service").record("STREAM_EVENT_PUBLISHED", user_id=session.get("user_id"), details={"event_id": event.id}); return jsonify(event.public()), 202
@streaming_api.get("/api/streaming/metrics")
@permission_required("streaming:read")
@tenant_required
def metrics():
    _processor.metrics.queue_depth = _queue.depth(); return jsonify(_processor.metrics.public())
@streaming_api.get("/workspace/live")
@permission_required("streaming:read")
@tenant_required
def live_workspace():
    return render_template("live.html", metrics=_processor.metrics.public(), events=_processor.events[-50:], alerts=_processor.alerts[-50:], investigations=_processor.investigations[-50:], actions=_processor.automation_actions[-50:])

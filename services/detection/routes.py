from flask import Blueprint, current_app, g, jsonify, request, session
from services.auth.permissions import permission_required
from services.core.security_context import request_context
from services.telemetry import EventNormalizer, WindowsEventAdapter, LinuxEventAdapter, SyslogAdapter
from .engine import DetectionEngine
detection_api = Blueprint("detection_api", __name__, url_prefix="/api/detection")
_events = []; _alerts = []
def _forward(alert):
    _alerts.append(alert)
    intake = current_app.container.get("investigation_intake")
    if intake is None:
        raise RuntimeError("durable investigation intake is unavailable")
    durable_alert = dict(alert)
    event = alert.get("event") if isinstance(alert.get("event"), dict) else {}
    raw_event = event.get("raw_data") if isinstance(event.get("raw_data"), dict) else {}
    durable_alert.setdefault("case_id", raw_event.get("case_id") or alert.get("id"))
    result = intake.accept(durable_alert, context=request_context(), source="detection")
    g.setdefault("detection_intake_results", []).append(result)
    return result
def _csrf(): return session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token")
def _engine(): return DetectionEngine(alert_sink=_forward)
@detection_api.post("/events")
@permission_required("detection:ingest")
def ingest():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}; source = data.get("source", "generic"); adapter = {"windows": WindowsEventAdapter(), "linux": LinuxEventAdapter(), "syslog": SyslogAdapter()}.get(source, EventNormalizer())
    event = adapter.normalize(data.get("event", data)); _events.append(event.public()); alerts = _engine().process(event)
    current_app.container.get("audit_service").record("TELEMETRY_PROCESSED", user_id=session.get("user_id"), details={"event_id": event.id, "alerts": len(alerts)})
    intake_results = g.get("detection_intake_results", [])
    rejected = next((item for item in intake_results if not item.accepted), None)
    response = {"event": event.public(), "alerts": [a.public() for a in alerts], "investigation_intake": [item.to_dict() for item in intake_results]}
    if rejected is not None:
        return jsonify(response), rejected.http_status
    return jsonify(response), 202
@detection_api.get("/alerts")
@permission_required("detection:read")
def alerts(): return jsonify({"alerts": _alerts})

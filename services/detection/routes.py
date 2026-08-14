from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from services.telemetry import EventNormalizer, WindowsEventAdapter, LinuxEventAdapter, SyslogAdapter
from .engine import DetectionEngine
detection_api = Blueprint("detection_api", __name__, url_prefix="/api/detection")
_events = []; _alerts = []
def _forward(alert):
    _alerts.append(alert)
    try: current_app.container.get("investigation_coordinator").investigate(case_id=alert["id"], alert=alert, artifacts=[{"type": "telemetry", "value": alert["event"]}])
    except Exception: pass
def _csrf(): return session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token")
def _engine(): return DetectionEngine(alert_sink=_forward)
@detection_api.post("/events")
@permission_required("detection:ingest")
def ingest():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}; source = data.get("source", "generic"); adapter = {"windows": WindowsEventAdapter(), "linux": LinuxEventAdapter(), "syslog": SyslogAdapter()}.get(source, EventNormalizer())
    event = adapter.normalize(data.get("event", data)); _events.append(event.public()); alerts = _engine().process(event)
    current_app.container.get("audit_service").record("TELEMETRY_PROCESSED", user_id=session.get("user_id"), details={"event_id": event.id, "alerts": len(alerts)})
    return jsonify({"event": event.public(), "alerts": [a.public() for a in alerts]}), 202
@detection_api.get("/alerts")
@permission_required("detection:read")
def alerts(): return jsonify({"alerts": _alerts})

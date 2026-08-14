from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from services.telemetry import EventNormalizer
from services.detection import DetectionEngine
from .engine import AdversaryEngine
adversary_api = Blueprint("adversary_api", __name__, url_prefix="/api/adversary")
_engine = AdversaryEngine()
def _csrf(): return session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token")
def _audit(event, details): current_app.container.get("audit_service").record(event, user_id=session.get("user_id"), details=details)
@adversary_api.post("/scenarios")
@permission_required("adversary:manage")
def create():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    try: campaign = _engine.create(request.get_json(silent=True) or {})
    except (TypeError, ValueError): return jsonify({"error": "invalid_campaign"}), 400
    _audit("ADVERSARY_SCENARIO_CREATED", {"campaign_id": campaign.id}); return jsonify(campaign.public()), 201
@adversary_api.get("/campaigns")
@permission_required("adversary:read")
def campaigns(): return jsonify({"campaigns": [item.public() for item in _engine.campaigns.values()]})
@adversary_api.post("/run")
@permission_required("adversary:execute")
def run():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}; campaign = _engine.campaigns.get(data.get("campaign_id"))
    if not campaign: return jsonify({"error": "campaign_not_found"}), 404
    result = _engine.run(campaign, data.get("hostname", "simulated-host")); detection = DetectionEngine(); normalized = []
    for event in result["events"]: normalized_event = EventNormalizer().normalize(event, "adversary_simulation"); normalized.append(normalized_event.public()); detection.process(normalized_event)
    result["normalized_events"] = normalized; result["detections"] = [alert.public() for alert in detection.alerts]
    _audit("ADVERSARY_CAMPAIGN_RUN", {"campaign_id": campaign.id, "events": len(normalized), "detections": len(detection.alerts)}); return jsonify(result), 202

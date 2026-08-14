from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
from services.telemetry import EventNormalizer
from services.detection import DetectionEngine
from .registry import ConnectorRegistry
connectors_api = Blueprint("connectors_api", __name__, url_prefix="/api/connectors")
_registry = ConnectorRegistry()
def _csrf(): return session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token")
def _org():
    org = current_organization(); return org.organization_id if org else None
def _audit(event, details): current_app.container.get("audit_service").record(event, user_id=session.get("user_id"), details=details)
@connectors_api.post("")
@permission_required("connectors:manage")
@tenant_required
def create():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}
    try: item = _registry.create(data.get("name", ""), data.get("connector_type", ""), _org(), data.get("config"))
    except ValueError: return jsonify({"error": "invalid_connector"}), 400
    _audit("CONNECTOR_CREATED", {"connector_id": item.id}); return jsonify(item.public()), 201
@connectors_api.get("")
@permission_required("connectors:read")
@tenant_required
def listing():
    return jsonify({"connectors": [item.public() for item in _registry.list(_org())]})
@connectors_api.post("/test")
@permission_required("connectors:test")
@tenant_required
def test():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    item = _registry.get((request.get_json(silent=True) or {}).get("connector_id", ""), _org())
    if not item: return jsonify({"error": "connector_not_found"}), 404
    health = _registry.test(item); _audit("CONNECTOR_HEALTH_CHECKED", {"connector_id": item.id}); return jsonify({"connector": item.public(), "health": health})
@connectors_api.get("/<connector_id>/health")
@permission_required("connectors:read")
@tenant_required
def health(connector_id):
    item = _registry.get(connector_id, _org())
    if not item: return jsonify({"error": "connector_not_found"}), 404
    return jsonify({"connector": item.public(), "health": item.health})
@connectors_api.post("/<connector_id>/collect")
@permission_required("connectors:collect")
@tenant_required
def collect(connector_id):
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    item = _registry.get(connector_id, _org())
    if not item: return jsonify({"error": "connector_not_found"}), 404
    events = _registry.collect(item); engine = DetectionEngine(); alerts = []
    for event in events: alerts.extend(engine.process(EventNormalizer().normalize(event, item.connector_type)))
    _audit("CONNECTOR_COLLECTION_COMPLETED", {"connector_id": item.id, "events": len(events), "alerts": len(alerts)}); return jsonify({"events": events, "alerts": [alert.public() for alert in alerts]}), 202

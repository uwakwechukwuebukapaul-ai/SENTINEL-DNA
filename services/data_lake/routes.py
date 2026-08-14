from flask import Blueprint, current_app, jsonify, render_template, request, session
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization, tenant_required
from .models import SecurityEventRecord

data_api = Blueprint("data_lake_api", __name__)
def org(): return current_organization().organization_id
def csrf(): return bool(session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token"))
def audit(event, details): current_app.container.get("audit_service").record(event, user_id=session.get("user_id"), details=details)

@data_api.post("/api/data/events")
@permission_required("analytics:search")
@tenant_required
def store_events():
    if not csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    payload = request.get_json(silent=True) or {}; rows = payload if isinstance(payload, list) else payload.get("events", [payload])
    events = [SecurityEventRecord(organization_id=org(), timestamp=x.get("timestamp", ""), source=x.get("source", "Application"), event_type=x.get("event_type", "unknown"), severity=x.get("severity", "INFO"), raw_event=x.get("raw_event", x), normalized_event=x.get("normalized_event", {}), mitre_mapping=x.get("mitre_mapping", []), asset_id=x.get("asset_id", ""), user_id=x.get("user_id", ""), ioc_matches=x.get("ioc_matches", [])) for x in rows]
    current_app.container.get("data_event_repository").bulk_store(events); audit("DATA_EVENT_STORED", {"count": len(events)}); return jsonify({"stored": len(events), "events": [e.public() for e in events]}), 201

@data_api.get("/api/data/search")
@permission_required("analytics:search")
@tenant_required
def search():
    result = current_app.container.get("security_query_engine").search(org(), request.args.to_dict()); audit("DATA_SEARCH_EXECUTED", {"count": result["count"]}); return jsonify(result)

@data_api.get("/api/analytics/threat-trends")
@permission_required("analytics:view")
@tenant_required
def trends(): return jsonify(current_app.container.get("analytics_service").threat_trends(org()))

@data_api.get("/api/analytics/techniques")
@permission_required("analytics:view")
@tenant_required
def techniques(): return jsonify(current_app.container.get("analytics_service").techniques(org()))

@data_api.get("/api/analytics/assets")
@permission_required("analytics:view")
@tenant_required
def assets(): return jsonify(current_app.container.get("analytics_service").assets(org()))

@data_api.get("/api/data/retention")
@permission_required("analytics:view")
@tenant_required
def retention(): return jsonify(current_app.container.get("retention_service").get(org()).public())

@data_api.put("/api/data/retention")
@permission_required("analytics:manage_retention")
@tenant_required
def update_retention():
    if not csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    item = current_app.container.get("retention_service").set(org(), (request.get_json(silent=True) or {}).get("retention_period", "90 days")); audit("RETENTION_POLICY_UPDATED", {"period": item.retention_period}); return jsonify(item.public())

@data_api.get("/workspace/analytics")
@permission_required("analytics:view")
@tenant_required
def analytics_workspace(): return render_template("analytics.html")

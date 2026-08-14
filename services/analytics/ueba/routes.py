from flask import Blueprint, current_app, jsonify, render_template, request, session
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization, tenant_required

ueba_api = Blueprint("ueba_api", __name__)
def org(): return current_organization().organization_id
def csrf(): return bool(session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token"))
def audit(event, details): current_app.container.get("audit_service").record(event, user_id=session.get("user_id"), details=details)

@ueba_api.get("/api/ueba/users")
@permission_required("ueba:view")
@tenant_required
def users():
    r=current_app.container.get("ueba_repository"); return jsonify({"users":[x.public() for x in r.scoped(r.profiles,org())]})
@ueba_api.get("/api/ueba/entities/<entity_id>")
@permission_required("ueba:view")
@tenant_required
def entity(entity_id):
    r=current_app.container.get("ueba_repository"); item=next((x for x in r.scoped(r.entities,org()) if x.entity_id==entity_id),None); return jsonify(item.public()) if item else (jsonify({"error":"entity_not_found"}),404)
@ueba_api.get("/api/ueba/anomalies")
@permission_required("ueba:view")
@tenant_required
def anomalies():
    r=current_app.container.get("ueba_repository"); return jsonify({"anomalies":[x.public() for x in r.scoped(r.anomalies,org())]})
@ueba_api.get("/api/ueba/risk")
@permission_required("ueba:view")
@tenant_required
def risk():
    r=current_app.container.get("ueba_repository"); return jsonify({"risk":[x.public() for x in r.scoped(r.risks,org())]})
@ueba_api.post("/api/detection/discovery/analyze")
@permission_required("detection:discover")
@tenant_required
def analyze():
    if not csrf(): return jsonify({"error":"csrf_validation_failed"}),403
    r=current_app.container.get("ueba_repository"); items=current_app.container.get("detection_discovery_engine").analyze(org(),r.scoped(r.anomalies,org())); audit("DETECTION_SUGGESTION_CREATED",{"count":len(items)}); return jsonify({"suggestions":[x.public() for x in items]})
@ueba_api.get("/api/detection/discovery/suggestions")
@permission_required("ueba:view")
@tenant_required
def suggestions(): return jsonify({"suggestions":[x.public() for x in current_app.container.get("detection_discovery_engine").scoped(org())]})
def decide(item_id,status,event):
    if not csrf(): return jsonify({"error":"csrf_validation_failed"}),403
    e=current_app.container.get("detection_discovery_engine"); item=next((x for x in e.scoped(org()) if x.id==item_id),None)
    if not item:return jsonify({"error":"suggestion_not_found"}),404
    item.status=status; audit(event,{"suggestion_id":item_id}); return jsonify(item.public())
@ueba_api.post("/api/detection/discovery/<item_id>/approve")
@permission_required("detection:approve_discovery")
@tenant_required
def approve(item_id): return decide(item_id,"APPROVED","DETECTION_SUGGESTION_APPROVED")
@ueba_api.post("/api/detection/discovery/<item_id>/reject")
@permission_required("detection:approve_discovery")
@tenant_required
def reject(item_id): return decide(item_id,"REJECTED","DETECTION_SUGGESTION_REJECTED")
@ueba_api.get("/workspace/ueba")
@permission_required("ueba:view")
@tenant_required
def workspace(): return render_template("ueba.html")

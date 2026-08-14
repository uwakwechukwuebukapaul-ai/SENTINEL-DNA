from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
threat_api = Blueprint("threat_api", __name__, url_prefix="/api/intelligence")
def org(): return current_organization().organization_id
def csrf(): return session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token")
@threat_api.post("/iocs")
@permission_required("threat:create")
@tenant_required
def create_ioc():
    if not csrf(): return jsonify({"error":"csrf_validation_failed"}),403
    item = current_app.container.get("threat_service").create_indicator(org(), request.get_json(silent=True) or {}); current_app.container.get("audit_service").record("IOC_CREATED", user_id=session.get("user_id"), details={"indicator_id": item.id}); return jsonify(item.public()),201
@threat_api.get("/iocs")
@permission_required("threat:view")
@tenant_required
def iocs(): return jsonify({"indicators":[x.public() for x in current_app.container.get("threat_service").repository.indicators_for(org())]})
@threat_api.post("/enrich")
@permission_required("threat:enrich")
@tenant_required
def enrich():
    if not csrf(): return jsonify({"error":"csrf_validation_failed"}),403
    result=current_app.container.get("threat_service").enrich(org(),(request.get_json(silent=True) or {}).get("value","")); current_app.container.get("audit_service").record("IOC_ENRICHED", user_id=session.get("user_id"), details={"value": result["ioc"]}); return jsonify(result)
@threat_api.get("/actors")
@permission_required("threat:view")
@tenant_required
def actors(): return jsonify({"actors":[x.public() for x in current_app.container.get("threat_service").actors(org())]})
@threat_api.get("/campaigns")
@permission_required("threat:view")
@tenant_required
def campaigns(): return jsonify({"campaigns":[x.public() for x in current_app.container.get("threat_service").campaigns(org())]})

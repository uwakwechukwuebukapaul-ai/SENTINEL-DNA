from flask import Blueprint, current_app, jsonify, render_template, request, session
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization, tenant_required

exposure_api = Blueprint("exposure_api", __name__, url_prefix="/api/exposure")
def org(): return current_organization().organization_id
def csrf(): return bool(session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token"))
def audit(event, details): current_app.container.get("audit_service").record(event, user_id=session.get("user_id"), details=details)

@exposure_api.post("/assets")
@permission_required("exposure:create")
@tenant_required
def create_asset():
    if not csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    item = current_app.container.get("asset_service").create(org(), request.get_json(silent=True) or {})
    audit("ASSET_REGISTERED", {"asset_id": item.id}); return jsonify(item.public()), 201

@exposure_api.get("/assets")
@permission_required("exposure:view")
@tenant_required
def assets(): return jsonify({"assets": [x.public() for x in current_app.container.get("asset_service").list(org())]})

@exposure_api.get("/assets/<item_id>")
@permission_required("exposure:view")
@tenant_required
def asset(item_id):
    item = current_app.container.get("asset_service").get(org(), item_id)
    return jsonify(item.public()) if item else (jsonify({"error": "asset_not_found"}), 404)

@exposure_api.post("/vulnerabilities")
@permission_required("exposure:create")
@tenant_required
def create_vulnerability():
    if not csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    item = current_app.container.get("vulnerability_service").create(org(), request.get_json(silent=True) or {})
    audit("VULNERABILITY_CREATED", {"vulnerability_id": item.id}); return jsonify(item.public()), 201

@exposure_api.get("/vulnerabilities")
@permission_required("exposure:view")
@tenant_required
def vulnerabilities(): return jsonify({"vulnerabilities": [x.public() for x in current_app.container.get("vulnerability_service").list(org())]})

@exposure_api.get("/vulnerabilities/<item_id>")
@permission_required("exposure:view")
@tenant_required
def vulnerability(item_id):
    item = current_app.container.get("vulnerability_service").get(org(), item_id)
    return jsonify(item.public()) if item else (jsonify({"error": "vulnerability_not_found"}), 404)

@exposure_api.get("/risk")
@permission_required("exposure:scan")
@tenant_required
def risk():
    assets = current_app.container.get("asset_service").list(org()); vulns = current_app.container.get("vulnerability_service").list(org()); results = []
    for item in vulns:
        asset = next((a for a in assets if a.id == item.asset_id), None)
        if asset: results.append(current_app.container.get("exposure_risk_engine").calculate(item, asset).public())
    audit("RISK_CALCULATED", {"count": len(results)}); return jsonify({"risks": results})

@exposure_api.get("/attack-paths")
@permission_required("exposure:view")
@tenant_required
def attack_paths():
    result = [x.public() for x in current_app.container.get("attack_path_analyzer").analyze(org(), current_app.container.get("asset_service").list(org()), current_app.container.get("vulnerability_service").list(org()))]
    audit("ATTACK_PATH_ANALYZED", {"count": len(result)}); return jsonify({"attack_paths": result})

@exposure_api.get("/workspace", endpoint="exposure_workspace_api")
def exposure_workspace_api(): return jsonify({"error": "use_workspace_route"}), 404


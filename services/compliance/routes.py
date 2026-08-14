from flask import Blueprint, current_app, jsonify, request, render_template
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
compliance_api = Blueprint("compliance_api", __name__, url_prefix="/api/compliance")
@compliance_api.get("/summary")
@permission_required("compliance:read")
@tenant_required
def summary():
    return jsonify(current_app.container.get("compliance_service").summary(current_organization().organization_id))
@compliance_api.post("/controls")
@permission_required("compliance:manage")
@tenant_required
def control(): return jsonify(current_app.container.get("governance_compliance").add_control(current_organization().organization_id,request.get_json(silent=True) or {})),201
@compliance_api.get("/posture")
@permission_required("compliance:read")
@tenant_required
def posture(): return jsonify(current_app.container.get("governance_compliance").score(current_organization().organization_id))
@compliance_api.post("/evidence")
@permission_required("compliance:manage")
@tenant_required
def evidence(): return jsonify(current_app.container.get("governance_compliance").add_evidence(current_organization().organization_id,request.get_json(silent=True) or {})),201
@compliance_api.get("/report")
@permission_required("compliance:read")
@tenant_required
def report(): return jsonify(current_app.container.get("governance_compliance").report(current_organization().organization_id))
@compliance_api.get("/workspace")
@permission_required("compliance:read")
@tenant_required
def workspace(): return render_template("compliance_governance.html")

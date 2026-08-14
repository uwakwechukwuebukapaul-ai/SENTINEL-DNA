from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
content_api = Blueprint("detection_content_api", __name__, url_prefix="/api/detection")
def _service(): return current_app.container.get("detection_content_service")
def _org(): return current_organization().organization_id
def _csrf(): return session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token")
@content_api.post("/rules")
@permission_required("detection:create")
@tenant_required
def create_rule():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    try: rule = _service().create(_org(), request.get_json(silent=True) or {}, session.get("user_id"))
    except ValueError as exc: return jsonify({"error": "invalid_detection_rule", "details": str(exc)}), 400
    current_app.container.get("audit_service").record("DETECTION_CREATED", user_id=session.get("user_id"), details={"rule_id": rule.id}); return jsonify(rule.public()), 201
@content_api.get("/rules")
@permission_required("detection:view")
@tenant_required
def list_rules():
    return jsonify({"rules": [x.public() for x in _service().repository.list_rules(_org())]})
@content_api.get("/rules/<rule_id>")
@permission_required("detection:view")
@tenant_required
def get_rule(rule_id):
    rule = _service().repository.get_rule(rule_id, _org()); return jsonify(rule.public() if rule else {"error": "rule_not_found"}), 200 if rule else 404
@content_api.put("/rules/<rule_id>")
@permission_required("detection:create")
@tenant_required
def update_rule(rule_id):
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    rule = _service().repository.get_rule(rule_id, _org())
    if not rule: return jsonify({"error": "rule_not_found"}), 404
    rule = _service().update(rule, request.get_json(silent=True) or {}, session.get("user_id")); return jsonify(rule.public())
@content_api.post("/rules/<rule_id>/test")
@permission_required("detection:test")
@tenant_required
def test_rule(rule_id):
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    rule = _service().repository.get_rule(rule_id, _org())
    if not rule: return jsonify({"error": "rule_not_found"}), 404
    return jsonify(_service().test(rule, (request.get_json(silent=True) or {}).get("events", [])))
@content_api.post("/rules/<rule_id>/deploy")
@permission_required("detection:deploy")
@tenant_required
def deploy_rule(rule_id):
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    rule = _service().repository.get_rule(rule_id, _org())
    if not rule: return jsonify({"error": "rule_not_found"}), 404
    try: rule = _service().deploy(rule)
    except ValueError as exc: return jsonify({"error": str(exc)}), 400
    current_app.container.get("audit_service").record("DETECTION_DEPLOYED", user_id=session.get("user_id"), details={"rule_id": rule.id}); return jsonify(rule.public())
@content_api.get("/packages")
@permission_required("detection:view")
@tenant_required
def packages():
    return jsonify({"packages": [x.public() for x in _service().packages(_org())]})
@content_api.get("/analytics")
@permission_required("detection:view")
@tenant_required
def analytics():
    rules = _service().repository.list_rules(_org()); return jsonify({"organization_id": _org(), "active_rules": sum(x.status == "ACTIVE" for x in rules), "draft_rules": sum(x.status == "DRAFT" for x in rules), "mitre_coverage": len({t for x in rules for t in x.mitre_techniques})})

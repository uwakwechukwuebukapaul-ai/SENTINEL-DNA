from flask import Blueprint, jsonify, request
from .service import CommandCenterPresentationService

def create_command_center_blueprint(service=None, tenant_resolver=None):
    bp=Blueprint("command_center", __name__); service=service or CommandCenterPresentationService()
    def tenant():
        value=tenant_resolver() if tenant_resolver else None
        if not value: raise PermissionError("organization_context_required")
        return value
    @bp.get("/api/command-center")
    def context():
        try:
            value=service.build_context(tenant()); return jsonify(value.to_dict() if hasattr(value,"to_dict") else value)
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    for name, getter in (("attention",service.get_attention),("investigations",service.get_investigations),("evidence",service.get_evidence),("decisions",service.get_decisions),("executive",service.get_executive),("subsystems",service.get_subsystems)):
        def route(getter=getter, key=name):
            try: return jsonify({"tenant_id":tenant(), key:getter(tenant())})
            except PermissionError as exc: return jsonify({"error":str(exc)}), 400
        bp.add_url_rule("/api/command-center/"+name, name, route)
    return bp

from flask import Blueprint, jsonify, request
from .service import CommandCenterPresentationService
from .drilldown import DrillDownService

def create_command_center_blueprint(service=None, tenant_resolver=None, source_resolver=None):
    bp=Blueprint("command_center", __name__); service=service or CommandCenterPresentationService()
    drilldown=DrillDownService(source_resolver)
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
    for name, getter in (("attention",drilldown.attention),("investigations",drilldown.investigation),("evidence",drilldown.evidence),("risk",drilldown.risk),("compliance",drilldown.compliance),("decisions",drilldown.decision),("lifecycle",drilldown.lifecycle),("history",drilldown.history)):
        def detail(reference, getter=getter):
            try:
                value=getter(tenant(), reference)
                return (jsonify(value), 200) if value else (jsonify({"error":"not_found"}), 404)
            except PermissionError as exc: return jsonify({"error":str(exc)}), 400
        bp.add_url_rule("/api/command-center/"+name+"/<reference>", name+"_detail", detail)
    return bp

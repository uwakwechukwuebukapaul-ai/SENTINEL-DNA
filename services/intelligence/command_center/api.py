from flask import Blueprint, jsonify, request
from .service import CommandCenterPresentationService
from .drilldown import DrillDownService
from .event_feed import AnalystEventFeed
from .attention_service import AnalystAttentionService

def create_command_center_blueprint(service=None, tenant_resolver=None, source_resolver=None, event_feed=None, attention_service=None):
    bp=Blueprint("command_center", __name__); service=service or CommandCenterPresentationService()
    drilldown=DrillDownService(source_resolver)
    event_feed=event_feed or AnalystEventFeed()
    attention_service=attention_service or AnalystAttentionService(event_feed)
    def tenant():
        value=tenant_resolver() if tenant_resolver else None
        if not value: raise PermissionError("organization_context_required")
        return value
    @bp.get("/api/command-center")
    def context():
        try:
            value=service.build_context(tenant()); return jsonify(value.to_dict() if hasattr(value,"to_dict") else value)
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    for name, getter in (("investigations",service.get_investigations),("evidence",service.get_evidence),("decisions",service.get_decisions),("executive",service.get_executive),("subsystems",service.get_subsystems)):
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
        bp.add_url_rule("/api/command-center/"+name+"/<reference>", "drilldown_"+name+"_detail", detail)
    @bp.get("/api/command-center/events")
    def events():
        try: return jsonify({"tenant_id":tenant(),"events":[x.to_dict() for x in event_feed.events(tenant(),**{k:request.args.get(k) for k in ("category","severity","source_domain","entity_reference","investigation_id","since","acknowledgement") if request.args.get(k)})]})
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/events/latest")
    def latest_events():
        try: return jsonify({"tenant_id":tenant(),"events":[x.to_dict() for x in event_feed.latest(tenant(),request.args.get("limit",20))]})
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/events/<event_id>")
    def event_detail(event_id):
        try:
            value=event_feed.get(tenant(),event_id); return (jsonify(value.to_dict()),200) if value else (jsonify({"error":"not_found"}),404)
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/attention")
    def attention():
        try: attention_service.derive(tenant()); return jsonify({"tenant_id":tenant(),"attention":[x.to_dict() for x in attention_service.get_attention_queue(tenant())]})
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/attention/<attention_id>")
    def attention_detail(attention_id):
        try:
            attention_service.derive(tenant()); value=attention_service.get_attention_context(tenant(),attention_id); return (jsonify(value),200) if value else (jsonify({"error":"not_found"}),404)
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    return bp

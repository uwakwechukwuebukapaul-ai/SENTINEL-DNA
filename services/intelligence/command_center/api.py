from flask import Blueprint, jsonify, request
from .service import CommandCenterPresentationService
from .drilldown import DrillDownService
from .event_feed import AnalystEventFeed
from .attention_service import AnalystAttentionService
from .decision_service import AnalystDecisionContextService
from .investigation_workspace import AnalystInvestigationWorkspaceService
from .actionability_service import AnalystActionabilityService
from .outcome_service import InvestigationOutcomeService
from .feedback_service import InvestigationFeedbackService
from .quality_trend_service import AnalystQualityTrendService
from .quality_intelligence_service import AnalystQualityIntelligenceService
from .learning_service import AnalystInvestigationLearningService
from .effectiveness_service import AnalystLearningEffectivenessService
from .learning_feedback_service import AnalystLearningFeedbackService
from .organizational_learning_service import OrganizationalLearningService
from .organizational_trend_service import OrganizationalTrendService
from .executive_learning_service import AnalystExecutiveLearningService
from .executive_learning_drilldown_service import ExecutiveLearningDrillDownService
from .maturity_service import OrganizationalMaturityService
from .maturity_reporting_service import MaturityReportingService
from .maturity_improvement_service import MaturityImprovementService
from .improvement_program_service import ImprovementProgramAnalyticsService

def create_command_center_blueprint(service=None, tenant_resolver=None, source_resolver=None, event_feed=None, attention_service=None, decision_service=None, investigation_workspace_service=None):
    bp=Blueprint("command_center", __name__); service=service or CommandCenterPresentationService()
    drilldown=DrillDownService(source_resolver)
    event_feed=event_feed or AnalystEventFeed()
    attention_service=attention_service or AnalystAttentionService(event_feed)
    decision_service=decision_service or AnalystDecisionContextService(attention_service)
    investigation_workspace_service=investigation_workspace_service or AnalystInvestigationWorkspaceService(event_feed, attention_service, decision_service, source_resolver)
    actionability_service=AnalystActionabilityService(investigation_workspace_service)
    outcome_service=InvestigationOutcomeService(investigation_workspace_service)
    feedback_service=InvestigationFeedbackService(investigation_workspace_service, outcome_service)
    quality_trend_service=AnalystQualityTrendService(feedback_service)
    quality_intelligence_service=AnalystQualityIntelligenceService(quality_trend_service)
    learning_service=AnalystInvestigationLearningService(quality_intelligence_service)
    effectiveness_service=AnalystLearningEffectivenessService(learning_service)
    learning_feedback_service=AnalystLearningFeedbackService(learning_service, effectiveness_service)
    organizational_learning_service=OrganizationalLearningService(learning_service, effectiveness_service, learning_feedback_service)
    organizational_trend_service=OrganizationalTrendService(learning_service, effectiveness_service, learning_feedback_service, organizational_learning_service)
    executive_learning_service=AnalystExecutiveLearningService(organizational_trend_service)
    executive_learning_drilldown_service=ExecutiveLearningDrillDownService(executive_learning_service, organizational_trend_service, learning_service, effectiveness_service, learning_feedback_service, organizational_learning_service)
    maturity_service=OrganizationalMaturityService(organizational_learning_service, organizational_trend_service, effectiveness_service, learning_feedback_service, executive_learning_service)
    maturity_reporting_service=MaturityReportingService(maturity_service)
    maturity_improvement_service=MaturityImprovementService(maturity_service, maturity_reporting_service)
    improvement_program_service=ImprovementProgramAnalyticsService(maturity_service, maturity_reporting_service, maturity_improvement_service)
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
    @bp.get("/api/command-center/investigation/<investigation_id>/workspace")
    def investigation_workspace(investigation_id):
        try:
            value=investigation_workspace_service.build(tenant(), investigation_id)
            return (jsonify(value.to_dict()),200) if value else (jsonify({"error":"not_found"}),404)
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/investigation/<investigation_id>/next-steps")
    def investigation_next_steps(investigation_id):
        try:
            value=actionability_service.get_next_steps(tenant(), investigation_id)
            return (jsonify(value),200) if value else (jsonify({"error":"not_found"}),404)
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/investigation/<investigation_id>/outcome")
    def investigation_outcome(investigation_id):
        try:
            value=outcome_service.get_outcome(tenant(), investigation_id)
            return (jsonify({"investigation_id":str(investigation_id),"outcome":value.to_dict(),"provenance":value.provenance,"advisory_only":True}),200) if value else (jsonify({"error":"not_found"}),404)
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/investigation/<investigation_id>/feedback")
    def investigation_feedback(investigation_id):
        try:
            value=feedback_service.get(tenant(),investigation_id)
            return (jsonify(value),200) if value else (jsonify({"error":"not_found"}),404)
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/quality/trends")
    def quality_trends():
        try: return jsonify(quality_trend_service.trend(tenant()).to_dict())
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/quality/intelligence")
    def quality_intelligence():
        try: return jsonify(quality_intelligence_service.derive(tenant()).to_dict())
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/quality/learning")
    def quality_learning():
        try: return jsonify({"tenant_id":tenant(),"learning":[x.to_dict() for x in learning_service.derive(tenant())],"advisory_only":True})
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/quality/effectiveness")
    def quality_effectiveness():
        try: return jsonify({"tenant_id":tenant(),"effectiveness":[x.to_dict() for x in effectiveness_service.derive(tenant())],"advisory_only":True})
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/quality/learning-feedback")
    def quality_learning_feedback():
        try: return jsonify({"tenant_id":tenant(),"feedback":[x.to_dict() for x in learning_feedback_service.derive(tenant())],"advisory_only":True})
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/quality/organizational-learning")
    def quality_organizational_learning():
        try: return jsonify({"tenant_id":tenant(),"organizational_learning":[x.to_dict() for x in organizational_learning_service.derive(tenant())],"advisory_only":True})
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/quality/organizational-trends")
    def quality_organizational_trends():
        try: return jsonify({"tenant_id":tenant(),"trends":[x.to_dict() for x in organizational_trend_service.derive(tenant())],"advisory_only":True})
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/quality/executive-learning")
    def quality_executive_learning():
        try:
            tenant_id = tenant(); signals = executive_learning_service.derive(tenant_id)
            return jsonify({"tenant_id": tenant_id, "signals": [x.to_dict() for x in signals], "summary": executive_learning_service.summary(tenant_id, signals).to_dict(), "advisory_only": True})
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/quality/executive-learning/<signal_id>")
    def quality_executive_learning_detail(signal_id):
        try:
            value = executive_learning_drilldown_service.get(tenant(), signal_id)
            return (jsonify({**value.to_dict(), "advisory_only": True}), 200) if value else (jsonify({"error": "not_found"}), 404)
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/quality/maturity")
    def quality_maturity():
        try:
            tenant_id = tenant(); value = maturity_service.derive(tenant_id)
            return jsonify({"tenant_id": tenant_id, "maturity": value.to_dict(), "advisory_only": True})
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/quality/maturity/report")
    def quality_maturity_report():
        try:
            tenant_id = tenant(); value = maturity_reporting_service.derive(tenant_id)
            return jsonify({"tenant_id": tenant_id, "report": value.to_dict(), "advisory_only": True})
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/quality/maturity/improvement")
    def quality_maturity_improvement():
        try:
            tenant_id = tenant(); return jsonify(maturity_improvement_service.derive(tenant_id))
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/quality/maturity/improvement/program")
    def quality_improvement_program():
        try: return jsonify(improvement_program_service.derive(tenant()))
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.post("/api/command-center/investigation/<investigation_id>/feedback")
    def submit_investigation_feedback(investigation_id):
        try:
            if not request.is_json: return jsonify({"error":"invalid_feedback"}),400
            value=feedback_service.submit(tenant(),investigation_id,request.get_json(silent=True))
            result=feedback_service.get(tenant(),investigation_id)
            return (jsonify(result),201) if value and result else (jsonify({"error":"not_found"}),404)
        except ValueError as exc: return jsonify({"error":str(exc)}),400
        except PermissionError as exc: return jsonify({"error":str(exc)}),400
    @bp.get("/api/command-center/attention/<attention_id>")
    def attention_detail(attention_id):
        try:
            attention_service.derive(tenant()); value=attention_service.get_attention_context(tenant(),attention_id); return (jsonify(value),200) if value else (jsonify({"error":"not_found"}),404)
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    def decision_payload(value):
        return value.to_dict() if hasattr(value, "to_dict") else value
    @bp.get("/api/command-center/decision")
    def decision_contexts():
        try:
            values=decision_service.derive(tenant()); return jsonify({"tenant_id":tenant(),"decisions":[decision_payload(x) for x in values]})
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/decision/latest")
    def latest_decision():
        try:
            value=decision_service.latest(tenant()) or (decision_service.derive(tenant()) or [None])[0]
            return (jsonify(decision_payload(value)),200) if value else (jsonify({"error":"not_found"}),404)
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/decision/history")
    def decision_history():
        try: return jsonify({"tenant_id":tenant(),"history":[decision_payload(x) for x in decision_service.history(tenant())]})
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/decision/<decision_context_id>")
    def decision_detail(decision_context_id):
        try:
            value=decision_service.get(tenant(),decision_context_id)
            return (jsonify(decision_payload(value)),200) if value else (jsonify({"error":"not_found"}),404)
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/decision/attention/<attention_id>")
    def decision_attention(attention_id):
        try:
            values=decision_service.by_attention(tenant(),attention_id) or decision_service.derive(tenant(),attention_id)
            if not isinstance(values,list): values=[values] if values else []
            return jsonify({"tenant_id":tenant(),"decisions":[decision_payload(x) for x in values]})
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    @bp.get("/api/command-center/decision/investigation/<investigation_id>")
    def decision_investigation(investigation_id):
        try: return jsonify({"tenant_id":tenant(),"decisions":[decision_payload(x) for x in decision_service.by_investigation(tenant(),investigation_id)]})
        except PermissionError as exc: return jsonify({"error":str(exc)}), 400
    return bp

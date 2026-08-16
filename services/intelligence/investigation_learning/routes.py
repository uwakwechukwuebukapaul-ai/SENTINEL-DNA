from flask import Blueprint, jsonify
from .learning_service import InvestigationLearningService
from services.intelligence.investigation_knowledge import InvestigationKnowledgeService
from services.intelligence.investigation_workflow import InvestigationWorkflowService

def create_investigation_learning_blueprint(tenant_resolver=None):
    bp=Blueprint("investigation_learning",__name__)
    services={"investigation-learning":InvestigationLearningService(),"investigation-knowledge":InvestigationKnowledgeService(),"investigation-workflow":InvestigationWorkflowService()}
    def tenant():
        value=tenant_resolver() if tenant_resolver else None
        if not value: raise PermissionError("organization_context_required")
        return value
    for name, service in services.items():
        def collection(service=service):
            try:return jsonify(service.derive(tenant()))
            except PermissionError as e:return jsonify({"error":str(e)}),400
        def detail(tenant_id, service=service):
            try:
                if tenant_id != tenant(): return jsonify({"error":"tenant_isolation_violation"}),403
                return jsonify(service.derive(tenant_id))
            except PermissionError as e:return jsonify({"error":str(e)}),400
        bp.add_url_rule(f"/api/intelligence/{name}",name+"_collection",collection)
        bp.add_url_rule(f"/api/intelligence/{name}/<tenant_id>",name+"_detail",detail)
    return bp

from flask import Blueprint, jsonify

from .decision_service import InvestigationDecisionService


def create_investigation_decision_blueprint(tenant_resolver=None, service=None):
    blueprint = Blueprint("investigation_decision", __name__)
    service = service or InvestigationDecisionService()

    def tenant_id():
        value = tenant_resolver() if tenant_resolver else None
        if not value:
            raise PermissionError("organization_context_required")
        return value

    @blueprint.get("/api/investigation-decision/analysis")
    def analysis():
        try:
            return jsonify(service.derive(tenant_id()))
        except PermissionError as error:
            return jsonify({"error": str(error)}), 400

    @blueprint.get("/api/investigation-decision/analysis/<analysis_id>")
    def detail(analysis_id):
        try:
            result = service.detail(tenant_id(), analysis_id)
            return jsonify(result or {"error": "not_found"}), 200 if result else 404
        except PermissionError as error:
            return jsonify({"error": str(error)}), 400

    return blueprint

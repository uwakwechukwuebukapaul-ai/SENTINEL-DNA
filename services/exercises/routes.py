from flask import Blueprint, current_app, jsonify
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
exercise_api = Blueprint("exercise_api", __name__, url_prefix="/api/exercises")
@exercise_api.get("")
@permission_required("exercises:read")
@tenant_required
def listing(): return jsonify({"exercises": current_app.container.get("exercise_service").list(current_organization().organization_id)})

from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from .engine import HuntEngine
from .models import HuntQuery
from .repository import HuntRepository

hunting_api = Blueprint("hunting_api", __name__, url_prefix="/api/hunting")
def _repo(): return HuntRepository(str(current_app.config["HUNT_DB_PATH"]))
def _engine(): return HuntEngine(str(current_app.config["HUNT_DB_PATH"]))

@hunting_api.post("/search")
@permission_required("hunting:execute")
def search():
    data = request.get_json(silent=True) or {}
    try: result = _engine().execute(HuntQuery(data.get("query", ""), data.get("query_type", "ioc"), data.get("limit", 100)))
    except (TypeError, ValueError): return jsonify({"error": "invalid_hunt_query"}), 400
    payload = _repo().save(result); current_app.container.get("audit_service").record("HUNT_COMPLETED" if result.error is None else "HUNT_FAILED", user_id=session.get("user_id"), details={"hunt_id": result.hunt_id})
    return jsonify(payload), 200 if result.error is None else 500

@hunting_api.get("/history")
@permission_required("hunting:read")
def history(): return jsonify({"hunts": _repo().history()})

@hunting_api.get("/<hunt_id>")
@permission_required("hunting:read")
def get_hunt(hunt_id):
    result = _repo().get(hunt_id)
    return jsonify(result or {"error": "hunt_not_found"}), 200 if result else 404

from flask import Blueprint, current_app, jsonify, request
from .authentication import DevelopmentAuthenticationProvider
gateway_api = Blueprint("platform_gateway_api", __name__, url_prefix="/api/platform")
def _gateway(): return current_app.container.get("platform_gateway") if hasattr(current_app, "container") else None
@gateway_api.get("/health")
def health():
    gateway = _gateway()
    if gateway is None: return jsonify({"success": False, "error": "gateway_unavailable"}), 503
    return jsonify({"success": True, "data": [x.to_dict() for x in gateway.health.check()]}), 200

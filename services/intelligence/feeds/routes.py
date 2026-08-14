from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
feeds_api = Blueprint("threat_feeds_api", __name__, url_prefix="/api/intelligence/feeds")
@feeds_api.get("")
@permission_required("threat:view")
@tenant_required
def listing(): return jsonify({"feeds":[x.public() for x in current_app.container.get("threat_feed_service").list(current_organization().organization_id)]})
@feeds_api.post("")
@permission_required("threat:manage_feeds")
@tenant_required
def create():
    item=current_app.container.get("threat_feed_service").create(current_organization().organization_id,request.get_json(silent=True) or {}); return jsonify(item.public()),201

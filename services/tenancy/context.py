from functools import wraps
from flask import current_app, g, jsonify, request, session
def current_organization():
    org_id = session.get("organization_id") or request.headers.get("X-Organization-ID")
    service = current_app.container.get("tenancy_service")
    org = service.get(org_id) if org_id else None
    g.organization = org
    return org
def tenant_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"): return jsonify({"error": "authentication_required"}), 401
        if not current_organization(): return jsonify({"error": "organization_context_required"}), 400
        if not current_app.container.get("tenancy_service").role(g.organization.organization_id, session["user_id"]): return jsonify({"error": "tenant_access_denied"}), 403
        return view(*args, **kwargs)
    return wrapped

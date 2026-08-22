from functools import wraps
from flask import current_app, g, jsonify, request, session
def current_organization():
    session_org_id = session.get("organization_id")
    header_org_id = request.headers.get("X-Organization-ID")
    if session_org_id and header_org_id and str(session_org_id) != str(header_org_id):
        g.organization = None
        g.tenant_scope_error = "tenant_scope_violation"
        return None
    org_id = session_org_id or header_org_id
    service = current_app.container.get("tenancy_service")
    org = service.get(org_id) if org_id else None
    g.organization = org
    return org
def tenant_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"): return jsonify({"error": "authentication_required"}), 401
        if not current_organization():
            error = getattr(g, "tenant_scope_error", "organization_context_required")
            return jsonify({"error": error}), 403 if error == "tenant_scope_violation" else 400
        if not current_app.container.get("tenancy_service").role(g.organization.organization_id, session["user_id"]): return jsonify({"error": "tenant_access_denied"}), 403
        return view(*args, **kwargs)
    return wrapped

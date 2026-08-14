from flask import Blueprint,current_app,jsonify,render_template,session
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization,tenant_required
experience_api=Blueprint("platform_experience_api",__name__)
def org(): return current_organization().organization_id
def context(): return current_app.container.get("platform_experience").context(org(),session.get("role","analyst"))
@experience_api.get("/api/platform/context")
@permission_required("platform:view")
@tenant_required
def platform_context(): return jsonify(context())
@experience_api.post("/api/platform/demo-mode")
@permission_required("platform:manage")
@tenant_required
def demo(): return jsonify(current_app.container.get("platform_experience").enable_demo(org()))
@experience_api.get("/workspace/enterprise")
@permission_required("platform:view")
@tenant_required
def overview(): return render_template("enterprise_overview.html",context=context())
@experience_api.get("/workspace/onboarding")
@permission_required("platform:manage")
@tenant_required
def onboarding(): return render_template("enterprise_onboarding.html")
@experience_api.get("/workspace/settings")
@permission_required("platform:manage")
@tenant_required
def settings(): return render_template("platform_settings.html")

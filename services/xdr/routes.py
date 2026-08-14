from flask import Blueprint,current_app,jsonify,request,session,render_template
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization,tenant_required
xdr_api=Blueprint("xdr_api",__name__)
def org(): return current_organization().organization_id
def csrf(): return bool(session.get("csrf_token") and request.headers.get("X-CSRF-Token")==session.get("csrf_token"))
def audit(e,d): current_app.container.get("audit_service").record(e,user_id=session.get("user_id"),details=d)
@xdr_api.post("/api/xdr/signals")
@permission_required("xdr:manage")
@tenant_required
def signals():
 if not csrf(): return jsonify({"error":"csrf_validation_failed"}),403
 e=current_app.container.get("xdr_engine"); item=e.ingest(org(),request.get_json(silent=True) or {}); audit("XDR_SIGNAL_RECEIVED",{"signal_id":item.id}); e.fuse(org()); return jsonify(item.public()),201
@xdr_api.get("/api/xdr/incidents")
@permission_required("xdr:view")
@tenant_required
def incidents():
 r=current_app.container.get("xdr_repository"); return jsonify({"incidents":[x.public() for x in r.scoped(r.incidents,org())]})
@xdr_api.get("/api/xdr/incidents/<incident_id>")
@permission_required("xdr:view")
@tenant_required
def incident(incident_id):
 r=current_app.container.get("xdr_repository"); x=next((i for i in r.scoped(r.incidents,org()) if i.id==incident_id),None); return jsonify(x.public()) if x else (jsonify({"error":"incident_not_found"}),404)
@xdr_api.get("/api/xdr/incidents/<incident_id>/timeline")
@permission_required("xdr:view")
@tenant_required
def timeline(incident_id):
 r=current_app.container.get("xdr_repository"); x=next((i for i in r.scoped(r.incidents,org()) if i.id==incident_id),None); return jsonify({"timeline":[s.public() for s in r.scoped(r.signals,org()) if s.id in (x.signals if x else [])]})
@xdr_api.get("/workspace/xdr")
@permission_required("xdr:view")
@tenant_required
def workspace(): return render_template("xdr.html")

from flask import Blueprint, jsonify, current_app
from .schemas import SOCResponse
from services.core.security_context import authorize_investigation

soc_api=Blueprint("soc_api",__name__,url_prefix="/api/soc")
def _service(): return current_app.container.get("soc_api_service") or __import__("services.api.soc.service",fromlist=["SOCAPIService"]).SOCAPIService()
def _respond(call):
    allowed,error=authorize_investigation({},write=False)
    if not allowed:return jsonify({"success":False,"error":error}),401 if error=="authentication_required" else 403
    data,warnings=call(); return jsonify(SOCResponse(True,data,warnings).to_dict()),200
@soc_api.get("/dashboard")
def dashboard(): return _respond(_service().get_dashboard)
@soc_api.get("/cases/<case_id>")
def case_view(case_id): return _respond(lambda:_service().get_case_view(case_id))
@soc_api.get("/threat-posture")
def threat_posture(): return _respond(_service().get_threat_posture)
@soc_api.get("/metrics")
def metrics(): return _respond(_service().get_metrics)

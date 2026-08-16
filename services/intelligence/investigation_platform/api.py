from flask import Blueprint,jsonify
def create_investigation_intelligence_blueprint(tenant_resolver=None,services=None):
 bp=Blueprint('investigation_intelligence',__name__);services=services or {}
 def tenant():
  value=tenant_resolver() if tenant_resolver else None
  if not value:raise PermissionError('organization_context_required')
  return value
 for path,key in (('','intelligence'),('/evidence','evidence'),('/assessment','assessment'),('/plan','plan'),('/summary','summary')):
  def route(case_id,key=key):
   try:
    t=tenant();s=services.get(key)
    if not s:return jsonify({'error':'service_unavailable'}),503
    return jsonify(s.derive(t,case_id))
   except PermissionError as e:return jsonify({'error':str(e)}),400
  bp.add_url_rule('/api/investigation-intelligence/<case_id>'+path,key,route)
 return bp

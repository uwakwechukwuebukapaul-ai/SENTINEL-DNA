from flask import Blueprint,jsonify
def create_investigation_lifecycle_blueprint(tenant_resolver=None,services=None):
 bp=Blueprint('investigation_lifecycle',__name__);services=services or {}
 def tenant():
  v=tenant_resolver() if tenant_resolver else None
  if not v:raise PermissionError('organization_context_required')
  return v
 for path,key in (('','lifecycle'),('/progress','progress'),('/quality','quality'),('/metrics','metrics')):
  def route(case_id=None,key=key):
   try:
    t=tenant();s=services.get(key)
    if not s:return jsonify({'error':'service_unavailable'}),503
    return jsonify(s.derive(t,case_id) if case_id is not None else s.derive(t))
   except PermissionError as e:return jsonify({'error':str(e)}),400
  bp.add_url_rule('/api/investigation-lifecycle/<case_id>'+path if path!='/metrics' else '/api/investigation-lifecycle/metrics',key,route)
 return bp

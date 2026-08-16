from flask import Blueprint,jsonify
def create_detection_intelligence_blueprint(tenant_resolver=None,services=None):
 bp=Blueprint('detection_intelligence',__name__);services=services or {}
 def tenant():
  t=tenant_resolver() if tenant_resolver else None
  if not t:raise PermissionError('organization_context_required')
  return t
 for path,key in (('overview','intelligence'),('coverage','coverage'),('quality','quality'),('gaps','gaps')):
  def route(key=key):
   try:
    tenant_id=tenant(); service=services.get(key)
    if service is None:return jsonify({'error':'service_unavailable'}),503
    return jsonify(service.derive(tenant_id))
   except PermissionError as e:return jsonify({'error':str(e)}),400
  bp.add_url_rule('/api/detection-intelligence/'+path,path,route)
  def detail(signal_id,key=key):
   try:
    tenant_id=tenant(); service=services.get(key)
    if service is None:return jsonify({'error':'service_unavailable'}),503
    return jsonify(service.detail(tenant_id,signal_id) or {'error':'not_found'})
   except PermissionError as e:return jsonify({'error':str(e)}),400
  bp.add_url_rule('/api/detection-intelligence/'+path+'/<signal_id>',path+'_detail',detail)
 return bp

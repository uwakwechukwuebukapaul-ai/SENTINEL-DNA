from flask import Blueprint,jsonify
def create_hunting_intelligence_blueprint(tenant_resolver=None,services=None):
 bp=Blueprint('hunting_intelligence',__name__);services=services or {}
 def tenant():
  value=tenant_resolver() if tenant_resolver else None
  if not value:raise PermissionError('organization_context_required')
  return value
 for path,key in (('overview','intelligence'),('prioritization','prioritization'),('effectiveness','effectiveness'),('gaps','gaps')):
  def route(key=key):
   try:
    t=tenant();s=services.get(key)
    if not s:return jsonify({'error':'service_unavailable'}),503
    return jsonify(s.derive(t))
   except PermissionError as e:return jsonify({'error':str(e)}),400
  bp.add_url_rule('/api/hunting-intelligence/'+path,path,route)
  def detail(signal_id,key=key):
   try:
    t=tenant();s=services.get(key)
    if not s:return jsonify({'error':'service_unavailable'}),503
    return jsonify(s.detail(t,signal_id) or {'error':'not_found'})
   except PermissionError as e:return jsonify({'error':str(e)}),400
  bp.add_url_rule('/api/hunting-intelligence/'+path+'/<signal_id>',path+'_detail',detail)
 return bp

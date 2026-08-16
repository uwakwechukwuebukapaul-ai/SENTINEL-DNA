from flask import Blueprint,jsonify
from .copilot_service import GovernedCopilotService
def create_copilot_blueprint(tenant_resolver=None,service=None):
 bp=Blueprint('governed_copilot',__name__);service=service or GovernedCopilotService()
 def tenant():
  value=tenant_resolver() if tenant_resolver else None
  if not value:raise PermissionError('organization_context_required')
  return value
 for path,method in (('context','context'),('explain','explain'),('recommend','recommend'),('reason','reason')):
  def route(case_id,method=method):
   try:return jsonify(getattr(service,method)(tenant(),case_id))
   except PermissionError as e:return jsonify({'error':str(e)}),400
  bp.add_url_rule('/api/copilot/'+path+'/<case_id>',path,route)
 return bp

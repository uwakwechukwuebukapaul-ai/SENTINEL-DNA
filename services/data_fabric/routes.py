from flask import Blueprint,jsonify,request
from .source_registry import DataSourceRegistry
from .ingestion import DataIngestionService
from .quality import DataQualityService
def create_data_fabric_blueprint(tenant_resolver=None,registry=None,ingestion=None,quality=None):
    bp=Blueprint('data_fabric_api',__name__); registry=registry or DataSourceRegistry(); ingestion=ingestion or DataIngestionService(); quality=quality or DataQualityService()
    def tenant():
        value=tenant_resolver() if tenant_resolver else None
        if not value: raise PermissionError('organization_context_required')
        return value
    @bp.get('/api/data-fabric/sources')
    def sources():
        try:return jsonify({'tenant_id':tenant(),'sources':[x.to_dict() for x in registry.list(tenant())],'advisory_only':True})
        except PermissionError as e:return jsonify({'error':str(e)}),400
    @bp.post('/api/data-fabric/sources')
    def register():
        try:
            if not request.is_json:return jsonify({'error':'json_required'}),400
            p=request.get_json() or {}; return jsonify(registry.register(tenant(),p.get('name','unknown'),p.get('source_type','unknown')).to_dict()),201
        except PermissionError as e:return jsonify({'error':str(e)}),400
    @bp.get('/api/data-fabric/quality')
    def data_quality():
        try:return jsonify({'tenant_id':tenant(),'quality':quality.report(tenant()).to_dict(),'advisory_only':True})
        except PermissionError as e:return jsonify({'error':str(e)}),400
    @bp.post('/api/data-fabric/normalize')
    def normalize():
        try:
            p=request.get_json() or {}; return jsonify(ingestion.ingest(tenant(),p.get('source_id','unknown'),p.get('event',p)).to_dict())
        except PermissionError as e:return jsonify({'error':str(e)}),400
    return bp

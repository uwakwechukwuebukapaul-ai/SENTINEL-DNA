from flask import Flask
from services.data_fabric.routes import create_data_fabric_blueprint
def test_data_fabric_routes_require_tenant():
    a=Flask('x'); a.register_blueprint(create_data_fabric_blueprint()); assert a.test_client().get('/api/data-fabric/sources').status_code==400

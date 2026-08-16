from flask import Flask
from services.intelligence.hunting_platform.api import create_hunting_intelligence_blueprint
def test_hunting_api_requires_tenant_and_registers_details():
    app=Flask('h'); app.register_blueprint(create_hunting_intelligence_blueprint()); assert app.test_client().get('/api/hunting-intelligence/overview').status_code==400; assert '/api/hunting-intelligence/gaps/<signal_id>' in str(app.url_map)

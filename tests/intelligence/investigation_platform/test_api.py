from flask import Flask
from services.intelligence.investigation_platform.api import create_investigation_intelligence_blueprint
def test_investigation_api_requires_tenant():
    app=Flask('investigation');app.register_blueprint(create_investigation_intelligence_blueprint());assert app.test_client().get('/api/investigation-intelligence/case').status_code==400

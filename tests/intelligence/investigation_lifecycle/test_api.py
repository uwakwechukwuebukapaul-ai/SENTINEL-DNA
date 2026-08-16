from flask import Flask
from services.intelligence.investigation_lifecycle.api import create_investigation_lifecycle_blueprint
def test_lifecycle_api_requires_tenant():
    app=Flask('lifecycle');app.register_blueprint(create_investigation_lifecycle_blueprint());assert app.test_client().get('/api/investigation-lifecycle/case').status_code==400

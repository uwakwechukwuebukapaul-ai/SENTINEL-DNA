from flask import Flask
from services.intelligence.copilot.api import create_copilot_blueprint
def test_copilot_api_requires_tenant():
    app=Flask('copilot');app.register_blueprint(create_copilot_blueprint());assert app.test_client().get('/api/copilot/context/case').status_code==400

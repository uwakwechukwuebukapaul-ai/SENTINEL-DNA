from flask import Flask
from services.intelligence.detection_platform.api import create_detection_intelligence_blueprint
def test_detection_api_is_tenant_protected_and_has_detail_routes():
    app=Flask('detection'); app.register_blueprint(create_detection_intelligence_blueprint()); client=app.test_client(); assert client.get('/api/detection-intelligence/overview').status_code==400
    assert '/api/detection-intelligence/overview/<signal_id>' in str(app.url_map)

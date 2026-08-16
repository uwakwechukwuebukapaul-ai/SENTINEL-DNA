from flask import Flask
from services.intelligence.investigation_decision.routes import create_investigation_decision_blueprint


def test_decision_routes_require_tenant():
    app = Flask("decision")
    app.register_blueprint(create_investigation_decision_blueprint())
    assert app.test_client().get("/api/investigation-decision/analysis").status_code == 400

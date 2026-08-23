from types import SimpleNamespace

from flask import Flask

from services.api.investigations.routes import investigations_api


class FakeCoordinator:
    def list_execution_projections(self, context, *, limit=50):
        return [{"version": "execution-projection-v1", "execution_id": "EXE-1", "tenant_id": context.tenant_id, "case_id": "CASE-1", "status": "COMPLETED"}]

    def get_execution_projection(self, execution_id, context):
        if execution_id != "EXE-1":
            return None
        return {"version": "execution-projection-v1", "execution_id": execution_id, "tenant_id": context.tenant_id, "case_id": "CASE-1", "status": "COMPLETED"}


class FakeContainer:
    def __init__(self):
        self.coordinator = FakeCoordinator()

    def get(self, name):
        if name == "investigation_coordinator":
            return self.coordinator
        if name == "canonical_authority":
            return SimpleNamespace(resolve=lambda tenant_id, actor_id: (SimpleNamespace(tenant_id=tenant_id), None, SimpleNamespace(role="analyst")))
        return None

    def require(self, name):
        if name == "canonical_authority":
            return self.get(name)
        if name == "investigation_coordinator":
            return self.coordinator
        raise LookupError(name)


def make_app():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.container = FakeContainer()
    app.register_blueprint(investigations_api)
    return app


def authenticate(client, tenant="tenant-a"):
    with client.session_transaction() as session:
        session.update(user_id="user-1", actor_id="actor-1", organization_id=tenant, canonical_principal={"actor_id": "actor-1", "tenant_id": tenant})


def test_execution_api_requires_authenticated_analyst():
    response = make_app().test_client().get("/api/investigations/executions")
    assert response.status_code == 401


def test_execution_api_returns_tenant_scoped_projection():
    client = make_app().test_client()
    authenticate(client)
    response = client.get("/api/investigations/executions/EXE-1")
    assert response.status_code == 200
    assert response.get_json()["tenant_id"] == "tenant-a"


def test_execution_api_missing_execution_is_not_found():
    client = make_app().test_client()
    authenticate(client, "tenant-b")
    response = client.get("/api/investigations/executions/EXE-MISSING")
    assert response.status_code == 404


def test_execution_api_rejects_malformed_identifier_without_querying_runtime():
    client = make_app().test_client()
    authenticate(client)
    response = client.get("/api/investigations/executions/EXE%20BAD")
    assert response.status_code == 404
    assert response.get_json() == {"error": "execution_not_found"}


def test_execution_api_rejects_unbounded_limit():
    client = make_app().test_client()
    authenticate(client)
    response = client.get("/api/investigations/executions?limit=101")
    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid_execution_query"}

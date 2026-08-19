import pytest
import shutil

@pytest.fixture(scope="session")
def isolated_database_template(tmp_path_factory):
    from database.connection import database
    from database.models import create_tables
    from services.auth.auth_service import AuthService
    from services.identity.canonical_authority import CanonicalAuthorityService
    from services.intelligence.repository.intelligence_repository import IntelligenceRepository
    from services.intelligence.repository.report_repository import InvestigationReportRepository
    template_path = tmp_path_factory.mktemp("sentinel-database-template") / "sentinel-test.db"
    previous = database.database_path
    database.database_path = str(template_path)
    try:
        create_tables(); AuthService(database); CanonicalAuthorityService(database)
        IntelligenceRepository(database); InvestigationReportRepository(database)
    finally:
        database.database_path = previous
    return template_path

@pytest.fixture(autouse=True)
def isolated_shared_database(tmp_path, monkeypatch, isolated_database_template):
    from database.connection import database
    path = tmp_path / "sentinel-test.db"
    previous = database.database_path
    shutil.copyfile(isolated_database_template, path)
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(path)); database.database_path = str(path)
    try:
        yield
    finally:
        database.database_path = previous

@pytest.fixture
def canonical_authenticated_client(isolated_shared_database):
    from app import create_app
    from services.auth.auth_service import AuthService
    from services.identity.canonical_authority import CanonicalAuthorityService
    from database.connection import database
    authority = CanonicalAuthorityService(database)
    authority.tenants.create("Acme", "tenant-a"); authority.identities.create("canonical@example.com", actor_id="actor-a"); authority.memberships.add("tenant-a", "actor-a", "analyst")
    user = AuthService(database).register("canonical-user", "canonical@example.com", "test-password-123", "analyst")
    application = create_app(); application.config["TESTING"] = True
    client = application.test_client()
    with client.session_transaction() as state:
        state["user_id"] = user.id; state["actor_id"] = "actor-a"; state["organization_id"] = "tenant-a"
    return client

@pytest.fixture
def authenticated_session():
    return {"user_id": 1, "role": "analyst"}

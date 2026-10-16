from tests.security.conftest import register_and_login_analyst
from services.core.pilot_boundary import pilot_path_allowed


def test_pilot_flag_is_wired_into_canonical_app(monkeypatch, tmp_path):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.setenv("SENTINEL_DNA_PILOT_ACCESS_REQUIRED", "1")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "pilot-boundary.sqlite"))

    from app import create_app

    app = create_app()
    assert app.config["PILOT_ACCESS_REQUIRED"] is True


def test_pilot_workspace_feedback_is_allowlisted_only_for_post():
    path = "/workspace/investigation/CASE-PILOT/feedback"
    assert pilot_path_allowed(path, "POST") is True
    assert pilot_path_allowed(path, "GET") is False


def test_analyst_cannot_reach_automation_or_non_pilot_surfaces(canonical_application):
    app = canonical_application
    client = app.test_client()
    register_and_login_analyst(client, "pilot-route-user", "pilot-route@example.test")
    app.config["PILOT_ACCESS_REQUIRED"] = True

    for path in ("/api/automation/history", "/api/soc/dashboard", "/api/incidents"):
        assert client.get(path).status_code == 403


def test_tenant_context_conflict_cannot_be_repaired_by_a_header_or_session(canonical_application):
    app = canonical_application
    client = app.test_client()
    register_and_login_analyst(client, "tenant-conflict", "tenant-conflict@example.test")

    with client.session_transaction() as state:
        principal = dict(state["canonical_principal"])
        principal["tenant_id"] = "attacker-tenant"
        state["canonical_principal"] = principal

    assert client.get("/api/investigations/CASE-1").status_code == 403


def test_canonical_analyst_role_cannot_be_upgraded_by_legacy_role_field(canonical_application):
    app = canonical_application
    client = app.test_client()
    register_and_login_analyst(client, "role-conflict", "role-conflict@example.test")
    with client.session_transaction() as state:
        user_id = state["user_id"]
    with app.container.require("auth_service").db.session() as connection:
        connection.execute("UPDATE users SET role='admin' WHERE id=?", (user_id,))
    app.config["PILOT_ACCESS_REQUIRED"] = True

    assert client.get("/api/automation/history").status_code == 403

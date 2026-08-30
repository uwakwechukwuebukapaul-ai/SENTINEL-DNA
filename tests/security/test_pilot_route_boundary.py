from tests.credential_helpers import random_password


def test_pilot_flag_is_wired_into_canonical_app(monkeypatch, tmp_path):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.setenv("SENTINEL_DNA_PILOT_ACCESS_REQUIRED", "1")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "pilot-boundary.sqlite"))

    from app import create_app

    app = create_app()
    assert app.config["PILOT_ACCESS_REQUIRED"] is True


def test_analyst_cannot_reach_automation_or_non_pilot_surfaces(monkeypatch, tmp_path):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "pilot-routes.sqlite"))

    from app import create_app

    app = create_app()
    client = app.test_client()
    password = random_password()
    assert client.post(
        "/api/auth/register",
        json={"username": "pilot-route-user", "email": "pilot-route@example.test", "password": password},
    ).status_code == 201
    assert client.post(
        "/api/auth/login",
        json={"username": "pilot-route-user", "password": password},
    ).status_code == 200
    app.config["PILOT_ACCESS_REQUIRED"] = True

    for path in ("/api/automation/history", "/api/soc/dashboard", "/api/incidents"):
        assert client.get(path).status_code == 403


def test_tenant_context_conflict_cannot_be_repaired_by_a_header_or_session(monkeypatch, tmp_path):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "tenant-conflict.sqlite"))

    from app import create_app

    app = create_app()
    client = app.test_client()
    password = random_password()
    assert client.post(
        "/api/auth/register",
        json={"username": "tenant-conflict", "email": "tenant-conflict@example.test", "password": password},
    ).status_code == 201
    assert client.post(
        "/api/auth/login",
        json={"username": "tenant-conflict", "password": password},
    ).status_code == 200

    with client.session_transaction() as state:
        principal = dict(state["canonical_principal"])
        principal["tenant_id"] = "attacker-tenant"
        state["canonical_principal"] = principal

    assert client.get("/api/investigations/CASE-1").status_code == 403


def test_canonical_analyst_role_cannot_be_upgraded_by_legacy_role_field(monkeypatch, tmp_path):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "role-conflict.sqlite"))

    from app import create_app

    app = create_app()
    client = app.test_client()
    password = random_password()
    assert client.post(
        "/api/auth/register",
        json={"username": "role-conflict", "email": "role-conflict@example.test", "password": password},
    ).status_code == 201
    assert client.post(
        "/api/auth/login",
        json={"username": "role-conflict", "password": password},
    ).status_code == 200
    with client.session_transaction() as state:
        user_id = state["user_id"]
    with app.container.require("auth_service").db.session() as connection:
        connection.execute("UPDATE users SET role='admin' WHERE id=?", (user_id,))
    app.config["PILOT_ACCESS_REQUIRED"] = True

    assert client.get("/api/automation/history").status_code == 403

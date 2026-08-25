"""
Sentinel DNA API Dependency Injection Tests.
"""

from importlib import import_module
import pytest


create_app = import_module("app").create_app


@pytest.fixture(autouse=True)
def testing_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECRET_KEY", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECURE_COOKIES", raising=False)
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "dependency-injection.sqlite"))



def test_investigation_service_from_container():

    app = create_app()


    service = app.container.get(
        "investigation_orchestrator"
    )


    assert service is not None



def test_dashboard_service_from_container():

    app = create_app()


    service = app.container.get(
        "dashboard_service"
    )


    assert service is not None

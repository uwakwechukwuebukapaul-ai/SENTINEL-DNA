"""
Sentinel DNA Flask Container Tests.
"""

import sys
from pathlib import Path
import pytest


# Ensure the project root is importable when this test is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app  # pyright: ignore[reportMissingImports]


@pytest.fixture(autouse=True)
def testing_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECRET_KEY", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECURE_COOKIES", raising=False)
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "flask-container.sqlite"))



def test_app_has_container():

    app = create_app()


    assert hasattr(
        app,
        "container",
    )



def test_container_has_core_services():

    app = create_app()


    container = app.container


    assert container.get(
        "case_manager"
    ) is not None


    assert container.get(
        "investigation_orchestrator"
    ) is not None


    assert container.get(
        "dashboard_service"
    ) is not None

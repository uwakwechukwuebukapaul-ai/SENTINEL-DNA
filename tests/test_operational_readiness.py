import json

import pytest

from sentinel_dna.case_management.case_store import CaseStore
from sentinel_dna.case_management.models import Case
from sentinel_dna.config import SentinelDNASettings
from sentinel_dna.investigation import InvestigationCoordinator
from sentinel_dna.workspace.web_app import create_app


def test_case_store_rejects_path_traversal_ids(tmp_path):
    store = CaseStore(tmp_path)
    with pytest.raises(ValueError, match="only letters"):
        store.get("../outside")
    with pytest.raises(ValueError, match="unsupported"):
        InvestigationCoordinator(tmp_path).investigate("../outside", {"subject": "Alert"})


def test_case_store_persists_valid_case_as_json(tmp_path):
    store = CaseStore(tmp_path)
    store.save(Case(case_id="customer-case_01", title="Test", description="Test"))

    loaded = store.get("customer-case_01")
    assert loaded.case_id == "customer-case_01"
    assert json.loads((tmp_path / "cases" / "customer-case_01.json").read_text())["title"] == "Test"


def test_health_and_readiness_endpoints_include_security_headers(tmp_path):
    client = create_app(str(tmp_path)).test_client()

    health = client.get("/healthz")
    ready = client.get("/readyz")

    assert health.status_code == 200
    assert health.json["status"] == "ok"
    assert ready.status_code == 200
    assert health.headers["X-Content-Type-Options"] == "nosniff"
    assert health.headers["X-Frame-Options"] == "DENY"


def test_environment_configuration_validates_port(monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_PORT", "70000")
    with pytest.raises(ValueError, match="between"):
        SentinelDNASettings.from_environment()

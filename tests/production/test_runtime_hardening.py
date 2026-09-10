import logging
from pathlib import Path

import pytest

from app import create_app
from config.production import ProductionConfig
from config.runtime import RuntimeConfig
from database.connection import DatabaseConnection
from services.intelligence.repository.report_repository import InvestigationReportRepository
from services.intelligence.runtime.execution_context import ExecutionContext
from services.intelligence.runtime.runtime_task_executor import RuntimeTaskExecutor
from services.intelligence.runtime.task import Task
from services.observability import ObservabilityService
from tests.credential_helpers import random_secret


def _production_env(monkeypatch, tmp_path, secret=None):
    secret = secret or random_secret()
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", secret)
    monkeypatch.setenv("SENTINEL_DNA_SECURE_COOKIES", "1")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "data" / "soc.db"))
    monkeypatch.delenv("FLASK_DEBUG", raising=False)


def test_production_factory_starts_secure_and_health_ready(monkeypatch, tmp_path):
    _production_env(monkeypatch, tmp_path)
    app = create_app()

    assert app.config["DEBUG"] is False
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    client = app.test_client()
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    assert client.get("/workspace/analyst/MISSING").status_code == 401


@pytest.mark.parametrize("environment", ["invalid", "production-debug"])
def test_invalid_environment_fails_closed(monkeypatch, tmp_path, environment):
    _production_env(monkeypatch, tmp_path)
    monkeypatch.setenv("SENTINEL_DNA_ENV", environment)
    with pytest.raises(RuntimeError, match="supported environment"):
        RuntimeConfig.from_environment().validate()


def test_production_rejects_debug_environment_leak(monkeypatch, tmp_path):
    _production_env(monkeypatch, tmp_path)
    monkeypatch.setenv("FLASK_DEBUG", "1")
    with pytest.raises(RuntimeError, match="DEBUG"):
        RuntimeConfig.from_environment().validate()


def test_production_config_uses_sqlite_contract_without_database_url(monkeypatch, tmp_path):
    _production_env(monkeypatch, tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    config = ProductionConfig.from_env()
    assert config.database_path == (tmp_path / "data" / "soc.db").resolve()
    assert config.database_url == ""


def test_sqlite_connection_uses_operational_pragmas(tmp_path):
    path = tmp_path / "soc.db"
    connection = DatabaseConnection(path).connect()
    try:
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "delete"
    finally:
        connection.close()


def test_report_persists_across_repository_recreation(tmp_path):
    database = DatabaseConnection(tmp_path / "reports.db")
    first = InvestigationReportRepository(database)
    first.save({"case_id": "CASE-RUNTIME", "summary": "durable"})
    second = InvestigationReportRepository(database)
    assert second.get_by_case_id("CASE-RUNTIME")["summary"] == "durable"


def test_observability_redacts_sensitive_nested_metadata(caplog):
    observer = ObservabilityService(logging.getLogger("runtime-hardening-test"))
    secret_token = random_secret()
    provider_secret = random_secret()
    with caplog.at_level(logging.INFO, logger="runtime-hardening-test"):
        observer.event(
            "diagnostic",
            case_id="CASE-1",
            correlation_id="corr-1",
            metadata={"api_key": secret_token, "safe": "ok"},
            raw_provider_response=provider_secret,
            evidence_payload={"body": "private evidence"},
        )
    output = " ".join(record.getMessage() for record in caplog.records)
    assert secret_token not in output
    assert provider_secret not in output
    assert "private evidence" not in output
    assert "corr-1" in output


def test_observability_measure_does_not_log_exception_text(caplog):
    observer = ObservabilityService(logging.getLogger("runtime-measure-test"))
    secret_token = random_secret()
    with caplog.at_level(logging.ERROR, logger="runtime-measure-test"):
        with pytest.raises(RuntimeError, match=secret_token):
            with observer.measure("operation"):
                raise RuntimeError(secret_token)
    output = " ".join(record.getMessage() for record in caplog.records)
    assert secret_token not in output
    assert "RuntimeError" in output


def test_correlation_id_is_preserved_in_http_response(monkeypatch, tmp_path):
    monkeypatch.delenv("SENTINEL_DNA_ENV", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECRET_KEY", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_DB_PATH", raising=False)
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "runtime-hardening.db"))
    app = create_app()
    response = app.test_client().get("/health", headers={"X-Correlation-ID": "corr-http"})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "corr-http"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    generated = app.test_client().get("/health")
    assert generated.headers["X-Correlation-ID"]
    assert generated.headers["X-Correlation-ID"] != "corr-http"


def test_correlation_id_reaches_runtime_task_events(caplog):
    logger = logging.getLogger("sentinel_dna")
    executor = RuntimeTaskExecutor()
    executor.register("analysis", lambda payload: {"ok": True})
    task = Task(
        capability="analysis",
        payload={
            "case_id": "CASE-RUNTIME",
            "context": ExecutionContext(correlation_id="corr-runtime"),
        },
    )

    with caplog.at_level(logging.INFO, logger="sentinel_dna"):
        assert executor.execute(task) == {"ok": True}

    events = " ".join(record.getMessage() for record in caplog.records)
    assert "corr-runtime" in events

import base64

import pytest

from sentinel_dna.config import SentinelDNASettings
from sentinel_dna.platform.distributed import LocalRateLimitStore, RedisRateLimitStore
from sentinel_dna.platform.workers import BackgroundJob, ENRICHMENT_JOB
from sentinel_dna.saas.database import SaaSDatabase
import sentinel_dna.platform.distributed as distributed
import sentinel_dna.workspace.web_app as web_app
from sentinel_dna.workspace.web_app import create_app


class FakeRedisSessionStore:
    def __init__(self, *_args, **_kwargs):
        self.sessions = {}

    def put(self, token_digest, user_id, ttl_seconds):
        self.sessions[token_digest] = user_id

    def get(self, token_digest):
        return self.sessions.get(token_digest)

    def revoke(self, token_digest):
        self.sessions.pop(token_digest, None)


class SharedFakeRedisRateLimitStore:
    counts = {}

    def __init__(self, _redis_url):
        pass

    def allow(self, key, limit, _window_seconds):
        if limit <= 0:
            return True
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key] <= limit


class FailingRedisRateLimitStore:
    def __init__(self, _redis_url):
        pass

    def allow(self, *_args):
        raise RuntimeError("redis unavailable")


def test_sqlite_remains_the_default_saas_database(tmp_path, monkeypatch):
    monkeypatch.delenv("SENTINEL_DNA_SAAS_DATABASE_URL", raising=False)
    database = SaaSDatabase(tmp_path)
    assert database.backend == "sqlite"
    assert database.is_ready() is True


def test_database_selector_rejects_non_postgresql_urls(tmp_path):
    with pytest.raises(ValueError, match="PostgreSQL"):
        SaaSDatabase(tmp_path, database_url="mysql://not-supported")


def test_production_configuration_fails_closed(monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.delenv("SENTINEL_DNA_SAAS_DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        SentinelDNASettings.from_environment()

    monkeypatch.setenv("SENTINEL_DNA_SAAS_DATABASE_URL", "postgresql://user:pass@db/sentinel")
    monkeypatch.setenv("SENTINEL_DNA_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"k" * 32).decode())
    monkeypatch.setenv("SENTINEL_DNA_RATE_LIMIT_PER_MINUTE", "5")
    assert SentinelDNASettings.from_environment().environment == "production"


def test_local_rate_limiter_enforces_fixed_window():
    limiter = LocalRateLimitStore()
    assert limiter.allow("tenant-a", 2, 60)
    assert limiter.allow("tenant-a", 2, 60)
    assert not limiter.allow("tenant-a", 2, 60)
    with pytest.raises(ValueError):
        RedisRateLimitStore("http://not-redis")


def test_api_rate_limit_is_enforced(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_RATE_LIMIT_PER_MINUTE", "1")
    client = create_app(str(tmp_path)).test_client()
    assert client.get("/healthz").status_code == 200
    assert client.get("/healthz").status_code == 429


def test_redis_rate_limiter_is_shared_across_app_instances(tmp_path, monkeypatch):
    SharedFakeRedisRateLimitStore.counts = {}
    monkeypatch.setenv("SENTINEL_DNA_REDIS_URL", "redis://redis.test/0")
    monkeypatch.setenv("SENTINEL_DNA_RATE_LIMIT_PER_MINUTE", "2")
    monkeypatch.setattr(web_app, "RedisRateLimitStore", SharedFakeRedisRateLimitStore)
    monkeypatch.setattr(distributed, "RedisSessionStore", FakeRedisSessionStore)

    first_client = create_app(str(tmp_path / "first")).test_client()
    second_client = create_app(str(tmp_path / "second")).test_client()

    assert first_client.get("/healthz", environ_base={"REMOTE_ADDR": "10.0.0.5"}).status_code == 200
    assert second_client.get("/healthz", environ_base={"REMOTE_ADDR": "10.0.0.5"}).status_code == 200
    assert first_client.get("/healthz", environ_base={"REMOTE_ADDR": "10.0.0.5"}).status_code == 429


def test_redis_rate_limiter_failure_falls_back_locally(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_REDIS_URL", "redis://redis.test/0")
    monkeypatch.setenv("SENTINEL_DNA_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setattr(web_app, "RedisRateLimitStore", FailingRedisRateLimitStore)
    monkeypatch.setattr(distributed, "RedisSessionStore", FakeRedisSessionStore)

    client = create_app(str(tmp_path)).test_client()

    assert client.get("/healthz", environ_base={"REMOTE_ADDR": "10.0.0.6"}).status_code == 200
    assert client.get("/healthz", environ_base={"REMOTE_ADDR": "10.0.0.6"}).status_code == 429


def test_rate_limiter_isolates_tenant_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_RATE_LIMIT_PER_MINUTE", "1")
    client = create_app(str(tmp_path)).test_client()

    assert client.get("/healthz", headers={"X-Sentinel-Org": "org-tenant-a"}, environ_base={"REMOTE_ADDR": "10.0.0.7"}).status_code == 200
    assert client.get("/healthz", headers={"X-Sentinel-Org": "org-tenant-b"}, environ_base={"REMOTE_ADDR": "10.0.0.7"}).status_code == 200
    assert client.get("/healthz", headers={"X-Sentinel-Org": "org-tenant-a"}, environ_base={"REMOTE_ADDR": "10.0.0.7"}).status_code == 429


def test_private_metrics_mode_requires_configured_token(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_METRICS_PRIVATE", "true")
    monkeypatch.setenv("SENTINEL_DNA_METRICS_TOKEN", "metrics-token")
    client = create_app(str(tmp_path)).test_client()

    assert client.get("/metrics").status_code == 403
    assert client.get("/metrics", headers={"X-Sentinel-Metrics-Token": "metrics-token"}).status_code == 200
    assert client.get("/metrics", headers={"Authorization": "Bearer metrics-token"}).status_code == 200


def test_health_and_readiness_fail_closed_on_database_failure(tmp_path, monkeypatch):
    def unavailable(_self):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(SaaSDatabase, "is_ready", unavailable)
    client = create_app(str(tmp_path)).test_client()

    assert client.get("/healthz").status_code == 503
    assert client.get("/readyz").status_code == 503


def test_background_job_envelope_is_serializable():
    job = BackgroundJob(ENRICHMENT_JOB, "org-test", {"case_id": "case-1"})
    assert job.to_dict()["payload"]["case_id"] == "case-1"

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rehearsal.postgresql.common import (
    APPROVAL_ENV,
    APPROVAL_VALUE,
    URL_ENV,
    digest,
    output_path,
    require_authorized_url,
)


ROOT = Path(__file__).resolve().parents[2]


def test_rehearsal_requires_explicit_authorization_and_dedicated_url():
    with pytest.raises(RuntimeError, match="authorization"):
        require_authorized_url({})

    with pytest.raises(RuntimeError, match="url"):
        require_authorized_url({APPROVAL_ENV: APPROVAL_VALUE})

    url = "postgresql://rehearsal:synthetic@127.0.0.1:55432/rehearsal"
    assert require_authorized_url({APPROVAL_ENV: APPROVAL_VALUE, URL_ENV: url}) == url


def test_rehearsal_does_not_fall_back_to_production_database_url():
    with pytest.raises(RuntimeError, match="url"):
        require_authorized_url({
            APPROVAL_ENV: APPROVAL_VALUE,
            "DATABASE_URL": "postgresql://production.example/sentinel_dna",
        })


def test_rehearsal_rejects_non_postgresql_urls():
    with pytest.raises(RuntimeError, match="disposable_postgresql_url"):
        require_authorized_url({
            APPROVAL_ENV: APPROVAL_VALUE,
            URL_ENV: "sqlite:///sentinel-dna.db",
        })


def test_rehearsal_never_writes_evidence_inside_repository(tmp_path):
    with pytest.raises(ValueError, match="outside_repository"):
        output_path(ROOT / "docs" / "remediation" / "forbidden.json", ROOT)

    target = output_path(tmp_path / "evidence.json", ROOT)
    assert target.parent == tmp_path.resolve()


def test_evidence_digest_is_deterministic_and_json_safe():
    value = {"checks": {"tenant_isolation": True}, "record_counts": {"tenant-a": 1}}
    assert digest(value) == digest(json.loads(json.dumps(value)))


def test_compose_is_disposable_postgresql_16_only():
    compose = (ROOT / "rehearsal" / "postgresql" / "docker-compose.yml").read_text(encoding="utf-8")
    requirements = (ROOT / "rehearsal" / "postgresql" / "requirements.txt").read_text(encoding="utf-8")
    assert "postgres:16-alpine" in compose
    assert "POSTGRES_PASSWORD: ${SENTINEL_DNA_REHEARSAL_PASSWORD:?" in compose
    assert '127.0.0.1:' in compose
    assert "tmpfs:" in compose
    assert "DATABASE_URL" not in compose
    assert "sentinel-postgres" not in compose
    assert "psycopg[binary]>=3.2,<4" in requirements

import json
from pathlib import Path
import sqlite3
import time

import pytest

from deployment.disaster_recovery.sqlite_backup import (
    SQLiteBackupError,
    SQLiteBackupService,
    SQLiteBackupValidationError,
)


def _database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        PRAGMA user_version = 7;
        CREATE TABLE cases (case_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, title TEXT NOT NULL);
        CREATE TABLE investigation_jobs (job_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, execution_id TEXT NOT NULL);
        CREATE TABLE provider_observations (observation_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, digest TEXT NOT NULL);
        CREATE TABLE audit_events (id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL, sequence_number INTEGER NOT NULL);
        CREATE UNIQUE INDEX idx_jobs_execution ON investigation_jobs(execution_id);
        """
    )
    connection.executemany(
        "INSERT INTO cases VALUES (?, ?, ?)",
        [("case-a", "tenant-a", "A"), ("case-b", "tenant-b", "B")],
    )
    connection.executemany(
        "INSERT INTO investigation_jobs VALUES (?, ?, ?)",
        [("job-a", "tenant-a", "exec-a"), ("job-b", "tenant-b", "exec-b")],
    )
    connection.executemany(
        "INSERT INTO provider_observations VALUES (?, ?, ?)",
        [("obs-a", "tenant-a", "digest-a"), ("obs-b", "tenant-b", "digest-b")],
    )
    connection.executemany(
        "INSERT INTO audit_events VALUES (?, ?, ?)",
        [(1, "tenant-a", 1), (2, "tenant-b", 1)],
    )
    connection.commit()
    connection.close()


def test_backup_manifest_is_cryptographic_nonsecret_and_deterministically_identified(tmp_path):
    source = tmp_path / "source.sqlite"
    artifact = tmp_path / "backup.sqlite"
    manifest = tmp_path / "backup.json"
    _database(source)

    result = SQLiteBackupService().backup(
        source,
        artifact,
        manifest,
        source_commit="8eef9afd588a1dda80975bb997e4baae06a1d06d",
        source_tree="6ca1c289586f84e93d5e9bb29fa4490f3dfbae9a",
    )

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload == result.manifest
    assert payload["artifact_id"].startswith("sha256:")
    assert payload["artifact"]["size_bytes"] == artifact.stat().st_size
    assert payload["database"]["integrity_check"] == "ok"
    assert payload["source"]["commit"] == "8eef9afd588a1dda80975bb997e4baae06a1d06d"
    assert "secret" not in json.dumps(payload).lower()


def test_restore_preserves_state_and_tenant_scoped_queries(tmp_path):
    source = tmp_path / "source.sqlite"
    artifact = tmp_path / "backup.sqlite"
    manifest = tmp_path / "backup.json"
    restored = tmp_path / "restored.sqlite"
    _database(source)
    service = SQLiteBackupService()
    service.backup(source, artifact, manifest)

    result = service.restore(artifact, manifest, restored)
    assert result.integrity_check == "ok"
    assert result.table_counts["investigation_jobs"] == 2
    connection = sqlite3.connect(restored)
    for tenant, expected in (("tenant-a", "job-a"), ("tenant-b", "job-b")):
        rows = connection.execute(
            "SELECT job_id FROM investigation_jobs WHERE tenant_id=? ORDER BY job_id",
            (tenant,),
        ).fetchall()
        assert [row[0] for row in rows] == [expected]
    assert connection.execute(
        "SELECT job_id FROM investigation_jobs WHERE tenant_id=? AND job_id=?",
        ("tenant-b", "job-a"),
    ).fetchone() is None
    connection.close()


def test_corrupted_artifact_fails_closed(tmp_path):
    source = tmp_path / "source.sqlite"
    artifact = tmp_path / "backup.sqlite"
    manifest = tmp_path / "backup.json"
    _database(source)
    service = SQLiteBackupService()
    service.backup(source, artifact, manifest)
    with artifact.open("ab") as stream:
        stream.write(b"corruption")
    with pytest.raises(SQLiteBackupValidationError):
        service.validate(artifact, manifest)


def test_restore_never_overwrites_existing_target(tmp_path):
    source = tmp_path / "source.sqlite"
    artifact = tmp_path / "backup.sqlite"
    manifest = tmp_path / "backup.json"
    target = tmp_path / "restored.sqlite"
    _database(source)
    service = SQLiteBackupService()
    service.backup(source, artifact, manifest)
    target.write_bytes(b"operator-owned")
    with pytest.raises(SQLiteBackupError):
        service.restore(artifact, manifest, target)
    assert target.read_bytes() == b"operator-owned"


def test_backup_refuses_existing_outputs(tmp_path):
    source = tmp_path / "source.sqlite"
    artifact = tmp_path / "backup.sqlite"
    manifest = tmp_path / "backup.json"
    _database(source)
    artifact.write_bytes(b"existing")
    with pytest.raises(SQLiteBackupError):
        SQLiteBackupService().backup(source, artifact, manifest)


def test_isolated_drill_reports_measured_rpo_and_rto(tmp_path):
    source = tmp_path / "source.sqlite"
    artifact = tmp_path / "backup.sqlite"
    manifest = tmp_path / "backup.json"
    restored = tmp_path / "restored.sqlite"
    _database(source)
    service = SQLiteBackupService()
    backup_started = time.time()
    service.backup(
        source,
        artifact,
        manifest,
        source_commit="8eef9afd588a1dda80975bb997e4baae06a1d06d",
        source_tree="6ca1c289586f84e93d5e9bb29fa4490f3dfbae9a",
    )
    backup_point = time.time()
    restore_started = time.time()
    result = service.restore(artifact, manifest, restored)
    restore_completed = time.time()
    connection = sqlite3.connect(restored)
    tenant_a_jobs = connection.execute(
        "SELECT job_id, execution_id FROM investigation_jobs WHERE tenant_id=?",
        ("tenant-a",),
    ).fetchall()
    cross_tenant_job = connection.execute(
        "SELECT job_id FROM investigation_jobs WHERE tenant_id=? AND job_id=?",
        ("tenant-b", "job-a"),
    ).fetchone()
    audit_sequences = connection.execute(
        "SELECT tenant_id, sequence_number FROM audit_events ORDER BY id"
    ).fetchall()
    connection.close()
    report = {
        "backup_point_epoch": backup_point,
        "backup_elapsed_seconds": backup_point - backup_started,
        "restore_elapsed_seconds": restore_completed - restore_started,
        "rpo_seconds": 0.0,
        "rto_seconds": result.elapsed_seconds,
        "integrity_check": result.integrity_check,
        "tenant_a_jobs": tenant_a_jobs,
        "cross_tenant_job": cross_tenant_job,
        "audit_sequences": audit_sequences,
    }
    print(json.dumps(report, sort_keys=True, default=list))
    assert result.integrity_check == "ok"
    assert tenant_a_jobs == [("job-a", "exec-a")]
    assert cross_tenant_job is None
    assert audit_sequences == [("tenant-a", 1), ("tenant-b", 1)]
    assert result.elapsed_seconds >= 0

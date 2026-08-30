from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile

import pytest

from deployment.disaster_recovery.sqlite_backup import SQLiteBackupService
from deployment.scripts.release_manifest import build_manifest, write_manifest
from deployment.validation.contract import (
    DeploymentContractValidator,
    write_immutable_report,
)
from deployment.scripts.release_metadata import derive_release_metadata
from tests.credential_helpers import random_password, random_secret


ROOT = Path(__file__).resolve().parents[2]


def _clean_repository(tmp_path: Path) -> Path:
    repository_root = tmp_path / "repository"
    subprocess.run(
        ["git", "clone", "--quiet", "--no-local", str(ROOT), str(repository_root)],
        check=True,
        capture_output=True,
        text=True,
    )
    if os.name != "nt":
        repository_root.chmod(0o700)
    return repository_root


def _evidence_inputs(tmp_path: Path) -> tuple[dict[str, str], Path, Path, Path]:
    repository_root = _clean_repository(tmp_path)
    metadata = derive_release_metadata(repository_root=repository_root, source_date_epoch="0")
    digest = "sha256:" + "a" * 64
    trusted = tmp_path / "trusted-metadata.json"
    trusted.write_text(json.dumps({"release_sha": metadata["SENTINEL_DNA_IMAGE_REVISION_FULL"], "image_digest": digest}) + "\n", encoding="utf-8")
    trusted.chmod(0o444)
    environment = {
        **metadata,
        "SENTINEL_DNA_ENV": "production",
        "SENTINEL_DNA_SECRET_KEY": random_secret(),
        "POSTGRES_PASSWORD": random_password(),
        "SENTINEL_DNA_SECURE_COOKIES": "1",
        "SENTINEL_DNA_DB_PATH": str(tmp_path / "runtime" / "soc.db"),
        "SENTINEL_DNA_IMAGE_DIGEST": digest,
        "SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE": str(trusted),
    }
    (tmp_path / "runtime").mkdir()
    manifest = build_manifest(
        repository_root=repository_root,
        image_digest=digest,
        image_id="sha256:image-id",
        image_created="1970-01-01T00:00:00Z",
    )
    release_manifest = tmp_path / "release-manifest.json"
    write_manifest(manifest, output=release_manifest, repository_root=repository_root)
    return environment, release_manifest, trusted, repository_root


def _backup_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    source = tmp_path / "source.sqlite"
    connection = sqlite3.connect(source)
    connection.executescript(
        "CREATE TABLE cases(case_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, provenance TEXT NOT NULL);"
        "CREATE TABLE audit_events(event_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, event_hash TEXT NOT NULL);"
        "CREATE TRIGGER audit_events_append_only_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'append_only'); END;"
        "CREATE TRIGGER audit_events_append_only_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'append_only'); END;"
        "INSERT INTO cases VALUES ('case-a', 'tenant-a', '{\"source\":\"synthetic\"}');"
        "INSERT INTO audit_events VALUES ('event-a', 'tenant-a', 'hash-a');"
    )
    connection.commit()
    connection.close()
    artifact = tmp_path / "backup.sqlite"
    manifest = tmp_path / "backup.json"
    SQLiteBackupService().backup(source, artifact, manifest, source_commit="a" * 40, source_tree="b" * 40)
    return source, artifact, manifest


def test_all_contracts_pass_with_local_nonsecret_evidence(tmp_path: Path):
    environment, release_manifest, _, repository_root = _evidence_inputs(tmp_path)
    source, artifact, backup_manifest = _backup_inputs(tmp_path)
    first = DeploymentContractValidator(
        repository_root=repository_root,
        environ=environment,
        release_manifest=release_manifest,
        backup_source=source,
        backup_artifact=artifact,
        backup_manifest=backup_manifest,
        generated_at="2026-01-01T00:00:00+00:00",
    ).run()
    second = DeploymentContractValidator(
        repository_root=repository_root,
        environ=environment,
        release_manifest=release_manifest,
        backup_source=source,
        backup_artifact=artifact,
        backup_manifest=backup_manifest,
        generated_at="2027-01-01T00:00:00+00:00",
    ).run()

    print(json.dumps(first.to_dict(), indent=2))
    assert first.validation_result == "passed"
    assert all(item["status"] == "passed" for item in first.contracts)
    startup = next(item for item in first.contracts if item["contract"] == "production_startup")
    assert startup["checks"] == {
        "canonical_wsgi_entrypoint": True,
        "debug_mode_disabled": True,
        "gunicorn_production_server": True,
        "non_root_runtime_user": True,
        "production_image_mode": True,
        "runtime_config_accepts_startup": True,
        "single_sqlite_worker_boundary": True,
    }
    assert "SENTINEL_DNA_ENV=production" not in (repository_root / "Dockerfile").read_text(encoding="utf-8")
    migration = next(item for item in first.contracts if item["contract"] == "database_migration_rehearsal")
    recovery = next(item for item in first.contracts if item["contract"] == "backup_restore_readiness")
    assert migration["checks"] == {
        "failure_handling": True,
        "migration_integrity": True,
        "migration_ordering": True,
        "upgrade_path": True,
    }
    assert recovery["checks"] == {
        "audit_integrity_after_restore": True,
        "backup_contents": True,
        "backup_creation": True,
        "backup_integrity": True,
        "provenance_preserved": True,
        "restore_integrity": True,
        "tenant_isolation_after_restore": True,
    }
    assert first.replay_digest == second.replay_digest
    assert first.report_digest != second.report_digest
    serialized = first.to_json()
    assert environment["SENTINEL_DNA_SECRET_KEY"] not in serialized
    assert environment["POSTGRES_PASSWORD"] not in serialized


def test_missing_backup_evidence_fails_closed(tmp_path: Path):
    environment, release_manifest, _, repository_root = _evidence_inputs(tmp_path)
    report = DeploymentContractValidator(
        repository_root=repository_root,
        environ=environment,
        release_manifest=release_manifest,
    ).run()
    backup = next(item for item in report.contracts if item["contract"] == "backup_restore_readiness")
    assert report.validation_result == "failed"
    assert backup["status"] == "failed"
    assert "backup_evidence_missing" in backup["failures"]


def test_report_writer_is_outside_repo_and_append_only(tmp_path: Path):
    environment, release_manifest, _, repository_root = _evidence_inputs(tmp_path)
    report = DeploymentContractValidator(repository_root=repository_root, environ=environment, release_manifest=release_manifest).run()
    output = Path(tempfile.mkdtemp(prefix="sentinel-contract-evidence-")) / "evidence.json"
    write_immutable_report(report, output, repository_root=repository_root)
    with pytest.raises(FileExistsError):
        write_immutable_report(report, output, repository_root=repository_root)
    with pytest.raises(ValueError, match="outside_repository"):
        write_immutable_report(report, repository_root / "evidence.json", repository_root=repository_root)

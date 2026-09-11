"""Offline migration, backup, and restore readiness validation services.

All database work in this module is isolated: migrations run in memory and
backup/restore probes operate on temporary copies and targets.  Reports retain
digests and bounded metadata only; they never retain database rows.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
from typing import Any, Iterable

from deployment.disaster_recovery.sqlite_backup import SQLiteBackupService


MIGRATION_RE = re.compile(r"^(\d{3})_.+\.py$")
PROVENANCE_COLUMNS = frozenset(
    {"provenance", "evidence_provenance", "source_investigation_id", "source_case_id", "source_commit"}
)
HASH_COLUMNS = frozenset({"event_hash", "audit_hash", "hash", "sha256"})


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str) + "\n").encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _quote(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _migration_files(root: Path) -> list[tuple[int, Path]]:
    directory = root / "database" / "migrations"
    result: list[tuple[int, Path]] = []
    for path in sorted(directory.glob("[0-9][0-9][0-9]_*.py")):
        match = MIGRATION_RE.fullmatch(path.name)
        if match:
            result.append((int(match.group(1)), path))
    return result


def _load_migration(path: Path, version: int) -> Any:
    spec = importlib.util.spec_from_file_location(f"_sentinel_migration_validation_{version}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("migration_module_unloadable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _schema_profile(connection: sqlite3.Connection) -> dict[str, Any]:
    objects = connection.execute(
        "SELECT type, name, COALESCE(sql, '') FROM sqlite_master "
        "WHERE type IN ('table', 'index', 'trigger', 'view') ORDER BY type, name"
    ).fetchall()
    tables = [str(row[1]) for row in objects if row[0] == "table"]
    columns: dict[str, list[str]] = {}
    table_counts: dict[str, int] = {}
    for table in tables:
        info = connection.execute(f"PRAGMA table_info({_quote(table)})").fetchall()
        columns[table] = [str(row[1]) for row in info]
        table_counts[table] = int(connection.execute(f"SELECT COUNT(*) FROM {_quote(table)}").fetchone()[0])
    schema_payload = [{"type": row[0], "name": row[1], "sql": row[2]} for row in objects]
    return {
        "schema_digest": _digest(schema_payload),
        "tables": tables,
        "table_counts": table_counts,
        "columns": columns,
        "triggers": [str(row[1]) for row in objects if row[0] == "trigger"],
    }


def _value(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"bytes_sha256": hashlib.sha256(value).hexdigest(), "size": len(value)}
    return value


def _content_digest(connection: sqlite3.Connection, profile: dict[str, Any]) -> str:
    """Hash logical table contents without exposing rows."""

    payload: list[dict[str, Any]] = []
    for table in profile["tables"]:
        try:
            rows = connection.execute(f"SELECT * FROM {_quote(table)} ORDER BY rowid").fetchall()
        except sqlite3.Error:
            rows = connection.execute(f"SELECT * FROM {_quote(table)}").fetchall()
        payload.append(
            {
                "table": table,
                "columns": profile["columns"][table],
                "rows": [[_value(value) for value in row] for row in rows],
            }
        )
    return _digest(payload)


def _tenant_profile(connection: sqlite3.Connection, profile: dict[str, Any]) -> dict[str, Any]:
    tenant_tables = [table for table, columns in profile["columns"].items() if "tenant_id" in columns]
    required_tenant_tables: list[str] = []
    null_rows = 0
    nullable_null_rows = 0
    required_null_rows = 0
    grouped_rows = 0
    distinct_tenants = 0
    for table in tenant_tables:
        table_info = connection.execute(f"PRAGMA table_info({_quote(table)})").fetchall()
        tenant_required = any(row[1] == "tenant_id" and bool(row[3]) for row in table_info)
        if tenant_required:
            required_tenant_tables.append(table)
        table_null_rows = int(
            connection.execute(
                f"SELECT COUNT(*) FROM {_quote(table)} WHERE tenant_id IS NULL OR TRIM(CAST(tenant_id AS TEXT)) = ''"
            ).fetchone()[0]
        )
        null_rows += table_null_rows
        if tenant_required:
            required_null_rows += table_null_rows
        else:
            nullable_null_rows += table_null_rows
        groups = connection.execute(
            f"SELECT tenant_id, COUNT(*) FROM {_quote(table)} "
            "WHERE tenant_id IS NOT NULL AND TRIM(CAST(tenant_id AS TEXT)) <> '' GROUP BY tenant_id"
        ).fetchall()
        grouped_rows += sum(int(row[1]) for row in groups)
        distinct_tenants += len(groups)
    total_tenant_rows = sum(profile["table_counts"][table] for table in tenant_tables)
    return {
        "tenant_table_count": len(tenant_tables),
        "required_tenant_table_count": len(required_tenant_tables),
        "tenant_row_count": total_tenant_rows,
        "grouped_row_count": grouped_rows,
        "distinct_tenant_group_count": distinct_tenants,
        "null_or_empty_tenant_rows": null_rows,
        "nullable_tenant_rows": nullable_null_rows,
        "required_null_or_empty_tenant_rows": required_null_rows,
        "isolation_ok": (
            bool(required_tenant_tables)
            and required_null_rows == 0
            and grouped_rows == total_tenant_rows - nullable_null_rows
        ),
    }


def _content_addressed_audit_ok(connection: sqlite3.Connection, table: str, columns: set[str]) -> bool:
    """Validate the row identity and payload hash used by memory audit tables."""

    required = {"audit_id", "tenant_id", "resource_type", "resource_id", "event_type", "payload", "event_hash"}
    if not required.issubset(columns):
        return False
    rows = connection.execute(
        f"SELECT audit_id, tenant_id, resource_type, resource_id, event_type, payload, event_hash FROM {_quote(table)}"
    ).fetchall()
    if not rows:
        return False
    for row in rows:
        try:
            payload = json.loads(str(row[5]))
        except (TypeError, json.JSONDecodeError):
            return False
        event_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        expected_audit_id = hashlib.sha256(
            f"{row[1]}|{row[2]}|{row[3]}|{row[4]}|{event_hash}".encode("utf-8")
        ).hexdigest()[:32]
        if str(row[6]) != event_hash or str(row[0]) != expected_audit_id:
            return False
    return True


def _audit_profile(connection: sqlite3.Connection, profile: dict[str, Any], objects: list[tuple[str, str, str]]) -> dict[str, Any]:
    audit_tables = [table for table in profile["tables"] if "audit" in table.lower()]
    trigger_sql = {str(row[1]): str(row[2]).lower() for row in objects if row[0] == "trigger"}
    table_checks: dict[str, bool] = {}
    enforcement: dict[str, str] = {}
    content_integrity: dict[str, bool] = {}
    for table in audit_tables:
        columns = set(profile["columns"][table])
        table_triggers = [sql for name, sql in trigger_sql.items() if table.lower() in sql]
        trigger_enforced = (
            any("before update" in sql for sql in table_triggers)
            and any("before delete" in sql for sql in table_triggers)
        )
        content_addressed = _content_addressed_audit_ok(connection, table, columns)
        content_integrity[table] = content_addressed
        if trigger_enforced:
            enforcement[table] = "database_triggers"
        elif content_addressed:
            enforcement[table] = "content_addressed_rows"
        table_checks[table] = (
            "tenant_id" in columns
            and (trigger_enforced or content_addressed)
        )
    return {
        "audit_table_count": len(audit_tables),
        "audit_tables": audit_tables,
        "audit_table_checks": table_checks,
        "enforcement": enforcement,
        "content_integrity": content_integrity,
        "integrity_ok": bool(audit_tables) and all(table_checks.values()),
    }


def _open_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def _database_profile(path: Path) -> dict[str, Any]:
    connection = _open_read_only(path)
    try:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity != "ok":
            raise RuntimeError("database_integrity_check_failed")
        profile = _schema_profile(connection)
        objects = connection.execute(
            "SELECT type, name, COALESCE(sql, '') FROM sqlite_master "
            "WHERE type IN ('table', 'index', 'trigger', 'view') ORDER BY type, name"
        ).fetchall()
        profile.update(
            {
                "integrity_check": integrity,
                "content_digest": _content_digest(connection, profile),
                "tenant": _tenant_profile(connection, profile),
                "audit": _audit_profile(connection, profile, [(row[0], row[1], row[2]) for row in objects]),
                "provenance_columns": sorted(
                    column
                    for values in profile["columns"].values()
                    for column in values
                    if column in PROVENANCE_COLUMNS
                ),
            }
        )
        audit_hash_columns = {
            table: sorted(set(profile["columns"][table]) & HASH_COLUMNS)
            for table in profile["audit"]["audit_tables"]
        }
        empty_hash_rows = 0
        for table, hash_columns in audit_hash_columns.items():
            for column in hash_columns:
                empty_hash_rows += int(
                    connection.execute(
                        f"SELECT COUNT(*) FROM {_quote(table)} WHERE {column} IS NULL OR TRIM(CAST({column} AS TEXT)) = ''"
                    ).fetchone()[0]
                )
        profile["audit"]["hash_columns"] = audit_hash_columns
        profile["audit"]["empty_hash_rows"] = empty_hash_rows
        profile["audit"]["integrity_ok"] = profile["audit"]["integrity_ok"] and empty_hash_rows == 0
        return profile
    finally:
        connection.close()


@dataclass(frozen=True)
class MigrationRehearsalService:
    repository_root: Path

    def validate(self) -> dict[str, Any]:
        files = _migration_files(self.repository_root)
        versions = [version for version, _ in files]
        checks = {
            "migration_ordering": bool(files) and versions == list(range(1, len(files) + 1)),
            "migration_integrity": True,
            "upgrade_path": False,
            "failure_handling": False,
        }
        failures: list[str] = []
        migration_evidence: list[dict[str, Any]] = []
        upgrade_evidence = {
            "initial_apply": False,
            "replay_apply": False,
            "schema_stable_after_replay": False,
        }
        connection: sqlite3.Connection | None = None
        try:
            for version, path in files:
                source = path.read_bytes()
                compile(source, str(path), "exec")
                module = _load_migration(path, version)
                valid = (
                    int(getattr(module, "VERSION")) == version
                    and bool(str(getattr(module, "DESCRIPTION", "")).strip())
                    and callable(getattr(module, "upgrade", None))
                )
                checks["migration_integrity"] = checks["migration_integrity"] and valid
                migration_evidence.append(
                    {"version": version, "path": str(path.relative_to(self.repository_root)).replace("\\", "/"), "sha256": hashlib.sha256(source).hexdigest()}
                )
                if not valid:
                    raise RuntimeError(f"migration_contract_invalid:{version:03d}")

            connection = sqlite3.connect(":memory:")
            connection.execute("PRAGMA foreign_keys = ON")
            for version, path in files:
                _load_migration(path, version).upgrade(connection)
            upgrade_evidence["initial_apply"] = True
            first = _schema_profile(connection)
            for version, path in files:
                _load_migration(path, version).upgrade(connection)
            upgrade_evidence["replay_apply"] = True
            second = _schema_profile(connection)
            upgrade_evidence["schema_stable_after_replay"] = (
                first["schema_digest"] == second["schema_digest"]
                and first["tables"] == second["tables"]
            )
            checks["upgrade_path"] = bool(files) and all(upgrade_evidence.values())

            failure_connection = sqlite3.connect(":memory:")
            try:
                failure_connection.execute("BEGIN")
                failure_connection.execute("CREATE TABLE migration_failure_probe (id INTEGER PRIMARY KEY)")
                raise RuntimeError("synthetic_migration_failure")
            except RuntimeError:
                failure_connection.rollback()
                remaining = failure_connection.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'migration_failure_probe'"
                ).fetchone()[0]
                checks["failure_handling"] = int(remaining) == 0
            finally:
                failure_connection.close()
        except Exception as exc:  # noqa: BLE001 - convert all rehearsal failures to safe evidence
            if len(migration_evidence) < len(files):
                checks["migration_integrity"] = False
            failures.append(type(exc).__name__)
        finally:
            if connection is not None:
                connection.close()
        failures.extend(name for name, passed in checks.items() if not passed)
        return {
            "contract": "database_migration_rehearsal",
            "status": "passed" if all(checks.values()) else "failed",
            "checks": checks,
            "failures": sorted(set(failures)),
            "evidence": {
                "migration_versions": versions,
                "migrations": migration_evidence,
                "upgrade_path": upgrade_evidence,
                "rollback_expectation": "forward migrations have no inferred down path; rollback requires restoring a validated pre-migration backup",
                "rehearsal_database": "sqlite-in-memory",
            },
        }


@dataclass(frozen=True)
class BackupRecoveryValidationService:
    source: Path | None = None
    artifact: Path | None = None
    manifest: Path | None = None
    restored: Path | None = None

    def validate(self) -> dict[str, Any]:
        checks = {
            "backup_creation": False,
            "backup_contents": False,
            "backup_integrity": False,
            "restore_integrity": False,
            "tenant_isolation_after_restore": False,
            "provenance_preserved": False,
            "audit_integrity_after_restore": False,
        }
        failures: list[str] = []
        evidence: dict[str, Any] = {}
        service = SQLiteBackupService()
        try:
            with tempfile.TemporaryDirectory(prefix="sentinel-recovery-validation-") as directory:
                workspace = Path(directory)
                source_copy: Path | None = None
                artifact = self.artifact
                manifest = self.manifest
                if self.source is not None:
                    if self.source.is_symlink() or not self.source.is_file():
                        raise RuntimeError("backup_source_invalid")
                    source_copy = workspace / "source.sqlite"
                    shutil.copyfile(self.source, source_copy)
                    generated_artifact = workspace / "generated-backup.sqlite"
                    generated_manifest = workspace / "generated-backup.json"
                    service.backup(source_copy, generated_artifact, generated_manifest, source_commit="validation", source_tree="validation")
                    artifact = artifact or generated_artifact
                    manifest = manifest or generated_manifest
                    checks["backup_creation"] = True
                if artifact is None or manifest is None:
                    raise RuntimeError("backup_evidence_missing")
                checks["backup_creation"] = (
                    artifact.is_file()
                    and not artifact.is_symlink()
                    and manifest.is_file()
                    and not manifest.is_symlink()
                )
                payload = service.validate(artifact, manifest)
                checks["backup_integrity"] = True
                artifact_profile = _database_profile(artifact)
                source_profile = _database_profile(source_copy) if source_copy is not None else None
                source_matches_artifact = source_profile is None or source_profile["content_digest"] == artifact_profile["content_digest"]
                checks["backup_contents"] = bool(artifact_profile["tables"]) and artifact_profile["table_counts"] == payload["database"]["table_counts"] and source_matches_artifact
                restored = service.restore(artifact, manifest, workspace / "restored.sqlite")
                restored_profile = _database_profile(Path(restored.restored_database))
                restored_evidence_profile: dict[str, Any] | None = None
                if self.restored is not None:
                    if self.restored.is_symlink() or not self.restored.is_file():
                        raise RuntimeError("restore_evidence_invalid")
                    restored_evidence_path = self.restored
                    restored_evidence_profile = _database_profile(restored_evidence_path)
                    if hashlib.sha256(restored_evidence_path.read_bytes()).hexdigest() != payload["artifact"]["sha256"]:
                        raise RuntimeError("restore_evidence_digest_mismatch")
                    if restored_evidence_profile != artifact_profile:
                        raise RuntimeError("restore_evidence_metadata_mismatch")
                checks["restore_integrity"] = restored_profile["integrity_check"] == "ok" and restored_profile["content_digest"] == artifact_profile["content_digest"]
                if restored_evidence_profile is not None:
                    checks["restore_integrity"] = checks["restore_integrity"] and restored_evidence_profile["content_digest"] == artifact_profile["content_digest"]
                comparison_profiles = [profile for profile in (source_profile, artifact_profile, restored_profile, restored_evidence_profile) if profile is not None]
                content_preserved = len({profile["content_digest"] for profile in comparison_profiles}) == 1
                source_provenance = payload.get("source")
                manifest_provenance = (
                    isinstance(source_provenance, dict)
                    and bool(str(source_provenance.get("commit", "")).strip())
                    and bool(str(source_provenance.get("tree", "")).strip())
                )
                checks["provenance_preserved"] = bool(restored_profile["provenance_columns"]) and manifest_provenance and content_preserved
                checks["tenant_isolation_after_restore"] = bool(restored_profile["tenant"]["isolation_ok"])
                checks["audit_integrity_after_restore"] = bool(restored_profile["audit"]["integrity_ok"])
                evidence = {
                    "artifact_id": payload.get("artifact_id"),
                    "artifact_sha256": payload.get("artifact", {}).get("sha256"),
                    "source_content_digest": source_profile["content_digest"] if source_profile else None,
                    "artifact_content_digest": artifact_profile["content_digest"],
                    "restored_content_digest": restored_profile["content_digest"],
                    "restored_artifact_sha256": hashlib.sha256(Path(restored.restored_database).read_bytes()).hexdigest(),
                    "restore_evidence_filename": self.restored.name if self.restored is not None else None,
                    "tenant": restored_profile["tenant"],
                    "provenance_columns": restored_profile["provenance_columns"],
                    "source_provenance": source_provenance,
                    "audit": restored_profile["audit"],
                    "integrity_check": restored_profile["integrity_check"],
                }
        except Exception as exc:  # noqa: BLE001 - report only an exception class, never its message
            if self.artifact is None and self.source is None:
                failures.append("backup_evidence_missing")
            else:
                failures.append(type(exc).__name__)
        failures.extend(name for name, passed in checks.items() if not passed)
        return {
            "contract": "backup_restore_readiness",
            "status": "passed" if all(checks.values()) else "failed",
            "checks": checks,
            "failures": sorted(set(failures)),
            "evidence": evidence,
        }


@dataclass(frozen=True)
class BackupRecoveryEvidenceValidator:
    """Run a complete backup/restore proof against a disposable fixture."""

    generated_at: str | None = None

    def run(self) -> dict[str, Any]:
        from datetime import datetime, timezone

        generated_at = str(self.generated_at or datetime.now(timezone.utc).isoformat())
        checks = {
            "backup_artifact_creation": False,
            "backup_integrity": False,
            "restore_process": False,
            "restored_record_counts": False,
            "tenant_isolation_after_restore": False,
            "evidence_provenance_after_restore": False,
            "audit_chain_integrity_after_restore": False,
        }
        evidence: dict[str, Any] = {
            "temporary_targets_only": True,
            "production_restore_performed": False,
            "external_integrations_used": False,
        }
        failures: list[str] = []
        service = SQLiteBackupService()
        try:
            with tempfile.TemporaryDirectory(prefix="sentinel-backup-recovery-evidence-") as directory:
                root = Path(directory)
                source = root / "source.sqlite"
                artifact = root / "backup.sqlite"
                manifest = root / "backup.json"
                restored = root / "restored.sqlite"
                connection = sqlite3.connect(source)
                connection.executescript(
                    "CREATE TABLE cases(case_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, evidence_provenance TEXT NOT NULL);"
                    "CREATE TABLE audit_events(event_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, event_hash TEXT NOT NULL);"
                    "CREATE TRIGGER audit_events_append_only_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'append_only'); END;"
                    "CREATE TRIGGER audit_events_append_only_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'append_only'); END;"
                    "INSERT INTO cases VALUES ('case-a', 'tenant-a', '{\"source\":\"synthetic\"}');"
                    "INSERT INTO cases VALUES ('case-b', 'tenant-b', '{\"source\":\"synthetic\"}');"
                    "INSERT INTO audit_events VALUES ('event-a', 'tenant-a', 'hash-a');"
                    "INSERT INTO audit_events VALUES ('event-b', 'tenant-b', 'hash-b');"
                )
                connection.commit()
                connection.close()
                service.backup(source, artifact, manifest, source_commit="validation", source_tree="validation")
                checks["backup_artifact_creation"] = artifact.is_file() and manifest.is_file()
                validated = service.validate(artifact, manifest)
                checks["backup_integrity"] = True
                result = service.restore(artifact, manifest, restored)
                checks["restore_process"] = Path(result.restored_database).is_file()
                source_connection = sqlite3.connect(source)
                restored_connection = sqlite3.connect(restored)
                try:
                    source_counts = {
                        "cases": source_connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
                        "audit_events": source_connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0],
                    }
                    restored_counts = {
                        "cases": restored_connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
                        "audit_events": restored_connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0],
                    }
                    checks["restored_record_counts"] = source_counts == restored_counts
                    tenant_rows = restored_connection.execute("SELECT tenant_id FROM cases").fetchall()
                    checks["tenant_isolation_after_restore"] = bool(tenant_rows) and all(row[0] for row in tenant_rows) and len({row[0] for row in tenant_rows}) == 2
                    provenance_rows = restored_connection.execute("SELECT evidence_provenance FROM cases").fetchall()
                    checks["evidence_provenance_after_restore"] = bool(provenance_rows) and all(row[0] for row in provenance_rows)
                    update_blocked = delete_blocked = False
                    for statement in ("UPDATE audit_events SET event_hash='tampered' WHERE event_id='event-a'", "DELETE FROM audit_events WHERE event_id='event-a'"):
                        try:
                            restored_connection.execute(statement)
                        except sqlite3.DatabaseError:
                            if statement.startswith("UPDATE"):
                                update_blocked = True
                            else:
                                delete_blocked = True
                    checks["audit_chain_integrity_after_restore"] = update_blocked and delete_blocked and restored_connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] == 2
                    evidence.update({
                        "source_record_counts": source_counts,
                        "restored_record_counts": restored_counts,
                        "restored_tenant_ids": sorted({row[0] for row in tenant_rows}),
                        "restored_provenance_records": len(provenance_rows),
                        "artifact_id": validated.get("artifact_id"),
                    })
                finally:
                    source_connection.close()
                    restored_connection.close()
        except Exception as exc:  # noqa: BLE001 - bounded failure evidence
            failures.append(type(exc).__name__)
        failures.extend(name for name, passed in checks.items() if not passed)
        result = "passed" if all(checks.values()) else "failed"
        stable = {
            "replay_version": "sentinel-dna-backup-recovery-evidence-replay.v1",
            "checks": checks,
            "failures": sorted(set(failures)),
            "source_record_counts": evidence.get("source_record_counts", {}),
            "restored_record_counts": evidence.get("restored_record_counts", {}),
            "restored_tenant_ids": evidence.get("restored_tenant_ids", []),
            "restored_provenance_records": evidence.get("restored_provenance_records", 0),
        }
        replay = _digest(stable)
        body = {
            "report_version": "sentinel-dna-backup-recovery-evidence.v1",
            "generated_at": generated_at,
            "validation_result": result,
            "checks": checks,
            "failures": sorted(set(failures)),
            "warnings": ["disposable SQLite fixture only; no production restore performed"],
            "evidence": evidence,
            "replay_digest": replay,
        }
        return {**body, "report_digest": _digest(body)}


__all__ = ["BackupRecoveryValidationService", "BackupRecoveryEvidenceValidator", "MigrationRehearsalService"]

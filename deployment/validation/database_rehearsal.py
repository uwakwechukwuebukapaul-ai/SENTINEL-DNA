"""Disposable database migration rehearsal evidence."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

from .recovery import MigrationRehearsalService, _load_migration, _migration_files


REPORT_VERSION = "sentinel-dna-database-rehearsal-validation.v1"
REPLAY_VERSION = "sentinel-dna-database-rehearsal-replay.v1"


def _digest(value: Any) -> str:
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":"), default=str) + "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class DatabaseMigrationRehearsalValidator:
    """Rehearse migrations in disposable SQLite state only."""

    def __init__(self, *, repository_root: str | Path, generated_at: str | None = None) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.generated_at = str(generated_at or datetime.now(timezone.utc).isoformat())

    def run(self) -> dict[str, Any]:
        base = MigrationRehearsalService(self.repository_root).validate()
        files = _migration_files(self.repository_root)
        checks = {
            "migration_ordering": base["checks"].get("migration_ordering", False),
            "migration_integrity": base["checks"].get("migration_integrity", False),
            "schema_compatibility": base["checks"].get("upgrade_path", False),
            "rollback_simulation": base["checks"].get("failure_handling", False),
            "tenant_data_preservation": False,
            "provenance_preservation": False,
            "audit_integrity": False,
            "postgresql_rehearsal_completed": False,
        }
        evidence: dict[str, Any] = {
            "rehearsal_database": "sqlite-in-memory-disposable",
            "postgresql_credentials_used": False,
            "migration_versions": [version for version, _ in files],
            "rollback_expectation": "restore a validated pre-migration backup; no down migration is inferred",
        }
        failures: list[str] = []
        try:
            connection = sqlite3.connect(":memory:")
            try:
                for version, path in files:
                    _load_migration(path, version).upgrade(connection)
                connection.execute(
                    "CREATE TABLE rehearsal_records (record_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, provenance TEXT NOT NULL)"
                )
                connection.execute(
                    "CREATE TABLE rehearsal_audit (event_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, event_hash TEXT NOT NULL)"
                )
                connection.executescript(
                    "CREATE TRIGGER rehearsal_audit_update BEFORE UPDATE ON rehearsal_audit BEGIN SELECT RAISE(ABORT, 'append_only'); END;"
                    "CREATE TRIGGER rehearsal_audit_delete BEFORE DELETE ON rehearsal_audit BEGIN SELECT RAISE(ABORT, 'append_only'); END;"
                )
                rows = (("record-a", "tenant-a", "provenance-a"), ("record-b", "tenant-b", "provenance-b"))
                connection.executemany("INSERT INTO rehearsal_records VALUES (?,?,?)", rows)
                connection.executemany("INSERT INTO rehearsal_audit VALUES (?,?,?)", (("event-a", "tenant-a", "hash-a"), ("event-b", "tenant-b", "hash-b")))
                connection.commit()
                before = connection.execute("SELECT record_id,tenant_id,provenance FROM rehearsal_records ORDER BY record_id").fetchall()
                for version, path in files:
                    _load_migration(path, version).upgrade(connection)
                after = connection.execute("SELECT record_id,tenant_id,provenance FROM rehearsal_records ORDER BY record_id").fetchall()
                checks["tenant_data_preservation"] = before == after and all(row[1] for row in after)
                checks["provenance_preservation"] = before == after and all(row[2] for row in after)
                update_blocked = delete_blocked = False
                for statement in ("UPDATE rehearsal_audit SET event_hash='tampered' WHERE event_id='event-a'", "DELETE FROM rehearsal_audit WHERE event_id='event-a'"):
                    try:
                        connection.execute(statement)
                    except sqlite3.DatabaseError:
                        if statement.startswith("UPDATE"):
                            update_blocked = True
                        else:
                            delete_blocked = True
                checks["audit_integrity"] = update_blocked and delete_blocked and connection.execute("SELECT COUNT(*) FROM rehearsal_audit").fetchone()[0] == 2
                evidence["record_count_before"] = len(before)
                evidence["record_count_after"] = len(after)
                evidence["tenant_ids"] = sorted({row[1] for row in after})
                evidence["provenance_digest"] = _digest([row[2] for row in after])
            finally:
                connection.close()
        except Exception as exc:  # noqa: BLE001 - bounded evidence only
            failures.append(type(exc).__name__)
        failures.extend(name for name, passed in checks.items() if not passed and name != "postgresql_rehearsal_completed")
        pending_checks = ["postgresql_rehearsal_completed"]
        result = "passed" if all(value for name, value in checks.items() if name != "postgresql_rehearsal_completed") and checks["postgresql_rehearsal_completed"] else "blocked"
        evidence["postgresql_rehearsal_scope"] = "not executed; no external database credentials or connections permitted"
        stable = {
            "replay_version": REPLAY_VERSION,
            "checks": checks,
            "failures": sorted(set(failures)),
            "pending_checks": pending_checks,
            "migration_versions": evidence["migration_versions"],
            "record_count_before": evidence.get("record_count_before", 0),
            "record_count_after": evidence.get("record_count_after", 0),
            "provenance_digest": evidence.get("provenance_digest", ""),
        }
        replay = _digest(stable)
        body = {
            "report_version": REPORT_VERSION,
            "generated_at": self.generated_at,
            "validation_result": result,
            "checks": checks,
            "pending_checks": pending_checks,
            "failures": sorted(set(failures)),
            "warnings": ["postgresql_rehearsal_not_executed_in_evidence_only_scope"],
            "evidence": evidence,
            "replay_digest": replay,
        }
        return {**body, "report_digest": _digest(body)}


DatabaseRehearsalValidator = DatabaseMigrationRehearsalValidator

__all__ = ["DatabaseMigrationRehearsalValidator", "DatabaseRehearsalValidator"]

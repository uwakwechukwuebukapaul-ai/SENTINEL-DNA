"""Safe, verifiable SQLite backup and isolated-restore utilities.

The application uses SQLite as its current authoritative persistence boundary.
This module provides operational evidence for that boundary without attempting
to become a second database or recovery engine.  It never prints database
rows, secrets, or provider payloads.  Backup artifacts and manifests must be
written to an operator-selected location outside the repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Any, Mapping


SCHEMA_VERSION = "sentinel-dna-sqlite-backup-v1"


class SQLiteBackupError(RuntimeError):
    """Base error for fail-closed backup and restore operations."""


class SQLiteBackupValidationError(SQLiteBackupError):
    """Raised when a database, artifact, or manifest fails validation."""


@dataclass(frozen=True)
class SQLiteBackupResult:
    """Safe metadata returned after a verified backup."""

    manifest: dict[str, Any]


@dataclass(frozen=True)
class SQLiteRestoreResult:
    """Safe metadata returned after a verified isolated restore."""

    manifest: dict[str, Any]
    restored_database: str
    integrity_check: str
    table_counts: dict[str, int]
    elapsed_seconds: float


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _regular_file(path: Path, label: str) -> Path:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise SQLiteBackupValidationError(f"{label} must not be a symlink")
    resolved = candidate.resolve()
    if not resolved.exists() or not resolved.is_file():
        raise SQLiteBackupValidationError(f"{label} must be an existing regular file")
    return resolved


def _new_output(path: Path, label: str) -> Path:
    candidate = path.expanduser()
    if candidate.exists() or candidate.is_symlink():
        raise SQLiteBackupError(f"refusing to overwrite existing {label}")
    resolved = candidate.resolve()
    if not resolved.parent.exists() or not resolved.parent.is_dir() or resolved.parent.is_symlink():
        raise SQLiteBackupError(f"{label} parent must be an existing non-symlink directory")
    return resolved


def _same_path(left: Path, right: Path) -> bool:
    return left.expanduser().resolve() == right.expanduser().resolve()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _database_metadata(path: Path) -> dict[str, Any]:
    """Return non-sensitive integrity and inventory metadata for *path*."""

    database = _regular_file(path, "database")
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(str(database))
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity != "ok":
            raise SQLiteBackupValidationError("SQLite integrity_check did not return ok")
        schema_rows = connection.execute(
            """
            SELECT type, name, COALESCE(sql, '') AS sql
            FROM sqlite_master
            WHERE type IN ('table', 'index', 'trigger', 'view')
            ORDER BY type, name
            """
        ).fetchall()
        schema_payload = [
            {"type": str(row["type"]), "name": str(row["name"]), "sql": str(row["sql"])}
            for row in schema_rows
        ]
        schema_digest = hashlib.sha256(
            (json.dumps(schema_payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        ).hexdigest()
        tables = [str(row["name"]) for row in schema_rows if row["type"] == "table"]
        counts: dict[str, int] = {}
        for table in tables:
            counts[table] = int(connection.execute(f"SELECT COUNT(*) FROM {_quote_identifier(table)}").fetchone()[0])
        user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        return {
            "integrity_check": integrity,
            "schema_digest": schema_digest,
            "schema_tables": tables,
            "table_counts": counts,
            "user_version": user_version,
        }
    except sqlite3.Error as exc:
        raise SQLiteBackupValidationError("SQLite validation failed") from exc
    finally:
        if connection is not None:
            connection.close()


def _read_manifest(path: Path) -> dict[str, Any]:
    manifest_path = _regular_file(path, "backup manifest")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SQLiteBackupValidationError("backup manifest is not valid JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise SQLiteBackupValidationError("unsupported SQLite backup manifest")
    return payload


def _atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise SQLiteBackupError("refusing to overwrite an existing manifest temporary file")
    try:
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        temporary.replace(path)
    except OSError as exc:
        raise SQLiteBackupError("could not write backup manifest") from exc


class SQLiteBackupService:
    """Create, validate, and restore SQLite artifacts without overwriting data."""

    def backup(
        self,
        source: Path,
        artifact: Path,
        manifest: Path,
        *,
        source_commit: str | None = None,
        source_tree: str | None = None,
    ) -> SQLiteBackupResult:
        source_path = _regular_file(source, "source database")
        artifact_path = _new_output(artifact, "backup artifact")
        manifest_path = _new_output(manifest, "backup manifest")
        if _same_path(source_path, artifact_path) or _same_path(source_path, manifest_path):
            raise SQLiteBackupError("backup outputs must differ from the source database")
        if _same_path(artifact_path, manifest_path):
            raise SQLiteBackupError("backup artifact and manifest must differ")

        source_metadata = _database_metadata(source_path)
        source_connection: sqlite3.Connection | None = None
        destination_connection: sqlite3.Connection | None = None
        try:
            source_connection = sqlite3.connect(str(source_path))
            destination_connection = sqlite3.connect(str(artifact_path))
            source_connection.backup(destination_connection)
            destination_connection.commit()
        except sqlite3.Error as exc:
            artifact_path.unlink(missing_ok=True)
            raise SQLiteBackupError("SQLite backup operation failed") from exc
        finally:
            if source_connection is not None:
                source_connection.close()
            if destination_connection is not None:
                destination_connection.close()

        artifact_metadata = _database_metadata(artifact_path)
        if artifact_metadata != source_metadata:
            artifact_path.unlink(missing_ok=True)
            raise SQLiteBackupValidationError("backup metadata differs from source metadata")
        digest = _sha256(artifact_path)
        created_at = _utc_now()
        safe_commit = str(source_commit).strip() if source_commit else None
        safe_tree = str(source_tree).strip() if source_tree else None
        payload = {
            "schema_version": SCHEMA_VERSION,
            "artifact_id": f"sha256:{digest}",
            "created_at": created_at,
            "artifact": {
                "filename": artifact_path.name,
                "size_bytes": artifact_path.stat().st_size,
                "sha256": digest,
            },
            "database": artifact_metadata,
            "source": {"commit": safe_commit, "tree": safe_tree},
        }
        _atomic_json_write(manifest_path, payload)
        return SQLiteBackupResult(payload)

    def validate(self, artifact: Path, manifest: Path) -> dict[str, Any]:
        artifact_path = _regular_file(artifact, "backup artifact")
        payload = _read_manifest(manifest)
        artifact_info = payload.get("artifact")
        if not isinstance(artifact_info, dict):
            raise SQLiteBackupValidationError("backup manifest artifact metadata is invalid")
        expected_digest = str(artifact_info.get("sha256", ""))
        expected_size = artifact_info.get("size_bytes")
        digest = _sha256(artifact_path)
        if digest != expected_digest or artifact_path.stat().st_size != expected_size:
            raise SQLiteBackupValidationError("backup artifact digest or size mismatch")
        if payload.get("artifact_id") != f"sha256:{digest}":
            raise SQLiteBackupValidationError("backup artifact identity mismatch")
        observed = _database_metadata(artifact_path)
        if observed != payload.get("database"):
            raise SQLiteBackupValidationError("backup database metadata mismatch")
        return payload

    def restore(self, artifact: Path, manifest: Path, target: Path) -> SQLiteRestoreResult:
        import time

        started = time.perf_counter()
        artifact_path = _regular_file(artifact, "backup artifact")
        target_path = _new_output(target, "restore target")
        if _same_path(artifact_path, target_path) or _same_path(target_path, Path(manifest)):
            raise SQLiteBackupError("restore target must be isolated from backup inputs")
        payload = self.validate(artifact_path, manifest)
        try:
            shutil.copyfile(artifact_path, target_path)
        except OSError as exc:
            target_path.unlink(missing_ok=True)
            raise SQLiteBackupError("could not create isolated restore target") from exc
        try:
            if _sha256(target_path) != str(payload["artifact"]["sha256"]):
                raise SQLiteBackupValidationError("restored database digest mismatch")
            metadata = _database_metadata(target_path)
            if metadata != payload["database"]:
                raise SQLiteBackupValidationError("restored database metadata mismatch")
        except Exception:
            target_path.unlink(missing_ok=True)
            raise
        return SQLiteRestoreResult(
            manifest=payload,
            restored_database=str(target_path),
            integrity_check=str(payload["database"]["integrity_check"]),
            table_counts=dict(payload["database"]["table_counts"]),
            elapsed_seconds=time.perf_counter() - started,
        )

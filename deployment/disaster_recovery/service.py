"""Deployment-facing facade for the authoritative SQLite recovery service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .sqlite_backup import SQLiteBackupService


class DisasterRecoveryService:
    """Expose verified SQLite backup and isolated restore operations.

    The facade keeps the existing service import stable while making recovery
    fail closed. It does not back up process-local caches, secrets, provider
    credentials, or external infrastructure.
    """

    def __init__(self, backup_service: SQLiteBackupService | None = None) -> None:
        self.backup_service = backup_service or SQLiteBackupService()

    def backup_database(
        self,
        source: Path,
        artifact: Path,
        manifest: Path,
        *,
        source_commit: str | None = None,
        source_tree: str | None = None,
    ) -> dict[str, Any]:
        return self.backup_service.backup(
            source,
            artifact,
            manifest,
            source_commit=source_commit,
            source_tree=source_tree,
        ).manifest

    def validate_backup(self, artifact: Path, manifest: Path) -> dict[str, Any]:
        return self.backup_service.validate(artifact, manifest)

    def restore_database(self, artifact: Path, manifest: Path, target: Path) -> dict[str, Any]:
        result = self.backup_service.restore(artifact, manifest, target)
        return {
            "manifest": result.manifest,
            "restored_database": result.restored_database,
            "integrity_check": result.integrity_check,
            "table_counts": result.table_counts,
            "elapsed_seconds": result.elapsed_seconds,
        }

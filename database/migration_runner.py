"""Portable, transactional runner for the authoritative schema chain."""

from __future__ import annotations

import hashlib
from .backend import DatabaseBackend
from .migrations.registry import (
    CONTROLLED_ANALYST_PILOT_MIGRATIONS,
    MIGRATIONS,
    NAMESPACE_MIGRATIONS,
    STAGING_MIGRATIONS,
    Migration,
    NamespaceMigration,
    _REGISTRY_TOKEN,
    validate_namespace_registry,
)


# Backward-compatible public name retained for existing callers.
CORE_MIGRATIONS = MIGRATIONS


class MigrationRunner:
    """Apply ordered migrations through the selected backend contract."""

    def __init__(
        self,
        backend: DatabaseBackend,
        migrations: tuple[Migration, ...] | None = None,
        namespace_migrations: tuple[NamespaceMigration, ...] | None = None,
    ) -> None:
        self.backend = backend
        if migrations is None:
            migrations = MIGRATIONS
        self.migrations = tuple(sorted(migrations, key=lambda item: item.version))
        versions = [item.version for item in self.migrations]
        if len(set(versions)) != len(versions) or versions != list(range(1, len(versions) + 1)):
            raise ValueError("migration_versions_must_be_contiguous")
        if namespace_migrations is None:
            namespace_migrations = NAMESPACE_MIGRATIONS
        self.namespace_migrations = validate_namespace_registry(tuple(namespace_migrations))
        if any(
            migration._registry_token is not _REGISTRY_TOKEN
            for migration in self.namespace_migrations
        ):
            raise ValueError("namespace_registry_not_trusted")

    def run(self) -> tuple[int, ...]:
        """Apply pending migrations and return the versions applied now."""

        applied_now: list[int] = []
        with self.backend.session() as connection:
            # Python's sqlite3 driver does not implicitly start a transaction
            # for DDL. Keep this scoped to migrations so legacy repositories
            # remain free to use their own BEGIN IMMEDIATE boundaries.
            if self.backend.backend_name == "sqlite":
                connection.execute("BEGIN IMMEDIATE")
            else:
                connection.execute("SELECT pg_advisory_xact_lock(%s)", (_MIGRATION_LOCK_KEY,))
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
            if self.namespace_migrations:
                self._ensure_namespace_metadata(connection)
            applied = {
                int(row["version"])
                for row in connection.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                ).fetchall()
            }
            for migration in self.migrations:
                if migration.version in applied:
                    continue
                migration.apply(connection, self.backend.backend_name)
                connection.execute(
                    """
                    INSERT INTO schema_migrations(version, applied_at)
                    VALUES (?, CURRENT_TIMESTAMP)
                    ON CONFLICT (version) DO NOTHING
                    """,
                    (migration.version,),
                )
                applied_now.append(migration.version)
            self._run_namespace_migrations(connection)
        return tuple(applied_now)

    def _ensure_namespace_metadata(self, connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS migration_records (
                namespace TEXT NOT NULL,
                migration_key TEXT NOT NULL,
                display_version INTEGER,
                name TEXT NOT NULL,
                source_digest TEXT NOT NULL,
                prerequisites_json TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('applying', 'applied')),
                started_at TEXT,
                applied_at TEXT,
                PRIMARY KEY(namespace, migration_key),
                CHECK(
                    (status = 'applied' AND started_at IS NOT NULL AND applied_at IS NOT NULL)
                    OR (status = 'applying' AND started_at IS NOT NULL AND applied_at IS NULL)
                )
            )
            """
        )

    def _run_namespace_migrations(self, connection) -> None:
        for migration in self.namespace_migrations:
            row = connection.execute(
                """
                SELECT namespace, migration_key, display_version, name,
                       source_digest, prerequisites_json, status, started_at, applied_at
                FROM migration_records
                WHERE namespace=? AND migration_key=?
                """,
                (migration.namespace, migration.migration_key),
            ).fetchone()
            if row is not None:
                self._validate_applied_record(row, migration)
                continue

            connection.execute(
                """
                INSERT INTO migration_records(
                    namespace, migration_key, display_version, name,
                    source_digest, prerequisites_json, status, started_at, applied_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'applying', CURRENT_TIMESTAMP, NULL)
                """,
                (
                    migration.namespace,
                    migration.migration_key,
                    migration.display_version,
                    migration.name,
                    migration.source_digest,
                    migration.prerequisites_json(),
                ),
            )
            migration.upgrade(connection)
            connection.execute(
                """
                UPDATE migration_records
                SET status='applied', applied_at=CURRENT_TIMESTAMP
                WHERE namespace=? AND migration_key=? AND status='applying'
                """,
                (migration.namespace, migration.migration_key),
            )

    @staticmethod
    def _validate_applied_record(row, migration: NamespaceMigration) -> None:
        values = {key: row[key] for key in (
            "namespace",
            "migration_key",
            "display_version",
            "name",
            "source_digest",
            "prerequisites_json",
            "status",
            "started_at",
            "applied_at",
        )} if hasattr(row, "keys") else {
            "namespace": row[0],
            "migration_key": row[1],
            "display_version": row[2],
            "name": row[3],
            "source_digest": row[4],
            "prerequisites_json": row[5],
            "status": row[6],
            "started_at": row[7],
            "applied_at": row[8],
        }
        if (
            values["status"] != "applied"
            or not values["started_at"]
            or not values["applied_at"]
        ):
            raise ValueError("inconsistent_migration_metadata")
        expected = {
            "namespace": migration.namespace,
            "migration_key": migration.migration_key,
            "display_version": migration.display_version,
            "name": migration.name,
            "source_digest": migration.source_digest,
            "prerequisites_json": migration.prerequisites_json(),
        }
        if any(values[key] != value for key, value in expected.items()):
            raise ValueError("migration_metadata_mismatch")


_MIGRATION_LOCK_KEY = int.from_bytes(
    hashlib.sha256(b"sentinel-dna:migration-runner:v2").digest()[:8],
    byteorder="big",
    signed=True,
)


__all__ = [
    "CORE_MIGRATIONS",
    "MIGRATIONS",
    "STAGING_MIGRATIONS",
    "CONTROLLED_ANALYST_PILOT_MIGRATIONS",
    "Migration",
    "NamespaceMigration",
    "MigrationRunner",
]

"""Portable, transactional runner for the authoritative schema chain."""

from __future__ import annotations

from .backend import DatabaseBackend
from .migrations.registry import MIGRATIONS, Migration


# Backward-compatible public name retained for existing callers.
CORE_MIGRATIONS = MIGRATIONS


class MigrationRunner:
    """Apply ordered migrations through the selected backend contract."""

    def __init__(
        self,
        backend: DatabaseBackend,
        migrations: tuple[Migration, ...] | None = None,
    ) -> None:
        self.backend = backend
        if migrations is None:
            migrations = MIGRATIONS
        self.migrations = tuple(sorted(migrations, key=lambda item: item.version))
        versions = [item.version for item in self.migrations]
        if len(set(versions)) != len(versions) or versions != list(range(1, len(versions) + 1)):
            raise ValueError("migration_versions_must_be_contiguous")

    def run(self) -> tuple[int, ...]:
        """Apply pending migrations and return the versions applied now."""

        applied_now: list[int] = []
        with self.backend.session() as connection:
            # Python's sqlite3 driver does not implicitly start a transaction
            # for DDL. Keep this scoped to migrations so legacy repositories
            # remain free to use their own BEGIN IMMEDIATE boundaries.
            if self.backend.backend_name == "sqlite":
                connection.execute("BEGIN")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
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
        return tuple(applied_now)


__all__ = ["CORE_MIGRATIONS", "MIGRATIONS", "Migration", "MigrationRunner"]

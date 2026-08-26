"""Portable, transactional runner for the normalized core schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .backend import DatabaseBackend
from .schema import SchemaBackend, core_schema_statements


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    statements: Callable[[SchemaBackend], tuple[str, ...]]


CORE_MIGRATIONS = (
    Migration(
        version=1,
        name="normalized_core_schema",
        statements=lambda backend: core_schema_statements(backend)[1:],
    ),
)


class MigrationRunner:
    """Apply ordered migrations through the selected backend contract."""

    def __init__(
        self,
        backend: DatabaseBackend,
        migrations: tuple[Migration, ...] = CORE_MIGRATIONS,
    ) -> None:
        self.backend = backend
        self.migrations = tuple(sorted(migrations, key=lambda item: item.version))
        versions = [item.version for item in self.migrations]
        if len(set(versions)) != len(versions) or versions != list(range(1, len(versions) + 1)):
            raise ValueError("migration_versions_must_be_contiguous")

    def run(self) -> tuple[int, ...]:
        """Apply pending migrations and return the versions applied now."""

        applied_now: list[int] = []
        with self.backend.session() as connection:
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
                for statement in migration.statements(self.backend.backend_name):
                    connection.execute(statement)
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


__all__ = ["CORE_MIGRATIONS", "Migration", "MigrationRunner"]

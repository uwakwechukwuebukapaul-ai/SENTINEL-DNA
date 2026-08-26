"""Compatibility facade for the backend boundary.

Existing repository call sites can continue importing ``DatabaseConnection``
and using SQLite paths. New wiring should use ``create_database_backend`` so
backend choice is explicit and centrally governed.
"""

from pathlib import Path
import os

from .backend import (
    DEFAULT_BUSY_TIMEOUT_MS,
    DatabaseBackend,
    DatabaseConfigurationError,
    DatabaseSettings,
    PostgreSQLBackend,
    SQLiteBackend,
    create_database_backend,
)


def resolve_database_path(database_path: str | Path | None = None) -> Path:
    """Resolve the SQLite path for legacy callers."""
    settings = DatabaseSettings.from_environment(
        database_url="",
        database_path=database_path,
    )
    return settings.database_path  # type: ignore[return-value]


DATABASE_PATH = resolve_database_path()


class DatabaseConnection:
    """Backward-compatible constructor at the new backend boundary.

    Passing a path explicitly always creates SQLite, preserving test and
    repository compatibility. With no path, ``DATABASE_URL`` is authoritative
    and selects PostgreSQL when configured.
    """

    def __new__(
        cls,
        database_path: str | Path | None = None,
        *,
        database_url: str | None = None,
        busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
    ) -> DatabaseBackend:
        if database_url is not None or (database_path is None and os.getenv("DATABASE_URL", "").strip()):
            return create_database_backend(
                database_url=database_url,
                require_postgresql=True,
                busy_timeout_ms=busy_timeout_ms,
            )
        return SQLiteBackend(database_path, busy_timeout_ms=busy_timeout_ms)


def database_for_environment(*, require_postgresql: bool | None = None) -> DatabaseBackend:
    """Resolve the application backend without opening a connection."""
    if require_postgresql is None:
        require_postgresql = os.getenv("SENTINEL_DNA_ENV", "").strip().lower() == "production"
    return create_database_backend(require_postgresql=require_postgresql)


# Kept for existing imports. The selected backend is still lazy with respect
# to network/database access; only configuration is resolved at import time.
database = database_for_environment()


__all__ = [
    "DATABASE_PATH",
    "DatabaseBackend",
    "DatabaseConfigurationError",
    "DatabaseConnection",
    "DatabaseSettings",
    "PostgreSQLBackend",
    "SQLiteBackend",
    "create_database_backend",
    "database",
    "database_for_environment",
    "resolve_database_path",
]

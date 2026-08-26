"""Database backend boundary.

This module owns backend selection and connection lifecycle concerns.  It is
intentionally independent from repository SQL: Phase 1 establishes the seam,
while repository SQL portability is a later phase.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Iterator, Literal, Mapping, Protocol
from urllib.parse import urlparse

from .errors import DatabaseError


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BUSY_TIMEOUT_MS = 5_000
BackendName = Literal["sqlite", "postgresql"]


class DatabaseConfigurationError(DatabaseError):
    """Raised when database configuration is absent or unsupported."""


class DatabaseBackend(Protocol):
    """Small contract consumed by repositories and services."""

    backend_name: BackendName

    def connect(self) -> Any:
        """Return a backend-native connection."""

    @contextmanager
    def session(self) -> Iterator[Any]:
        """Yield one transaction and close it after use."""
        yield  # pragma: no cover - protocol-only declaration


@dataclass(frozen=True)
class DatabaseSettings:
    """Resolved, non-secret database selection metadata."""

    backend: BackendName
    database_url: str = ""
    database_path: Path | None = None

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        database_url: str | None = None,
        database_path: str | Path | None = None,
        require_postgresql: bool = False,
    ) -> "DatabaseSettings":
        values = os.environ if environ is None else environ
        configured_url = (
            values.get("DATABASE_URL", "") if database_url is None else database_url
        ).strip()

        # DATABASE_URL is authoritative.  A path may still be present for
        # backwards-compatible metadata, but it is never selected when the
        # URL is configured.
        if configured_url:
            _validate_postgresql_url(configured_url)
            return cls("postgresql", database_url=configured_url)

        if require_postgresql:
            raise DatabaseConfigurationError(
                "DATABASE_URL must be configured with a PostgreSQL URL"
            )

        configured_path = (
            values.get("SENTINEL_DNA_DB_PATH") if database_path is None else database_path
        )
        if not configured_path:
            configured_path = PROJECT_ROOT / "soc.db"
        return cls("sqlite", database_path=Path(configured_path).expanduser().resolve())


def _validate_postgresql_url(database_url: str) -> None:
    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.netloc:
        raise DatabaseConfigurationError(
            "DATABASE_URL must use a valid PostgreSQL URL"
        )


class SQLiteBackend:
    """SQLite backend retained for local development and tests."""

    backend_name: BackendName = "sqlite"

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
    ) -> None:
        configured = database_path
        if configured is None:
            configured = os.getenv("SENTINEL_DNA_DB_PATH", PROJECT_ROOT / "soc.db")
        self.database_path = str(Path(configured).expanduser().resolve())
        self.busy_timeout_ms = max(0, int(busy_timeout_ms))

    def connect(self) -> Any:
        import sqlite3

        connection = sqlite3.connect(
            self.database_path,
            timeout=self.busy_timeout_ms / 1_000,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms};")
        return connection

    @contextmanager
    def session(self) -> Iterator[Any]:
        import sqlite3

        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise DatabaseError("Database transaction failed") from exc
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


class PostgreSQLBackend:
    """PostgreSQL backend using psycopg 3 with lazy driver loading."""

    backend_name: BackendName = "postgresql"

    def __init__(self, database_url: str, *, connect_timeout: int = 10) -> None:
        _validate_postgresql_url(database_url)
        self.database_url = database_url
        self.connect_timeout = max(1, int(connect_timeout))

    def connect(self) -> Any:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise DatabaseError(
                "PostgreSQL driver is unavailable; install the psycopg[binary] dependency"
            ) from exc

        try:
            return psycopg.connect(
                self.database_url,
                connect_timeout=self.connect_timeout,
                row_factory=dict_row,
            )
        except psycopg.Error as exc:
            # Do not include the URL: it may contain credentials.
            raise DatabaseError("PostgreSQL connection failed") from exc

    @contextmanager
    def session(self) -> Iterator[Any]:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception as exc:
            try:
                connection.rollback()
            except Exception:
                pass
            if isinstance(exc, DatabaseError):
                raise
            raise DatabaseError("Database transaction failed") from exc
        finally:
            connection.close()


def create_database_backend(
    *,
    environ: Mapping[str, str] | None = None,
    database_url: str | None = None,
    database_path: str | Path | None = None,
    require_postgresql: bool | None = None,
    busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
) -> DatabaseBackend:
    """Create the configured backend without opening a connection."""

    if require_postgresql is None:
        values = os.environ if environ is None else environ
        require_postgresql = values.get("SENTINEL_DNA_ENV", "").strip().lower() == "production"

    settings = DatabaseSettings.from_environment(
        environ,
        database_url=database_url,
        database_path=database_path,
        require_postgresql=require_postgresql,
    )
    if settings.backend == "postgresql":
        return PostgreSQLBackend(settings.database_url)
    return SQLiteBackend(settings.database_path, busy_timeout_ms=busy_timeout_ms)

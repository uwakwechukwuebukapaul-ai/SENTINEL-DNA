"""
Sentinel DNA
Database Connection Manager
"""

import sqlite3
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from .errors import DatabaseError


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_database_path(database_path=None) -> Path:
    """Resolve the application's SQLite database path consistently."""
    configured_path = database_path
    if configured_path is None:
        configured_path = os.getenv(
            "SENTINEL_DNA_DB_PATH",
            PROJECT_ROOT / "soc.db",
        )
    return Path(configured_path).expanduser().resolve()


DATABASE_PATH = resolve_database_path()
DEFAULT_BUSY_TIMEOUT_MS = 30_000

_WAL_INITIALIZATION_LOCK = threading.Lock()
_WAL_INITIALIZED_PATHS: set[str] = set()


class DatabaseConnection:
    """
    Production-ready SQLite connection manager.
    """

    def __init__(self, database_path=None, *, busy_timeout_ms=DEFAULT_BUSY_TIMEOUT_MS):
        self.database_path = str(resolve_database_path(database_path))
        self.busy_timeout_ms = max(0, int(busy_timeout_ms))

    def _ensure_wal(self, connection) -> None:
        """Initialize WAL once per process/database with bounded lock retry."""
        database_path = self.database_path
        if database_path in _WAL_INITIALIZED_PATHS:
            return

        with _WAL_INITIALIZATION_LOCK:
            if database_path in _WAL_INITIALIZED_PATHS:
                return

            deadline = time.monotonic() + self.busy_timeout_ms / 1_000
            while True:
                try:
                    mode = connection.execute(
                        "PRAGMA journal_mode;"
                    ).fetchone()[0]
                    if str(mode).lower() != "wal":
                        mode = connection.execute(
                            "PRAGMA journal_mode = WAL;"
                        ).fetchone()[0]
                    if str(mode).lower() != "wal":
                        raise sqlite3.OperationalError(
                            f"SQLite journal mode initialization returned {mode!r}"
                        )
                    _WAL_INITIALIZED_PATHS.add(database_path)
                    return
                except sqlite3.OperationalError as exc:
                    if "locked" not in str(exc).lower():
                        raise
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise
                    time.sleep(min(0.01, remaining))

    def connect(self):
        """
        Create SQLite connection.
        """

        connection = None
        try:
            connection = sqlite3.connect(
                self.database_path,
                timeout=self.busy_timeout_ms / 1_000,
            )

            connection.row_factory = sqlite3.Row

            connection.execute("PRAGMA foreign_keys = ON;")
            connection.execute(
                f"PRAGMA busy_timeout = {self.busy_timeout_ms};"
            )
            self._ensure_wal(connection)
            connection.execute("PRAGMA synchronous = NORMAL;")

            return connection
        except Exception:
            if connection is not None:
                connection.close()
            raise

    @contextmanager
    def session(self):
        """
        Safe database session.
        """

        connection = None

        try:
            connection = self.connect()

            yield connection

            connection.commit()

        except sqlite3.Error as exc:

            if connection is not None:
                connection.rollback()
            raise DatabaseError("Database transaction failed") from exc
        except Exception:
            if connection is not None:
                connection.rollback()
            raise

        finally:

            if connection is not None:
                connection.close()


database = DatabaseConnection()

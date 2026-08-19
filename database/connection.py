"""
Sentinel DNA
Database Connection Manager
"""

import sqlite3
import os
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
DEFAULT_BUSY_TIMEOUT_MS = 5_000


class DatabaseConnection:
    """
    Production-ready SQLite connection manager.
    """

    def __init__(self, database_path=None, *, busy_timeout_ms=DEFAULT_BUSY_TIMEOUT_MS):
        self.database_path = str(resolve_database_path(database_path))
        self.busy_timeout_ms = max(0, int(busy_timeout_ms))

    def connect(self):
        """
        Create SQLite connection.
        """

        connection = sqlite3.connect(
            self.database_path,
            timeout=self.busy_timeout_ms / 1_000,
        )

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA foreign_keys = ON;"
        )
        # Let SQLite wait a bounded period for a competing writer instead of
        # leaking transient SQLITE_BUSY errors from BEGIN IMMEDIATE callers.
        connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms};")

        connection.execute("PRAGMA journal_mode = WAL;")

        return connection

    @contextmanager
    def session(self):
        """
        Safe database session.
        """

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


database = DatabaseConnection()

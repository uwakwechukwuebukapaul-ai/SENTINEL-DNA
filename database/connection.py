"""
Sentinel DNA
Database Connection Manager
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .errors import DatabaseError


# Database file
DATABASE_PATH = Path("soc.db")


class DatabaseConnection:
    """
    Production-ready SQLite connection manager.
    """

    def __init__(self, database_path=DATABASE_PATH):
        self.database_path = str(database_path)

    def connect(self):
        """
        Create SQLite connection.
        """

        connection = sqlite3.connect(self.database_path)

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA foreign_keys = ON;"
        )

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

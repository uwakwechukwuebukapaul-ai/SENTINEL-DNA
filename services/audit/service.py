from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from database.connection import DatabaseConnection, database


class AuditService:
    def __init__(self, db: DatabaseConnection | None = None) -> None:
        self.db = db or database
        with self.db.session() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL,
                case_id TEXT, user_id INTEGER, details_json TEXT NOT NULL,
                created_at TEXT NOT NULL)""")

    def record(self, event_type: str, case_id: str | None = None, user_id: int | None = None, details: dict[str, Any] | None = None, connection: Any | None = None) -> None:
        import json
        if connection is not None:
            connection.execute(
                "INSERT INTO audit_events(event_type,case_id,user_id,details_json,created_at) VALUES(?,?,?,?,?)",
                (event_type, case_id, user_id, json.dumps(details or {}), datetime.now(timezone.utc).isoformat()),
            )
            return
        with self.db.session() as session:
            session.execute(
                "INSERT INTO audit_events(event_type,case_id,user_id,details_json,created_at) VALUES(?,?,?,?,?)",
                (event_type, case_id, user_id, json.dumps(details or {}), datetime.now(timezone.utc).isoformat()),
            )

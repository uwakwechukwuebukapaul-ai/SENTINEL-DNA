from pathlib import Path
from typing import Any

from database.backend import DatabaseBackend
from database.connection import DatabaseConnection, database


class AgentAuditLogger:
    """Backend-neutral append-only audit sink for agent orchestration."""

    def __init__(self, database_backend: str | Path | DatabaseBackend | None = None):
        self.backend = (
            database_backend
            if hasattr(database_backend, "connect")
            else DatabaseConnection(database_backend) if database_backend is not None else database
        )
        with self.backend.session() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS agent_audit (
                   event TEXT NOT NULL,
                   agent_id TEXT NOT NULL,
                   payload TEXT NOT NULL
                )"""
            )

    def record(self, event: str, agent_id: str = "", payload: Any = ""):
        with self.backend.session() as connection:
            connection.execute(
                "INSERT INTO agent_audit(event, agent_id, payload) VALUES (?, ?, ?)",
                (event, agent_id, str(payload)),
            )
        return {"event": event, "agent_id": agent_id, "payload": payload}

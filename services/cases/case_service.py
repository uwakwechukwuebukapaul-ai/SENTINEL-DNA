from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from database.connection import DatabaseConnection, database
from services.audit import AuditService
from .models import CaseAssignment


@dataclass(frozen=True)
class AuthorizedCaseAccess:
    case_id: str
    user_id: int
    role: str


class CaseService:
    def __init__(self, db: DatabaseConnection | None = None) -> None:
        self.db = db or database
        self.audit = AuditService(self.db)
        with self.db.session() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS case_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL UNIQUE,
                user_id INTEGER NOT NULL, assigned_by INTEGER, assigned_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE')""")
            connection.execute("""CREATE TABLE IF NOT EXISTS analyst_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL,
                user_id INTEGER NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL)""")

    def assign(self, case_id: str, user_id: int, assigned_by: int | None) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self.db.session() as connection:
            connection.execute("""INSERT INTO case_assignments(case_id,user_id,assigned_by,assigned_at,status)
                VALUES(?,?,?,?,?) ON CONFLICT(case_id) DO UPDATE SET user_id=excluded.user_id,
                assigned_by=excluded.assigned_by, assigned_at=excluded.assigned_at, status='ACTIVE'""",
                (case_id, user_id, assigned_by, now, "ACTIVE"))
        self.audit.record("CASE_ASSIGNED", case_id, assigned_by, {"user_id": user_id})
        return self.assignment(case_id) or {}

    def assignment(self, case_id: str) -> dict[str, Any] | None:
        with self.db.session() as connection:
            row = connection.execute("SELECT case_id,user_id,assigned_by,assigned_at,status FROM case_assignments WHERE case_id=?", (case_id,)).fetchone()
        return dict(row) if row else None

    def authorize(
        self,
        case_id: str,
        user_id: int | None,
        role: str | None,
    ) -> AuthorizedCaseAccess | None:
        """Return an authoritative case grant for an authenticated caller."""
        if not user_id or not role:
            return None
        normalized_role = str(role).strip().lower()
        if normalized_role in {"admin", "soc_manager"}:
            return AuthorizedCaseAccess(case_id, int(user_id), normalized_role)
        assignment = self.assignment(case_id)
        if (
            assignment
            and assignment.get("status") == "ACTIVE"
            and int(assignment.get("user_id", 0)) == int(user_id)
        ):
            return AuthorizedCaseAccess(case_id, int(user_id), normalized_role)
        return None

    def add_note(self, case_id: str, user_id: int, note: str) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self.db.session() as connection:
            cursor = connection.execute("INSERT INTO analyst_notes(case_id,user_id,note,created_at,updated_at) VALUES(?,?,?,?,?)", (case_id, user_id, note, now, now))
            row = connection.execute("SELECT * FROM analyst_notes WHERE id=?", (cursor.lastrowid,)).fetchone()
        self.audit.record("NOTE_CREATED", case_id, user_id)
        return dict(row)

    def notes(self, case_id: str) -> list[dict[str, Any]]:
        with self.db.session() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM analyst_notes WHERE case_id=? ORDER BY id DESC", (case_id,)).fetchall()]

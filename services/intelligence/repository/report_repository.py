"""SQLite persistence for analyst-ready investigation reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from database.connection import DatabaseConnection, database
from services.intelligence.reporting.report_models import InvestigationReport


class InvestigationReportRepository:
    def __init__(self, db: DatabaseConnection | None = None) -> None:
        self.db = db or database
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self.db.session() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS investigation_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL UNIQUE,
                    report_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )"""
            )

    def save(self, report: InvestigationReport) -> dict[str, Any]:
        payload = report.to_dict()
        now = datetime.now(timezone.utc).isoformat()
        encoded = json.dumps(payload)
        with self.db.session() as connection:
            connection.execute(
                """INSERT INTO investigation_reports
                (case_id, report_json, created_at, updated_at) VALUES (?, ?, ?, ?)
                ON CONFLICT(case_id) DO UPDATE SET report_json=excluded.report_json,
                updated_at=excluded.updated_at""",
                (report.case_id, encoded, report.created_at or now, now),
            )
        return self.get_by_case_id(report.case_id) or {}

    def get_by_case_id(self, case_id: str) -> dict[str, Any] | None:
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT report_json FROM investigation_reports WHERE case_id=?",
                (case_id,),
            ).fetchone()
        return json.loads(row["report_json"]) if row else None

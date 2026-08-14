"""SQLite persistence boundary for investigation intelligence memory."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import InvestigationMemoryRecord


class InvestigationMemoryRepository:
    def __init__(self, database: str | Path = ":memory:") -> None:
        self.database = str(database)
        self._connection = sqlite3.connect(self.database)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("""CREATE TABLE IF NOT EXISTS investigation_memory (
            memory_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, investigation_type TEXT NOT NULL,
            scenario TEXT NOT NULL, risk_level TEXT NOT NULL, confidence REAL NOT NULL,
            evidence_summary TEXT NOT NULL, reasoning_summary TEXT NOT NULL,
            mitre_techniques TEXT NOT NULL, outcome TEXT NOT NULL, created_at TEXT NOT NULL,
            synthetic_only INTEGER NOT NULL CHECK (synthetic_only IN (0, 1)))""")
        self._connection.commit()

    def save(self, record: InvestigationMemoryRecord) -> InvestigationMemoryRecord:
        self._connection.execute("""INSERT OR IGNORE INTO investigation_memory VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
            record.memory_id, record.case_id, record.investigation_type, record.scenario,
            record.risk_level, record.confidence, json.dumps(record.evidence_summary, default=str),
            json.dumps(record.reasoning_summary, default=str), json.dumps(record.mitre_techniques),
            json.dumps(record.outcome, default=str), record.created_at, int(record.synthetic_only)))
        self._connection.commit()
        return record

    @staticmethod
    def _record(row: sqlite3.Row) -> InvestigationMemoryRecord:
        data = dict(row)
        for key in ("evidence_summary", "reasoning_summary", "mitre_techniques", "outcome"):
            data[key] = json.loads(data[key])
        data["synthetic_only"] = bool(data["synthetic_only"])
        return InvestigationMemoryRecord(**data)

    def get_case_history(self, case_id: str) -> list[InvestigationMemoryRecord]:
        rows = self._connection.execute("SELECT * FROM investigation_memory WHERE case_id = ? ORDER BY created_at", (case_id,)).fetchall()
        return [self._record(row) for row in rows]

    def find_similar(self, investigation_type: str, scenario: str = "") -> list[InvestigationMemoryRecord]:
        rows = self._connection.execute("SELECT * FROM investigation_memory WHERE investigation_type = ? AND (? = '' OR scenario = ?) ORDER BY created_at DESC", (investigation_type, scenario, scenario)).fetchall()
        return [self._record(row) for row in rows]

    def all(self) -> list[InvestigationMemoryRecord]:
        return [self._record(row) for row in self._connection.execute("SELECT * FROM investigation_memory ORDER BY created_at DESC").fetchall()]


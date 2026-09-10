from __future__ import annotations
import json
from pathlib import Path

from database.backend import DatabaseBackend
from database.connection import DatabaseConnection
from database.portability import execute_statements

from .models import ThreatIndicator

class ThreatIntelligenceRepository:
    def __init__(self, database: str | Path | DatabaseBackend = ":memory:"):
        self.backend = database if hasattr(database, "connect") else DatabaseConnection(database)
        self.db = self.backend.connect()
        execute_statements(self.db, [
            "CREATE TABLE IF NOT EXISTS indicators (indicator_id TEXT PRIMARY KEY, indicator_type TEXT NOT NULL, value TEXT NOT NULL, payload TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS indicator_cases (indicator_id TEXT NOT NULL, case_id TEXT NOT NULL, PRIMARY KEY(indicator_id, case_id))",
            "CREATE INDEX IF NOT EXISTS idx_indicator_cases_indicator ON indicator_cases(indicator_id)",
        ])
        self.db.commit()
    def add_indicator(self, indicator: ThreatIndicator):
        self.db.execute(
            """INSERT INTO indicators(indicator_id, indicator_type, value, payload)
               VALUES (?, ?, ?, ?)
               ON CONFLICT (indicator_id) DO UPDATE SET
                 indicator_type=excluded.indicator_type,
                 value=excluded.value,
                 payload=excluded.payload""",
            (indicator.indicator_id, indicator.indicator_type, indicator.value, json.dumps(indicator.to_dict(), default=str)),
        )
        self.db.commit()
        return indicator
    def get_indicator(self, indicator_id: str):
        row = self.db.execute("SELECT payload FROM indicators WHERE indicator_id=?", (indicator_id,)).fetchone()
        return ThreatIndicator(**json.loads(row["payload"])) if row else None
    def search_indicator(self, value: str, indicator_type: str | None = None):
        rows = self.db.execute("SELECT payload FROM indicators WHERE value=? AND (? IS NULL OR indicator_type=?)", (value, indicator_type, indicator_type)).fetchall()
        return [ThreatIndicator(**json.loads(row["payload"])) for row in rows]
    def link_indicator_to_case(self, indicator_id: str, case_id: str):
        self.db.execute(
            "INSERT INTO indicator_cases(indicator_id, case_id) VALUES (?, ?) ON CONFLICT (indicator_id, case_id) DO NOTHING",
            (indicator_id, case_id),
        )
        self.db.commit()
    def get_related_cases(self, indicator_id: str):
        return [row["case_id"] for row in self.db.execute("SELECT case_id FROM indicator_cases WHERE indicator_id=?", (indicator_id,)).fetchall()]
    def close(self) -> None:
        self.db.close()

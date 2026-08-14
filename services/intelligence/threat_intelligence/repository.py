from __future__ import annotations
import json, sqlite3
from .models import ThreatIndicator

class ThreatIntelligenceRepository:
    def __init__(self, database: str = ":memory:"):
        self.db = sqlite3.connect(database); self.db.row_factory = sqlite3.Row
        self.db.executescript("CREATE TABLE IF NOT EXISTS indicators (indicator_id TEXT PRIMARY KEY, indicator_type TEXT, value TEXT, payload TEXT); CREATE TABLE IF NOT EXISTS indicator_cases (indicator_id TEXT, case_id TEXT, PRIMARY KEY(indicator_id, case_id));"); self.db.commit()
    def add_indicator(self, indicator: ThreatIndicator):
        self.db.execute("INSERT OR REPLACE INTO indicators VALUES (?, ?, ?, ?)", (indicator.indicator_id, indicator.indicator_type, indicator.value, json.dumps(indicator.to_dict(), default=str))); self.db.commit(); return indicator
    def get_indicator(self, indicator_id: str):
        row = self.db.execute("SELECT payload FROM indicators WHERE indicator_id=?", (indicator_id,)).fetchone(); return ThreatIndicator(**json.loads(row[0])) if row else None
    def search_indicator(self, value: str, indicator_type: str | None = None):
        rows = self.db.execute("SELECT payload FROM indicators WHERE value=? AND (? IS NULL OR indicator_type=?)", (value, indicator_type, indicator_type)).fetchall(); return [ThreatIndicator(**json.loads(r[0])) for r in rows]
    def link_indicator_to_case(self, indicator_id: str, case_id: str):
        self.db.execute("INSERT OR IGNORE INTO indicator_cases VALUES (?, ?)", (indicator_id, case_id)); self.db.commit()
    def get_related_cases(self, indicator_id: str):
        return [r[0] for r in self.db.execute("SELECT case_id FROM indicator_cases WHERE indicator_id=?", (indicator_id,)).fetchall()]

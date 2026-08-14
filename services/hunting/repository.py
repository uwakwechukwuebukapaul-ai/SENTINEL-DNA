from __future__ import annotations
import json, sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from .models import HuntFinding, HuntQuery, HuntResult, HuntStatus

class HuntRepository:
    def __init__(self, db_path: str = "soc.db"):
        self.db_path = db_path
        with sqlite3.connect(db_path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS hunts (hunt_id TEXT PRIMARY KEY,status TEXT,query_json TEXT NOT NULL,result_json TEXT NOT NULL,created_at TEXT NOT NULL)")
    def save(self, result: HuntResult) -> dict:
        payload = result.to_dict(); now = result.created_at or datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as db: db.execute("INSERT OR REPLACE INTO hunts VALUES (?,?,?,?,?)", (result.hunt_id, result.status.value, json.dumps(payload["query"]), json.dumps(payload), now))
        return payload
    def history(self, limit: int = 100) -> list[dict]:
        with sqlite3.connect(self.db_path) as db: db.row_factory = sqlite3.Row; return [json.loads(row["result_json"]) for row in db.execute("SELECT result_json FROM hunts ORDER BY created_at DESC LIMIT ?", (max(1,min(limit,100)),))]
    def get(self, hunt_id: str) -> dict | None:
        with sqlite3.connect(self.db_path) as db: db.row_factory = sqlite3.Row; row = db.execute("SELECT result_json FROM hunts WHERE hunt_id=?", (hunt_id,)).fetchone(); return json.loads(row["result_json"]) if row else None

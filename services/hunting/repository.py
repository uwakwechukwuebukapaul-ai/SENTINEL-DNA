from __future__ import annotations
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from database.backend import DatabaseBackend
from database.connection import DatabaseConnection, database
from .models import HuntFinding, HuntQuery, HuntResult, HuntStatus

class HuntRepository:
    def __init__(self, db_path: str | Path | DatabaseBackend | None = None):
        self.backend = (
            db_path
            if hasattr(db_path, "connect")
            else DatabaseConnection(db_path) if db_path is not None else database
        )
        self.db_path = str(getattr(self.backend, "database_path", ""))
        with self.backend.session() as db:
            db.execute("CREATE TABLE IF NOT EXISTS hunts (hunt_id TEXT PRIMARY KEY,status TEXT,query_json TEXT NOT NULL,result_json TEXT NOT NULL,created_at TEXT NOT NULL)")
    def save(self, result: HuntResult) -> dict:
        payload = result.to_dict(); now = result.created_at or datetime.now(timezone.utc).isoformat()
        with self.backend.session() as db:
            db.execute("INSERT INTO hunts(hunt_id,status,query_json,result_json,created_at) VALUES (?,?,?,?,?) ON CONFLICT (hunt_id) DO UPDATE SET status=excluded.status,query_json=excluded.query_json,result_json=excluded.result_json,created_at=excluded.created_at", (result.hunt_id, result.status.value, json.dumps(payload["query"]), json.dumps(payload), now))
        return payload
    def history(self, limit: int = 100) -> list[dict]:
        with self.backend.session() as db:
            return [json.loads(row["result_json"]) for row in db.execute("SELECT result_json FROM hunts ORDER BY created_at DESC LIMIT ?", (max(1,min(limit,100)),)).fetchall()]
    def get(self, hunt_id: str) -> dict | None:
        with self.backend.session() as db:
            row = db.execute("SELECT result_json FROM hunts WHERE hunt_id=?", (hunt_id,)).fetchone()
            return json.loads(row["result_json"]) if row else None

"""SQLite persistence for normalized investigation intelligence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from database.connection import DatabaseConnection, database
from services.intelligence.models.investigation_intelligence import (
    InvestigationIntelligence,
)


class IntelligenceRepository:
    """Store and retrieve immutable-ish intelligence snapshots."""

    def __init__(self, db: DatabaseConnection | None = None) -> None:
        self.db = db or database
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self.db.session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS investigation_intelligence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL,
                    risk_score REAL NOT NULL,
                    risk_severity TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    findings_json TEXT NOT NULL,
                    recommendations_json TEXT NOT NULL,
                    mitre_json TEXT NOT NULL,
                    iocs_json TEXT NOT NULL,
                    attack_story TEXT,
                    timeline_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def save(
        self,
        case_id: str,
        intelligence: InvestigationIntelligence,
    ) -> dict[str, Any]:
        if not case_id or not isinstance(intelligence, InvestigationIntelligence):
            raise ValueError("case_id and InvestigationIntelligence are required")
        payload = intelligence.to_dict()
        now = datetime.now(timezone.utc).isoformat()
        encoded = {
            "findings_json": json.dumps(payload["findings"]),
            "recommendations_json": json.dumps(payload["recommendations"]),
            "mitre_json": json.dumps(payload["mitre_techniques"]),
            "iocs_json": json.dumps(payload["iocs"]),
            "timeline_json": json.dumps(payload["timeline"]),
            "metadata_json": json.dumps(payload["metadata"]),
        }
        with self.db.session() as connection:
            existing = connection.execute(
                "SELECT id, created_at FROM investigation_intelligence "
                "WHERE case_id=? ORDER BY id DESC LIMIT 1",
                (case_id,),
            ).fetchone()
            if existing:
                connection.execute(
                    """UPDATE investigation_intelligence SET
                    risk_score=?, risk_severity=?, confidence=?, findings_json=?,
                    recommendations_json=?, mitre_json=?, iocs_json=?, attack_story=?,
                    timeline_json=?, metadata_json=?, updated_at=? WHERE id=?""",
                    (payload["risk_score"], payload["risk_severity"], payload["confidence"],
                     encoded["findings_json"], encoded["recommendations_json"], encoded["mitre_json"],
                     encoded["iocs_json"], payload["attack_story"], encoded["timeline_json"],
                     encoded["metadata_json"], now, existing["id"]),
                )
            else:
                connection.execute(
                    """INSERT INTO investigation_intelligence
                    (case_id, risk_score, risk_severity, confidence, findings_json,
                     recommendations_json, mitre_json, iocs_json, attack_story,
                     timeline_json, metadata_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (case_id, payload["risk_score"], payload["risk_severity"], payload["confidence"],
                     encoded["findings_json"], encoded["recommendations_json"], encoded["mitre_json"],
                     encoded["iocs_json"], payload["attack_story"], encoded["timeline_json"],
                     encoded["metadata_json"], now, now),
                )
        return self.get_by_case_id(case_id) or {}

    def get_by_case_id(self, case_id: str) -> dict[str, Any] | None:
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT * FROM investigation_intelligence WHERE case_id=? ORDER BY id DESC LIMIT 1",
                (case_id,),
            ).fetchone()
        return self._decode(row) if row else None

    def update(self, case_id: str, intelligence: InvestigationIntelligence) -> dict[str, Any]:
        return self.save(case_id, intelligence)

    def list_history(self, case_id: str | None = None) -> list[dict[str, Any]]:
        with self.db.session() as connection:
            if case_id:
                rows = connection.execute("SELECT * FROM investigation_intelligence WHERE case_id=? ORDER BY id DESC", (case_id,)).fetchall()
            else:
                rows = connection.execute("SELECT * FROM investigation_intelligence ORDER BY id DESC").fetchall()
        return [self._decode(row) for row in rows]

    @staticmethod
    def _decode(row: Any) -> dict[str, Any]:
        return {
            "id": row["id"], "case_id": row["case_id"],
            "risk_score": row["risk_score"], "risk_severity": row["risk_severity"],
            "confidence": row["confidence"], "findings": json.loads(row["findings_json"]),
            "recommendations": json.loads(row["recommendations_json"]),
            "mitre": json.loads(row["mitre_json"]), "iocs": json.loads(row["iocs_json"]),
            "attack_story": row["attack_story"], "timeline": json.loads(row["timeline_json"]),
            "metadata": json.loads(row["metadata_json"]),
            "created_at": row["created_at"], "updated_at": row["updated_at"],
        }

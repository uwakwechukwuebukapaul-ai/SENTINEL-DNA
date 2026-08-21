"""Durable repository for canonical investigation artifacts."""

from __future__ import annotations

import json
from typing import Any

from .errors import RepositoryError


_SENSITIVE = {"authorization", "authorization_capability", "token", "password", "secret", "credential", "credentials", "database_path"}


def _safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items() if str(key).lower() not in _SENSITIVE}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    return value


class InvestigationArtifactRepository:
    def __init__(self, db=None) -> None:
        if db is None:
            from database.connection import database
            db = database
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.db.session() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS investigation_artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    investigation_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    tenant_id TEXT,
                    artifact_type TEXT NOT NULL,
                    artifact_payload_json TEXT NOT NULL,
                    provenance_json TEXT NOT NULL,
                    evidence_refs_json TEXT NOT NULL,
                    confidence REAL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            connection.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_investigation ON investigation_artifacts(investigation_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_case ON investigation_artifacts(case_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_type ON investigation_artifacts(artifact_type)")

    def save_many(self, artifacts) -> list[dict[str, Any]]:
        values = [artifact.to_dict() if hasattr(artifact, "to_dict") else dict(artifact) for artifact in artifacts]
        try:
            # The shared database may be rebound after this repository is
            # constructed (isolated tests and worker initialization).
            self._ensure_schema()
            with self.db.session() as connection:
                for item in values:
                    connection.execute("""
                        INSERT INTO investigation_artifacts
                        (artifact_id, investigation_id, case_id, tenant_id, artifact_type,
                         artifact_payload_json, provenance_json, evidence_refs_json,
                         confidence, source, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(artifact_id) DO UPDATE SET
                            artifact_payload_json=excluded.artifact_payload_json,
                            provenance_json=excluded.provenance_json,
                            evidence_refs_json=excluded.evidence_refs_json,
                            confidence=excluded.confidence
                    """, (
                        item["artifact_id"], item["investigation_id"], item["case_id"], item.get("tenant_id"), item["artifact_type"],
                        json.dumps(_safe(item.get("payload", {})), sort_keys=True), json.dumps(_safe(item.get("provenance", {})), sort_keys=True),
                        json.dumps(_safe(item.get("evidence_refs", [])), sort_keys=True), item.get("confidence"), item.get("source", ""), item["created_at"],
                    ))
        except Exception as exc:
            raise RepositoryError("Unable to persist investigation artifacts") from exc
        return values

    def get_for_investigation(self, investigation_id: str, tenant_id: str | None = None, artifact_type: str | None = None) -> list[dict[str, Any]]:
        clauses = ["investigation_id=?"]
        params: list[Any] = [str(investigation_id)]
        if tenant_id:
            clauses.append("tenant_id=?")
            params.append(str(tenant_id))
        if artifact_type:
            clauses.append("artifact_type=?")
            params.append(str(artifact_type))
        query = "SELECT * FROM investigation_artifacts WHERE " + " AND ".join(clauses) + " ORDER BY created_at, artifact_id"
        with self.db.session() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row(row) for row in rows]

    @staticmethod
    def _row(row) -> dict[str, Any]:
        return {
            "artifact_id": row["artifact_id"], "investigation_id": row["investigation_id"], "case_id": row["case_id"],
            "tenant_id": row["tenant_id"], "artifact_type": row["artifact_type"], "payload": json.loads(row["artifact_payload_json"]),
            "provenance": json.loads(row["provenance_json"]), "evidence_refs": json.loads(row["evidence_refs_json"]),
            "confidence": row["confidence"], "source": row["source"], "created_at": row["created_at"],
        }

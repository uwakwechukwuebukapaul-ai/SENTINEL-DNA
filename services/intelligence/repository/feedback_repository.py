"""SQLite persistence for append-only analyst investigation feedback."""

from __future__ import annotations

import json
from typing import Any

from services.intelligence.investigation.analyst_feedback import AnalystFeedback


class InvestigationFeedbackRepository:
    """Persist feedback without updating the underlying AI investigation report."""

    def __init__(self, db):
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.db.session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS investigation_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    investigation_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    finding_id TEXT,
                    recommendation_id TEXT,
                    decision TEXT NOT NULL CHECK (decision IN ('accepted', 'rejected', 'modified', 'false_positive', 'escalated')),
                    reason TEXT NOT NULL DEFAULT '',
                    analyst_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    evidence_refs_json TEXT NOT NULL DEFAULT '[]',
                    artifact_refs_json TEXT NOT NULL DEFAULT '[]'
                )
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(investigation_feedback)").fetchall()}
            if "evidence_refs_json" not in columns:
                connection.execute("ALTER TABLE investigation_feedback ADD COLUMN evidence_refs_json TEXT NOT NULL DEFAULT '[]'")
            if "artifact_refs_json" not in columns:
                connection.execute("ALTER TABLE investigation_feedback ADD COLUMN artifact_refs_json TEXT NOT NULL DEFAULT '[]'")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_feedback_investigation ON investigation_feedback(tenant_id, investigation_id, created_at)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_feedback_case ON investigation_feedback(tenant_id, case_id, created_at)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_feedback_decision ON investigation_feedback(tenant_id, decision, created_at)")

    def save(self, feedback: AnalystFeedback) -> AnalystFeedback:
        metadata = json.dumps(feedback.metadata, sort_keys=True)
        evidence_refs = json.dumps(feedback.evidence_refs, sort_keys=True)
        artifact_refs = json.dumps(feedback.artifact_refs, sort_keys=True)
        with self.db.session() as connection:
            connection.execute(
                """
                INSERT INTO investigation_feedback
                (feedback_id, investigation_id, case_id, finding_id, recommendation_id, decision, reason, analyst_id, tenant_id, created_at, metadata_json, evidence_refs_json, artifact_refs_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (feedback.feedback_id, feedback.investigation_id, feedback.case_id, feedback.finding_id,
                 feedback.recommendation_id, feedback.decision, feedback.reason, feedback.analyst_id,
                 feedback.tenant_id, feedback.created_at, metadata, evidence_refs, artifact_refs),
            )
        return feedback

    @staticmethod
    def _from_row(row: Any) -> AnalystFeedback:
        return AnalystFeedback(
            feedback_id=row["feedback_id"], investigation_id=row["investigation_id"], case_id=row["case_id"],
            finding_id=row["finding_id"], recommendation_id=row["recommendation_id"], decision=row["decision"],
            reason=row["reason"], analyst_id=row["analyst_id"], tenant_id=row["tenant_id"],
            created_at=row["created_at"], metadata=json.loads(row["metadata_json"] or "{}"),
            evidence_refs=json.loads(row["evidence_refs_json"] or "[]"),
            artifact_refs=json.loads(row["artifact_refs_json"] or "[]"),
        )

    def list_for_investigation(self, tenant_id: str, investigation_id: str) -> list[AnalystFeedback]:
        with self.db.session() as connection:
            rows = connection.execute(
                # SQLite's implicit rowid preserves append order.  Analyst decisions
                # are an append-only history; wall-clock timestamps can tie or move
                # backward on a developer workstation and must not reorder decisions.
                "SELECT * FROM investigation_feedback WHERE tenant_id=? AND investigation_id=? ORDER BY rowid",
                (tenant_id, investigation_id),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def list_for_tenant(
        self,
        tenant_id: str,
        *,
        start: str | None = None,
        end: str | None = None,
        case_id: str | None = None,
        investigation_id: str | None = None,
    ) -> list[AnalystFeedback]:
        clauses = ["tenant_id=?"]
        parameters: list[str] = [str(tenant_id)]
        if start:
            clauses.append("created_at>=?")
            parameters.append(start)
        if end:
            clauses.append("created_at<=?")
            parameters.append(end)
        if case_id:
            clauses.append("case_id=?")
            parameters.append(str(case_id))
        if investigation_id:
            clauses.append("investigation_id=?")
            parameters.append(str(investigation_id))
        with self.db.session() as connection:
            rows = connection.execute(
                f"SELECT * FROM investigation_feedback WHERE {' AND '.join(clauses)} ORDER BY rowid",
                parameters,
            ).fetchall()
        return [self._from_row(row) for row in rows]

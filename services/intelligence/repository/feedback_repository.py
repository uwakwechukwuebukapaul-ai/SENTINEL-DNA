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
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_feedback_investigation ON investigation_feedback(tenant_id, investigation_id, created_at)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_feedback_case ON investigation_feedback(tenant_id, case_id, created_at)")

    def save(self, feedback: AnalystFeedback) -> AnalystFeedback:
        payload = json.dumps(feedback.metadata, sort_keys=True)
        with self.db.session() as connection:
            connection.execute(
                """
                INSERT INTO investigation_feedback
                (feedback_id, investigation_id, case_id, finding_id, recommendation_id, decision, reason, analyst_id, tenant_id, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (feedback.feedback_id, feedback.investigation_id, feedback.case_id, feedback.finding_id,
                 feedback.recommendation_id, feedback.decision, feedback.reason, feedback.analyst_id,
                 feedback.tenant_id, feedback.created_at, payload),
            )
        return feedback

    @staticmethod
    def _from_row(row: Any) -> AnalystFeedback:
        metadata = json.loads(row["metadata_json"] or "{}")
        return AnalystFeedback(
            feedback_id=row["feedback_id"], investigation_id=row["investigation_id"], case_id=row["case_id"],
            finding_id=row["finding_id"], recommendation_id=row["recommendation_id"], decision=row["decision"],
            reason=row["reason"], analyst_id=row["analyst_id"], tenant_id=row["tenant_id"],
            created_at=row["created_at"],
            helpful_rating=metadata.get("helpful_rating"),
            confidence_rating=metadata.get("confidence_rating"),
            estimated_time_saved=metadata.get("estimated_time_saved"),
            analyst_comments=metadata.get("analyst_comments", row["reason"]),
            metadata=metadata,
        )

    def list_for_investigation(self, tenant_id: str, investigation_id: str) -> list[AnalystFeedback]:
        with self.db.session() as connection:
            rows = connection.execute(
                "SELECT * FROM investigation_feedback WHERE tenant_id=? AND investigation_id=? ORDER BY created_at, feedback_id",
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
                f"SELECT * FROM investigation_feedback WHERE {' AND '.join(clauses)} ORDER BY created_at, feedback_id",
                parameters,
            ).fetchall()
        return [self._from_row(row) for row in rows]

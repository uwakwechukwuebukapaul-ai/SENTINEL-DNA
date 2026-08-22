"""Append-only evidence review lifecycle persistence."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from uuid import uuid4

REVIEW_STATES = {"pending_review", "assigned", "in_review", "reviewed", "accepted", "rejected", "requires_escalation", "completed"}


class EvidenceReviewRepository:
    def __init__(self, db):
        self.db = db
        with db.session() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS investigation_evidence_reviews (
                review_id TEXT PRIMARY KEY, investigation_id TEXT NOT NULL, case_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL, actor_id TEXT NOT NULL, evidence_id TEXT NOT NULL,
                previous_state TEXT NOT NULL, new_state TEXT NOT NULL, reason TEXT NOT NULL,
                created_at TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}')""")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_evidence_review_case ON investigation_evidence_reviews(tenant_id, case_id, evidence_id, created_at)")
            columns = {row[1] for row in connection.execute("PRAGMA table_info(investigation_evidence_reviews)").fetchall()}
            for name, definition in (("priority", "TEXT NOT NULL DEFAULT 'normal'"), ("assigned_to", "TEXT"), ("review_deadline", "TEXT")):
                if name not in columns:
                    connection.execute(f"ALTER TABLE investigation_evidence_reviews ADD COLUMN {name} {definition}")

    def append(self, *, investigation_id, case_id, tenant_id, actor_id, evidence_id, new_state, reason="", priority="normal", assigned_to=None, review_deadline=None, evidence_refs=None):
        if new_state not in REVIEW_STATES:
            raise ValueError("invalid_evidence_review_state")
        history = self.list_for_evidence(case_id, evidence_id, tenant_id=tenant_id)
        previous = history[-1]["new_state"] if history else "pending_review"
        event = {"review_id": f"ERV-{uuid4().hex}", "investigation_id": str(investigation_id), "case_id": str(case_id), "tenant_id": str(tenant_id), "actor_id": str(actor_id), "evidence_id": str(evidence_id), "previous_state": previous, "new_state": new_state, "reason": str(reason or "").strip()[:2000], "priority": str(priority or "normal"), "assigned_to": str(assigned_to) if assigned_to else None, "review_deadline": review_deadline, "evidence_refs": sorted({str(item) for item in (evidence_refs or [evidence_id]) if item}), "created_at": datetime.now(timezone.utc).isoformat(), "metadata": {"source": "evidence_review_boundary"}}
        with self.db.session() as connection:
            connection.execute("""INSERT INTO investigation_evidence_reviews
                (review_id, investigation_id, case_id, tenant_id, actor_id, evidence_id, previous_state, new_state, reason, created_at, metadata_json, priority, assigned_to, review_deadline)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (event["review_id"], event["investigation_id"], event["case_id"], event["tenant_id"], event["actor_id"], event["evidence_id"], event["previous_state"], event["new_state"], event["reason"], event["created_at"], json.dumps({**event["metadata"], "evidence_refs": event["evidence_refs"]}), event["priority"], event["assigned_to"], event["review_deadline"]))
        return event

    def list_for_case(self, case_id, *, tenant_id):
        with self.db.session() as connection:
            rows = connection.execute("SELECT * FROM investigation_evidence_reviews WHERE case_id=? AND tenant_id=? ORDER BY rowid", (str(case_id), str(tenant_id))).fetchall()
        return [{**dict(row), "metadata": json.loads(row["metadata_json"] or "{}")} for row in rows]

    def list_for_evidence(self, case_id, evidence_id, *, tenant_id):
        return [item for item in self.list_for_case(case_id, tenant_id=tenant_id) if str(item["evidence_id"]) == str(evidence_id)]

    def list_for_tenant(self, *, tenant_id, states=None, priority=None, assigned_to=None):
        clauses = ["tenant_id=?"]
        params = [str(tenant_id)]
        if states:
            values = list(states); clauses.append("new_state IN (" + ",".join("?" for _ in values) + ")"); params.extend(values)
        if priority:
            clauses.append("priority=?"); params.append(str(priority))
        if assigned_to:
            clauses.append("assigned_to=?"); params.append(str(assigned_to))
        with self.db.session() as connection:
            rows = connection.execute("SELECT * FROM investigation_evidence_reviews WHERE " + " AND ".join(clauses) + " ORDER BY created_at", params).fetchall()
        return [{**dict(row), "metadata": json.loads(row["metadata_json"] or "{}")} for row in rows]

    def current_queue(self, *, tenant_id, states=None, priority=None, assigned_to=None):
        items = self.list_for_tenant(tenant_id=tenant_id, states=states, priority=priority, assigned_to=assigned_to)
        latest = {}
        for item in items:
            latest[item["evidence_id"]] = item
        return list(latest.values())

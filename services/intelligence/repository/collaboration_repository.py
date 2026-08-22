"""Tenant-scoped append-only analyst collaboration records."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from uuid import uuid4


class AnalystCollaborationRepository:
    def __init__(self, db):
        self.db = db
        with db.session() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS investigation_collaboration_events (
                event_id TEXT PRIMARY KEY, investigation_id TEXT NOT NULL, case_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL, actor_id TEXT NOT NULL, event_kind TEXT NOT NULL,
                content TEXT NOT NULL, parent_event_id TEXT, evidence_id TEXT,
                mentions_json TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL)""")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_collab_case ON investigation_collaboration_events(tenant_id, case_id, created_at)")

    def append(self, *, investigation_id, case_id, tenant_id, actor_id, event_kind, content,
               parent_event_id=None, evidence_id=None, mentions=None):
        if not tenant_id or not actor_id or not case_id or not str(content or '').strip():
            raise ValueError("collaboration_identity_and_content_required")
        event = {"event_id": f"COL-{uuid4().hex}", "investigation_id": str(investigation_id), "case_id": str(case_id), "tenant_id": str(tenant_id), "actor_id": str(actor_id), "event_kind": str(event_kind), "content": str(content).strip()[:4000], "parent_event_id": str(parent_event_id) if parent_event_id else None, "evidence_id": str(evidence_id) if evidence_id else None, "mentions": sorted({str(item) for item in (mentions or []) if item}), "created_at": datetime.now(timezone.utc).isoformat()}
        with self.db.session() as connection:
            connection.execute("""INSERT INTO investigation_collaboration_events
                (event_id, investigation_id, case_id, tenant_id, actor_id, event_kind, content, parent_event_id, evidence_id, mentions_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (event["event_id"], event["investigation_id"], event["case_id"], event["tenant_id"], event["actor_id"], event["event_kind"], event["content"], event["parent_event_id"], event["evidence_id"], json.dumps(event["mentions"]), event["created_at"]))
        return event

    def list_for_case(self, case_id: str, *, tenant_id: str) -> list[dict]:
        with self.db.session() as connection:
            rows = connection.execute("SELECT * FROM investigation_collaboration_events WHERE case_id=? AND tenant_id=? ORDER BY rowid", (str(case_id), str(tenant_id))).fetchall()
        return [{**dict(row), "mentions": json.loads(row["mentions_json"] or "[]")} for row in rows]

    def list_for_tenant(self, *, tenant_id: str) -> list[dict]:
        with self.db.session() as connection:
            rows = connection.execute(
                "SELECT * FROM investigation_collaboration_events WHERE tenant_id=? ORDER BY created_at, rowid",
                (str(tenant_id),),
            ).fetchall()
        return [{**dict(row), "mentions": json.loads(row["mentions_json"] or "[]")} for row in rows]

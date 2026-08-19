"""Durable, tenant-scoped persistence for investigation quality assessments."""

from __future__ import annotations
import json
from typing import Any
from database.connection import database

class InvestigationQualityRepository:
    def __init__(self, db=None): self.db = db or database; self._ensure_schema()
    def _ensure_schema(self):
        with self.db.session() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS investigation_quality_assessments (id INTEGER PRIMARY KEY AUTOINCREMENT, quality_id TEXT NOT NULL UNIQUE, investigation_id TEXT NOT NULL, case_id TEXT NOT NULL, tenant_id TEXT NOT NULL, scores_json TEXT NOT NULL, evidence_refs_json TEXT NOT NULL DEFAULT '[]', artifact_refs_json TEXT NOT NULL DEFAULT '[]', provenance_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}')""")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_quality_investigation ON investigation_quality_assessments(tenant_id, investigation_id, created_at)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_quality_case ON investigation_quality_assessments(tenant_id, case_id, created_at)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_quality_tenant ON investigation_quality_assessments(tenant_id, created_at)")
    def save_assessment(self, assessment):
        if not assessment.tenant_id: raise ValueError("quality_assessment_tenant_required")
        scores = {key: getattr(assessment, key) for key in ("overall_score", "evidence_score", "enrichment_score", "reasoning_score", "mitre_mapping_score", "timeline_score", "confidence_score", "completeness_score", "quality_status")}
        with self.db.session() as connection:
            connection.execute("""INSERT INTO investigation_quality_assessments (quality_id, investigation_id, case_id, tenant_id, scores_json, evidence_refs_json, artifact_refs_json, provenance_json, created_at, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(quality_id) DO UPDATE SET scores_json=excluded.scores_json, evidence_refs_json=excluded.evidence_refs_json, artifact_refs_json=excluded.artifact_refs_json, provenance_json=excluded.provenance_json, metadata_json=excluded.metadata_json""", (assessment.quality_id, str(assessment.investigation_id), str(assessment.case_id or assessment.investigation_id), str(assessment.tenant_id), json.dumps(scores, sort_keys=True), json.dumps(sorted(set(assessment.evidence_refs))), json.dumps(sorted(set(assessment.artifact_refs))), json.dumps(assessment.provenance, sort_keys=True), assessment.created_at, json.dumps(assessment.metadata, sort_keys=True)))
        return assessment
    @staticmethod
    def _decode(row: Any):
        from .models import InvestigationQualityAssessment
        scores = json.loads(row["scores_json"] or "{}")
        return InvestigationQualityAssessment(investigation_id=row["investigation_id"], tenant_id=row["tenant_id"], case_id=row["case_id"], quality_id=row["quality_id"], created_at=row["created_at"], overall_score=scores.get("overall_score", 0), evidence_score=scores.get("evidence_score", 0), enrichment_score=scores.get("enrichment_score", 0), reasoning_score=scores.get("reasoning_score", 0), mitre_mapping_score=scores.get("mitre_mapping_score", 0), timeline_score=scores.get("timeline_score", 0), confidence_score=scores.get("confidence_score", 0), completeness_score=scores.get("completeness_score", 0), quality_status=scores.get("quality_status", "insufficient_data"), evidence_refs=json.loads(row["evidence_refs_json"] or "[]"), artifact_refs=json.loads(row["artifact_refs_json"] or "[]"), provenance=json.loads(row["provenance_json"] or "{}"), metadata=json.loads(row["metadata_json"] or "{}"))
    def get_assessment(self, tenant_id, investigation_id):
        with self.db.session() as connection: row = connection.execute("SELECT * FROM investigation_quality_assessments WHERE tenant_id=? AND investigation_id=? ORDER BY created_at DESC LIMIT 1", (str(tenant_id), str(investigation_id))).fetchone()
        return self._decode(row) if row else None
    def get_by_case_id(self, tenant_id, case_id):
        with self.db.session() as connection: row = connection.execute("SELECT * FROM investigation_quality_assessments WHERE tenant_id=? AND case_id=? ORDER BY created_at DESC LIMIT 1", (str(tenant_id), str(case_id))).fetchone()
        return self._decode(row) if row else None
    def list_assessments(self, tenant_id):
        with self.db.session() as connection: rows = connection.execute("SELECT * FROM investigation_quality_assessments WHERE tenant_id=? ORDER BY created_at, quality_id", (str(tenant_id),)).fetchall()
        return [self._decode(row) for row in rows]

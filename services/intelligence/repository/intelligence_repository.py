"""
Investigation intelligence repository.

Persistence layer for Sentinel DNA investigation intelligence.

Maintains compatibility with:
- InvestigationCoordinator
- API investigation workflow
- SQLite storage
- legacy tests
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ..models.investigation_intelligence import (
    InvestigationIntelligence,
)
from database.portability import identity_primary_key
from .errors import RepositoryError


class IntelligenceRepository:

    def __init__(self, db=None):
        """
        Supports dependency injection and legacy construction.
        """

        if db is None:
            from database.connection import database as default_db
            db = default_db

        self.db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Ensure the repository table exists for legacy/default construction."""
        with self.db.session() as connection:
            identity = identity_primary_key(self.db.backend_name)
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS investigation_intelligence (
                    id {identity},
                    case_id TEXT NOT NULL,
                    risk_score REAL DEFAULT 0,
                    risk_severity TEXT DEFAULT 'unknown',
                    confidence REAL DEFAULT 0,
                    findings_json TEXT DEFAULT '[]',
                    recommendations_json TEXT DEFAULT '[]',
                    mitre_json TEXT DEFAULT '[]',
                    iocs_json TEXT DEFAULT '[]',
                    attack_story TEXT DEFAULT '{{}}',
                    timeline_json TEXT DEFAULT '[]',
                    metadata_json TEXT DEFAULT '{{}}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _serialize(value: Any) -> str:
        """
        Convert Python objects into SQLite-safe strings.
        """

        if value is None:
            return ""

        if isinstance(value, str):
            return value

        return json.dumps(
            value,
            default=str,
        )


    def save(
        self,
        case_id: str,
        intelligence: InvestigationIntelligence,
    ) -> dict[str, Any]:
        """
        Persist investigation intelligence.
        """

        if not case_id:
            raise ValueError(
                "case_id required"
            )

        if not isinstance(
            intelligence,
            InvestigationIntelligence,
        ):
            raise ValueError(
                "Invalid intelligence object"
            )


        payload = intelligence.to_dict()
        try:
            from services.observability import ObservabilityService
            ObservabilityService().event("investigation_repository_save", case_id=case_id, operation="save", component="intelligence_repository", status="started")
        except Exception:
            pass

        now = datetime.now(
            timezone.utc
        ).isoformat()


        encoded = {

            "findings_json":
                self._serialize(
                    payload.get(
                        "findings",
                        [],
                    )
                ),

            "recommendations_json":
                self._serialize(
                    payload.get(
                        "recommendations",
                        [],
                    )
                ),

            "mitre_json":
                self._serialize(
                    payload.get(
                        "mitre_techniques",
                        [],
                    )
                ),

            "iocs_json":
                self._serialize(
                    payload.get(
                        "iocs",
                        [],
                    )
                ),

            "timeline_json":
                self._serialize(
                    payload.get(
                        "timeline",
                        [],
                    )
                ),

            "metadata_json":
                self._serialize(
                    payload.get(
                        "metadata",
                        {},
                    )
                ),
        }


        attack_story = self._serialize(
            payload.get(
                "attack_story",
                {},
            )
        )


        try:
            with self.db.session() as connection:

                existing = connection.execute(
                """
                SELECT id
                FROM investigation_intelligence
                WHERE case_id=?
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    case_id,
                ),
            ).fetchone()


                if existing:

                    connection.execute(
                    """
                    UPDATE investigation_intelligence

                    SET
                    risk_score=?,
                    risk_severity=?,
                    confidence=?,
                    findings_json=?,
                    recommendations_json=?,
                    mitre_json=?,
                    iocs_json=?,
                    attack_story=?,
                    timeline_json=?,
                    metadata_json=?,
                    updated_at=?

                    WHERE id=?

                    """,
                    (

                        payload.get(
                            "risk_score",
                            0,
                        ),

                        payload.get(
                            "risk_severity",
                            "unknown",
                        ),

                        payload.get(
                            "confidence",
                            0,
                        ),

                        encoded["findings_json"],

                        encoded["recommendations_json"],

                        encoded["mitre_json"],

                        encoded["iocs_json"],

                        attack_story,

                        encoded["timeline_json"],

                        encoded["metadata_json"],

                        now,

                        existing["id"],
                    ),
                )


                else:

                    connection.execute(
                    """
                    INSERT INTO investigation_intelligence
                    (
                        case_id,
                        risk_score,
                        risk_severity,
                        confidence,
                        findings_json,
                        recommendations_json,
                        mitre_json,
                        iocs_json,
                        attack_story,
                        timeline_json,
                        metadata_json,
                        created_at,
                        updated_at
                    )

                    VALUES
                    (
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?
                    )

                    """,

                    (

                        case_id,

                        payload.get(
                            "risk_score",
                            0,
                        ),

                        payload.get(
                            "risk_severity",
                            "unknown",
                        ),

                        payload.get(
                            "confidence",
                            0,
                        ),

                        encoded["findings_json"],

                        encoded["recommendations_json"],

                        encoded["mitre_json"],

                        encoded["iocs_json"],

                        attack_story,

                        encoded["timeline_json"],

                        encoded["metadata_json"],

                        now,

                        now,
                    ),
                )


            return payload
        except (ValueError, RepositoryError):
            raise
        except Exception as exc:
            try:
                from services.observability import ObservabilityService
                ObservabilityService().event("investigation_repository_save", case_id=case_id, operation="save", component="intelligence_repository", status="failed", metadata={"error_type": type(exc).__name__})
            except Exception:
                pass
            raise RepositoryError("Unable to persist investigation intelligence") from exc



    def get_by_case_id(
        self,
        case_id: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve stored intelligence.
        """

        with self.db.session() as connection:

            row = connection.execute(
                """
                SELECT *
                FROM investigation_intelligence
                WHERE case_id=?
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    case_id,
                ),
            ).fetchone()


        if row is None:
            return None


        payload = dict(row)
        for column, key, default in (
            ("findings_json", "findings", []),
            ("recommendations_json", "recommendations", []),
            ("mitre_json", "mitre_techniques", []),
            ("iocs_json", "iocs", []),
            ("timeline_json", "timeline", []),
            ("metadata_json", "metadata", {}),
        ):
            try:
                payload[key] = json.loads(payload.get(column) or json.dumps(default))
            except (TypeError, ValueError):
                payload[key] = default
        payload["attack_story"] = payload.get("attack_story") or ""
        return payload

    def get_by_case_id_for_tenant(self, case_id: str, tenant_id: str) -> dict[str, Any] | None:
        payload = self.get_by_case_id(case_id)
        if not payload:
            return None
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        return payload if str(metadata.get("tenant_id") or "") == str(tenant_id) else None

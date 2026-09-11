"""Portable persistence for the FAVP operations layer.

The repository stores program metadata and references, never raw evidence or
credentials.  All tenant-scoped reads include the tenant predicate.  Result,
feedback, provenance, invitation, and timeline rows are append-only at the
database boundary.
"""

from __future__ import annotations

import json
from typing import Any

from database.connection import DatabaseConnection, database
from database.portability import append_only_statements, table_columns
from .scenarios import FAVP_SCENARIOS


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _row(row: Any) -> dict[str, Any]:
    return dict(row) if row else {}


class FAVPOperationsRepository:
    """Database repository for explicit, tenant-scoped FAVP records."""

    def __init__(self, db: DatabaseConnection | None = None) -> None:
        self.db = db or database
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        statements = (
            """
            CREATE TABLE IF NOT EXISTS favp_organizations (
                organization_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                organization_ref TEXT NOT NULL,
                display_name TEXT NOT NULL,
                sector TEXT,
                size_band TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(tenant_id, organization_ref)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS favp_participants (
                participant_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                participant_ref TEXT NOT NULL,
                display_name TEXT NOT NULL,
                actor_identity_ref TEXT,
                role_title TEXT,
                contact_reference TEXT,
                state TEXT NOT NULL,
                nda_status TEXT NOT NULL,
                terms_status TEXT NOT NULL,
                onboarding_status TEXT NOT NULL,
                access_status TEXT NOT NULL,
                validation_phase TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                UNIQUE(tenant_id, participant_ref)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS favp_invitations (
                invitation_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                participant_id TEXT NOT NULL,
                invitation_ref TEXT NOT NULL,
                channel TEXT NOT NULL,
                status TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                response_at TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(tenant_id, invitation_ref)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS favp_timeline (
                timeline_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                participant_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                from_state TEXT,
                to_state TEXT,
                actor_ref TEXT NOT NULL,
                notes TEXT,
                occurred_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS favp_scenarios (
                scenario_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                evidence_package_json TEXT NOT NULL,
                objectives_json TEXT NOT NULL,
                mitre_mapping_json TEXT NOT NULL,
                evaluation_criteria_json TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                version TEXT NOT NULL,
                synthetic INTEGER NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS favp_assignments (
                assignment_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                participant_id TEXT NOT NULL,
                scenario_id TEXT NOT NULL,
                assigned_by TEXT NOT NULL,
                assigned_at TEXT NOT NULL,
                status TEXT NOT NULL,
                UNIQUE(tenant_id, participant_id, scenario_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS favp_results (
                result_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                participant_id TEXT NOT NULL,
                scenario_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                duration_seconds REAL NOT NULL,
                analyst_decision TEXT NOT NULL,
                ai_recommendation_json TEXT NOT NULL,
                evidence_references_json TEXT NOT NULL,
                provenance_references_json TEXT NOT NULL,
                features_used_json TEXT NOT NULL,
                limitations_json TEXT NOT NULL,
                ai_investigation_version TEXT NOT NULL,
                platform_build_version TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS favp_feedback (
                feedback_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                participant_id TEXT NOT NULL,
                scenario_id TEXT NOT NULL,
                result_id TEXT NOT NULL,
                trust_evidence INTEGER NOT NULL,
                reasoning_understanding INTEGER NOT NULL,
                confidence_rating INTEGER NOT NULL,
                provenance_clarity INTEGER NOT NULL,
                timeline_usefulness INTEGER NOT NULL,
                ioc_enrichment_usefulness INTEGER NOT NULL,
                evidence_quality INTEGER NOT NULL,
                would_pay INTEGER,
                requested_tier TEXT,
                requested_integrations_json TEXT NOT NULL,
                deployment_requirements_json TEXT NOT NULL,
                incorrect_reasoning TEXT,
                limitations TEXT,
                comments TEXT,
                created_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS favp_evidence_records (
                evidence_record_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                participant_id TEXT NOT NULL,
                result_id TEXT NOT NULL,
                evidence_reference TEXT NOT NULL,
                provenance_reference TEXT NOT NULL,
                evidence_sha256 TEXT NOT NULL,
                ai_investigation_version TEXT NOT NULL,
                platform_build_version TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                previous_record_hash TEXT,
                record_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """,
        )
        with self.db.session() as connection:
            for statement in statements:
                connection.execute(statement)
            participant_columns = table_columns(connection, self.db.backend_name, "favp_participants")
            if "actor_identity_ref" not in participant_columns:
                connection.execute("ALTER TABLE favp_participants ADD COLUMN actor_identity_ref TEXT")
            for table, prefix in (
                ("favp_invitations", "favp_invitations_append_only"),
                ("favp_timeline", "favp_timeline_append_only"),
                ("favp_results", "favp_results_append_only"),
                ("favp_feedback", "favp_feedback_append_only"),
                ("favp_evidence_records", "favp_evidence_append_only"),
            ):
                for statement in append_only_statements(
                    self.db.backend_name,
                    table_name=table,
                    trigger_prefix=prefix,
                    error_message=f"{table}_are_append_only",
                ):
                    connection.execute(statement)
            for scenario in FAVP_SCENARIOS.values():
                connection.execute(
                    """INSERT INTO favp_scenarios(
                        scenario_id,name,description,evidence_package_json,
                        objectives_json,mitre_mapping_json,evaluation_criteria_json,
                        difficulty,version,synthetic
                    ) VALUES(?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(scenario_id) DO NOTHING""",
                    (
                        scenario["scenario_id"], scenario["name"], scenario["description"],
                        _json(scenario["evidence_package"]),
                        _json(scenario["expected_investigation_objectives"]),
                        _json(scenario["mitre_attack_mapping"]),
                        _json(scenario["evaluation_criteria"]),
                        scenario["difficulty"], scenario["version"], 1,
                    ),
                )
            for index in (
                "CREATE INDEX IF NOT EXISTS idx_favp_org_tenant ON favp_organizations(tenant_id, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_favp_participant_tenant ON favp_participants(tenant_id, state, updated_at)",
                "CREATE INDEX IF NOT EXISTS idx_favp_timeline_participant ON favp_timeline(tenant_id, participant_id, occurred_at)",
                "CREATE INDEX IF NOT EXISTS idx_favp_assignment_participant ON favp_assignments(tenant_id, participant_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_favp_result_tenant ON favp_results(tenant_id, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_favp_feedback_tenant ON favp_feedback(tenant_id, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_favp_evidence_tenant ON favp_evidence_records(tenant_id, sequence_number)",
            ):
                connection.execute(index)

    def get_organization(self, tenant_id: str, organization_id: str, *, connection: Any | None = None):
        statement = "SELECT * FROM favp_organizations WHERE tenant_id=? AND organization_id=?"
        if connection is None:
            with self.db.session() as owned:
                row = owned.execute(statement, (tenant_id, organization_id)).fetchone()
        else:
            row = connection.execute(statement, (tenant_id, organization_id)).fetchone()
        return _row(row) if row else None

    def list_organizations(self, tenant_id: str):
        with self.db.session() as connection:
            rows = connection.execute(
                "SELECT * FROM favp_organizations WHERE tenant_id=? ORDER BY created_at, organization_id",
                (tenant_id,),
            ).fetchall()
        return [_row(row) for row in rows]

    def get_organization_by_ref(self, tenant_id: str, organization_ref: str, *, connection: Any | None = None):
        """Resolve an organization by its tenant-scoped operator reference."""
        statement = "SELECT * FROM favp_organizations WHERE tenant_id=? AND organization_ref=?"
        if connection is None:
            with self.db.session() as owned:
                row = owned.execute(statement, (tenant_id, organization_ref)).fetchone()
        else:
            row = connection.execute(statement, (tenant_id, organization_ref)).fetchone()
        return _row(row) if row else None

    def get_participant(self, tenant_id: str, participant_id: str, *, connection: Any | None = None):
        statement = "SELECT * FROM favp_participants WHERE tenant_id=? AND participant_id=?"
        if connection is None:
            with self.db.session() as owned:
                row = owned.execute(statement, (tenant_id, participant_id)).fetchone()
        else:
            row = connection.execute(statement, (tenant_id, participant_id)).fetchone()
        return _row(row) if row else None

    def list_participants(self, tenant_id: str):
        with self.db.session() as connection:
            rows = connection.execute(
                "SELECT * FROM favp_participants WHERE tenant_id=? ORDER BY created_at, participant_id",
                (tenant_id,),
            ).fetchall()
        return [_row(row) for row in rows]

    def get_participant_by_ref(self, tenant_id: str, participant_ref: str, *, connection: Any | None = None):
        """Resolve a participant by reference without crossing a tenant boundary."""
        statement = "SELECT * FROM favp_participants WHERE tenant_id=? AND participant_ref=?"
        if connection is None:
            with self.db.session() as owned:
                row = owned.execute(statement, (tenant_id, participant_ref)).fetchone()
        else:
            row = connection.execute(statement, (tenant_id, participant_ref)).fetchone()
        return _row(row) if row else None

    def get_invitation_by_ref(self, tenant_id: str, invitation_ref: str, *, connection: Any | None = None):
        """Resolve one invitation by reference without crossing a tenant boundary."""
        statement = "SELECT * FROM favp_invitations WHERE tenant_id=? AND invitation_ref=?"
        if connection is None:
            with self.db.session() as owned:
                row = owned.execute(statement, (tenant_id, invitation_ref)).fetchone()
        else:
            row = connection.execute(statement, (tenant_id, invitation_ref)).fetchone()
        return _row(row) if row else None

    def get_invitation_by_participant_and_ref(
        self,
        tenant_id: str,
        participant_id: str,
        invitation_ref: str,
        *,
        connection: Any | None = None,
    ):
        """Resolve an invitation only when all lifecycle ownership keys match.

        ``invitation_ref`` is operator supplied and may be stale or occupied by
        another append-only row.  Recovery must therefore never use the ref as
        the ownership check by itself.
        """
        statement = (
            "SELECT * FROM favp_invitations "
            "WHERE tenant_id=? AND participant_id=? AND invitation_ref=?"
        )
        params = (tenant_id, participant_id, invitation_ref)
        if connection is None:
            with self.db.session() as owned:
                row = owned.execute(statement, params).fetchone()
        else:
            row = connection.execute(statement, params).fetchone()
        return _row(row) if row else None

    def get_assignment(self, tenant_id: str, participant_id: str, scenario_id: str, *, connection: Any | None = None):
        statement = "SELECT * FROM favp_assignments WHERE tenant_id=? AND participant_id=? AND scenario_id=?"
        if connection is None:
            with self.db.session() as owned:
                row = owned.execute(statement, (tenant_id, participant_id, scenario_id)).fetchone()
        else:
            row = connection.execute(statement, (tenant_id, participant_id, scenario_id)).fetchone()
        return _row(row) if row else None

    def list_assignments(self, tenant_id: str, participant_id: str | None = None):
        with self.db.session() as connection:
            if participant_id:
                rows = connection.execute(
                    "SELECT * FROM favp_assignments WHERE tenant_id=? AND participant_id=? ORDER BY assigned_at, assignment_id",
                    (tenant_id, participant_id),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM favp_assignments WHERE tenant_id=? ORDER BY assigned_at, assignment_id",
                    (tenant_id,),
                ).fetchall()
        return [_row(row) for row in rows]

    def list_results(self, tenant_id: str, participant_id: str | None = None):
        with self.db.session() as connection:
            query = "SELECT * FROM favp_results WHERE tenant_id=?"
            params: list[Any] = [tenant_id]
            if participant_id:
                query += " AND participant_id=?"
                params.append(participant_id)
            query += " ORDER BY created_at, result_id"
            rows = connection.execute(query, tuple(params)).fetchall()
        return [_row(row) for row in rows]

    def get_result(self, tenant_id: str, result_id: str):
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT * FROM favp_results WHERE tenant_id=? AND result_id=?",
                (tenant_id, result_id),
            ).fetchone()
        return _row(row) if row else None

    def list_feedback(self, tenant_id: str, participant_id: str | None = None):
        with self.db.session() as connection:
            query = "SELECT * FROM favp_feedback WHERE tenant_id=?"
            params: list[Any] = [tenant_id]
            if participant_id:
                query += " AND participant_id=?"
                params.append(participant_id)
            query += " ORDER BY created_at, feedback_id"
            rows = connection.execute(query, tuple(params)).fetchall()
        return [_row(row) for row in rows]

    def list_evidence(self, tenant_id: str, result_id: str | None = None):
        with self.db.session() as connection:
            query = "SELECT * FROM favp_evidence_records WHERE tenant_id=?"
            params: list[Any] = [tenant_id]
            if result_id:
                query += " AND result_id=?"
                params.append(result_id)
            query += " ORDER BY sequence_number, evidence_record_id"
            rows = connection.execute(query, tuple(params)).fetchall()
        return [_row(row) for row in rows]

    def list_timeline(self, tenant_id: str, participant_id: str):
        with self.db.session() as connection:
            rows = connection.execute(
                "SELECT * FROM favp_timeline WHERE tenant_id=? AND participant_id=? ORDER BY occurred_at, timeline_id",
                (tenant_id, participant_id),
            ).fetchall()
        return [_row(row) for row in rows]

    def list_invitation(self, tenant_id: str, participant_id: str):
        with self.db.session() as connection:
            rows = connection.execute(
                "SELECT * FROM favp_invitations WHERE tenant_id=? AND participant_id=? ORDER BY created_at, invitation_id",
                (tenant_id, participant_id),
            ).fetchall()
        return [_row(row) for row in rows]

    def scenario(self, scenario_id: str):
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT * FROM favp_scenarios WHERE scenario_id=? AND synthetic=1",
                (scenario_id,),
            ).fetchone()
        if not row:
            return None
        item = _row(row)
        item["evidence_package"] = json.loads(item.pop("evidence_package_json") or "{}")
        item["expected_investigation_objectives"] = json.loads(item.pop("objectives_json") or "[]")
        item["mitre_attack_mapping"] = json.loads(item.pop("mitre_mapping_json") or "[]")
        item["evaluation_criteria"] = json.loads(item.pop("evaluation_criteria_json") or "[]")
        item["synthetic"] = bool(item["synthetic"])
        return item

    def all_scenarios(self):
        return [self.scenario(scenario_id) for scenario_id in FAVP_SCENARIOS]

    def next_evidence_sequence(self, tenant_id: str, connection: Any) -> tuple[int, str | None]:
        row = connection.execute(
            "SELECT sequence_number, record_hash FROM favp_evidence_records WHERE tenant_id=? ORDER BY sequence_number DESC LIMIT 1",
            (tenant_id,),
        ).fetchone()
        if not row:
            return 1, None
        return int(row["sequence_number"] if hasattr(row, "keys") else row[0]) + 1, (row["record_hash"] if hasattr(row, "keys") else row[1])


__all__ = ["FAVPOperationsRepository"]

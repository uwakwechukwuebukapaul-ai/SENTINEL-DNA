"""Fail-closed launch checks for the non-production FAVP operator environment."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from database.portability import table_columns
from services.auth.permissions import PERMISSIONS
from .execution_scenarios import FAVP_EXECUTION_SCENARIOS


FAVP_LAUNCH_READY = "FAVP_STAGING_LAUNCH_READY"
FAVP_LAUNCH_BLOCKED = "FAVP_STAGING_LAUNCH_BLOCKED"
_REQUIRED_TABLES = (
    "favp_organizations", "favp_participants", "favp_invitations", "favp_timeline",
    "favp_scenarios", "favp_assignments", "favp_results", "favp_feedback",
    "favp_evidence_records", "favp_execution_profiles", "favp_execution_scenarios",
    "favp_execution_sessions", "favp_execution_reviews", "favp_evidence_validations",
    "audit_events",
)
# Versioned scenario catalogs are global, immutable reference data. All
# participant, session, result, feedback, evidence, and audit records remain
# tenant-scoped.
_TENANT_TABLES = tuple(table for table in _REQUIRED_TABLES if table not in {"favp_scenarios", "favp_execution_scenarios"})
_REPORT_SECTIONS = (
    "Executive Summary", "Program Scope", "Participant Summary", "Scenario Coverage",
    "Analyst Feedback Summary", "Evidence Quality Assessment", "AI Boundary Findings",
    "Security Controls Tested", "Limitations", "Commercial Signals", "Next Recommendations",
)


def _check(name: str, passed: bool, reason: str, **details: Any) -> dict[str, Any]:
    result = {"name": name, "status": "PASS" if passed else "BLOCKED", "reason": reason}
    if details:
        result["details"] = details
    return result


def _scalar(row: Any, key: str) -> Any:
    """Read a scalar from SQLite rows and PostgreSQL mapping rows."""
    return row[key] if hasattr(row, "keys") else row[0]


class FAVPStagingLaunchReadiness:
    """Inspect, but never activate, the first controlled FAVP environment."""

    def __init__(
        self,
        db: Any = None,
        audit_service: Any = None,
        execution_service: Any = None,
        *,
        environ: Mapping[str, str] | None = None,
        evidence_dir: str | Path | None = None,
        compose_path: str | Path | None = None,
        tenant_id: str | None = None,
    ) -> None:
        self.db = db
        self.audit_service = audit_service
        self.execution = execution_service
        self.tenant_id = str(tenant_id).strip() if tenant_id else None
        self.environ = os.environ if environ is None else environ
        configured_evidence = evidence_dir if evidence_dir is not None else self.environ.get("SENTINEL_DNA_FAVP_EVIDENCE_DIR", "")
        self.evidence_dir = Path(str(configured_evidence)).expanduser() if str(configured_evidence).strip() else None
        self.compose_path = Path(compose_path).expanduser() if compose_path else None

    def _table_columns(self, table: str) -> set[str]:
        if self.db is None:
            return set()
        with self.db.session() as connection:
            return table_columns(connection, self.db.backend_name, table)

    def _database_schema(self) -> tuple[bool, dict[str, Any]]:
        missing = []
        for table in _REQUIRED_TABLES:
            try:
                if not self._table_columns(table):
                    missing.append(table)
            except Exception:
                missing.append(table)
        migration_version = None
        if not missing and getattr(self.db, "backend_name", None) == "postgresql":
            try:
                with self.db.session() as connection:
                    row = connection.execute(
                        "SELECT MAX(version) AS version FROM schema_migrations"
                    ).fetchone()
                    migration_version = row["version"] if hasattr(row, "keys") else row[0]
            except Exception:
                migration_version = None
            if migration_version is None or int(migration_version) < 9:
                missing.append("schema_migrations:staging_favp_version_9")
        return not missing, {
            "missing_tables": missing,
            "staging_migration_version": int(migration_version) if migration_version is not None else None,
        }

    def _audit_trail(self) -> tuple[bool, dict[str, Any]]:
        if self.db is None or not callable(getattr(self.audit_service, "record", None)):
            return False, {"audit_events": 0, "append_only_guards": 0}
        try:
            with self.db.session() as connection:
                if self.tenant_id:
                    event_count = _scalar(connection.execute("SELECT COUNT(*) AS count FROM audit_events WHERE tenant_id=?", (self.tenant_id,)).fetchone(), "count")
                else:
                    event_count = _scalar(connection.execute("SELECT COUNT(*) AS count FROM audit_events").fetchone(), "count")
                if self.db.backend_name == "sqlite":
                    guards = _scalar(connection.execute("SELECT COUNT(*) AS count FROM sqlite_master WHERE type='trigger' AND name LIKE 'audit_events_append_only_%'").fetchone(), "count")
                else:
                    guards = _scalar(connection.execute("""SELECT COUNT(*) AS count
                        FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
                        WHERE c.relname='audit_events' AND NOT t.tgisinternal
                          AND t.tgname LIKE 'audit_events_append_only_%'""").fetchone(), "count")
            passed = event_count > 0 and guards >= 2
            return passed, {"audit_events": int(event_count), "append_only_guards": int(guards)}
        except Exception:
            return False, {"audit_events": 0, "append_only_guards": 0}

    def _tenant_isolation(self) -> tuple[bool, dict[str, Any]]:
        missing = []
        for table in _TENANT_TABLES:
            try:
                if "tenant_id" not in self._table_columns(table):
                    missing.append(table)
            except Exception:
                missing.append(table)
        permission_ok = {"pilot:read", "pilot:manage", "validation:execute"}.issubset(PERMISSIONS)
        probe_ok = False
        probe_details = {"probe": "not_run", "probe_records": 0}
        if not missing and self.db is not None:
            try:
                # Ephemeral records exercise the tenant predicate without
                # creating a user, organization, result, or validation row.
                with self.db.session() as connection:
                    connection.execute("CREATE TEMP TABLE favp_tenant_isolation_probe (record_id TEXT, tenant_id TEXT NOT NULL)")
                    connection.execute("INSERT INTO favp_tenant_isolation_probe(record_id,tenant_id) VALUES(?,?),(?,?)", ("probe-a", "tenant-a", "probe-b", "tenant-b"))
                    own = connection.execute("SELECT record_id FROM favp_tenant_isolation_probe WHERE tenant_id=?", ("tenant-a",)).fetchall()
                    foreign = connection.execute("SELECT record_id FROM favp_tenant_isolation_probe WHERE tenant_id=?", ("tenant-b",)).fetchall()
                own_id = own[0]["record_id"] if hasattr(own[0], "keys") else own[0][0]
                foreign_id = foreign[0]["record_id"] if hasattr(foreign[0], "keys") else foreign[0][0]
                probe_ok = len(own) == 1 and len(foreign) == 1 and own_id == "probe-a" and foreign_id == "probe-b"
                probe_details = {
                    "probe": "passed",
                    "probe_records": 2,
                    "foreign_record_excluded": foreign_id not in {own_id},
                }
            except Exception:
                probe_details = {"probe": "failed", "probe_records": 0}
        passed = not missing and permission_ok and self.environ.get("SENTINEL_DNA_TENANT_ISOLATION_ENABLED") == "1" and probe_ok
        return passed, {"tables_without_tenant_id": missing, **probe_details}

    def _onboarding(self) -> tuple[bool, dict[str, Any]]:
        if self.db is None:
            return False, {"active_profiles": 0, "invalid_active_profiles": 0}
        try:
            now = datetime.now(timezone.utc)
            with self.db.session() as connection:
                if self.tenant_id:
                    rows = connection.execute("""SELECT e.state,e.nda_status,e.terms_status,
                        e.onboarding_status,e.access_expires_at,p.state AS participant_state,
                        p.access_status AS participant_access_status
                        FROM favp_execution_profiles e
                        JOIN favp_participants p ON p.tenant_id=e.tenant_id
                          AND p.participant_id=e.participant_id
                        WHERE e.tenant_id=?""", (self.tenant_id,)).fetchall()
                else:
                    rows = connection.execute("""SELECT e.state,e.nda_status,e.terms_status,
                        e.onboarding_status,e.access_expires_at,p.state AS participant_state,
                        p.access_status AS participant_access_status
                        FROM favp_execution_profiles e
                        JOIN favp_participants p ON p.tenant_id=e.tenant_id
                          AND p.participant_id=e.participant_id""").fetchall()
            active = [dict(row) for row in rows if row["state"] == "ACTIVE"]
            invalid = []
            for row in active:
                try:
                    expiry = datetime.fromisoformat(row["access_expires_at"].replace("Z", "+00:00"))
                    if (expiry <= now or row["nda_status"] != "ACCEPTED" or
                            row["terms_status"] != "ACCEPTED" or
                            row["onboarding_status"] != "COMPLETED" or
                            row["participant_state"] != "ACTIVE_VALIDATION" or
                            row["participant_access_status"] != "ACTIVE"):
                        invalid.append(row)
                except (TypeError, ValueError):
                    invalid.append(row)
            return bool(active) and not invalid, {"active_profiles": len(active), "invalid_active_profiles": len(invalid)}
        except Exception:
            return False, {"active_profiles": 0, "invalid_active_profiles": 0}

    def _activation_audit(self) -> tuple[bool, dict[str, Any]]:
        """Require the four immutable audit events for an active participant."""
        required = {
            "FAVP_INVITATION_ACCEPTED",
            "FAVP_NDA_ACCEPTED",
            "FAVP_TERMS_ACCEPTED",
            "FAVP_PARTICIPANT_ACTIVATED",
        }
        if self.db is None:
            return False, {"required_events": sorted(required), "missing_events": sorted(required)}
        try:
            with self.db.session() as connection:
                participant_query = """SELECT e.tenant_id,e.profile_id,e.participant_id
                    FROM favp_execution_profiles e
                    JOIN favp_participants p ON p.tenant_id=e.tenant_id
                      AND p.participant_id=e.participant_id
                    WHERE e.state='ACTIVE' AND p.state='ACTIVE_VALIDATION'"""
                participant_params: tuple[Any, ...] = ()
                if self.tenant_id:
                    participant_query += " AND e.tenant_id=?"
                    participant_params = (self.tenant_id,)
                event_types: set[str] = set()
                for row in connection.execute(participant_query, participant_params).fetchall():
                    event_rows = connection.execute(
                        """SELECT DISTINCT event_type FROM audit_events
                           WHERE tenant_id=? AND (
                               resource_id=? OR resource_id=? OR resource_id IN
                               (SELECT invitation_id FROM favp_invitations
                                WHERE tenant_id=? AND participant_id=?))""",
                        (row["tenant_id"], row["participant_id"], row["profile_id"], row["tenant_id"], row["participant_id"]),
                    ).fetchall()
                    event_types.update(item["event_type"] if hasattr(item, "keys") else item[0] for item in event_rows)
            missing = sorted(required - event_types)
            return not missing, {"required_events": sorted(required), "missing_events": missing}
        except Exception:
            return False, {"required_events": sorted(required), "missing_events": sorted(required)}

    def _scenarios(self) -> tuple[bool, dict[str, Any]]:
        try:
            with self.db.session() as connection:
                rows = connection.execute(
                    "SELECT scenario_id,scenario_json,version,synthetic FROM favp_execution_scenarios ORDER BY scenario_id"
                ).fetchall()
            scenarios = []
            for row in rows:
                item = json.loads(row["scenario_json"] if hasattr(row, "keys") else row[1])
                item["scenario_id"] = row["scenario_id"] if hasattr(row, "keys") else row[0]
                item["version"] = row["version"] if hasattr(row, "keys") else row[2]
                item["synthetic"] = bool(row["synthetic"] if hasattr(row, "keys") else row[3])
                scenarios.append(item)
        except Exception:
            scenarios = []
        required = {"scenario_id", "difficulty", "synthetic", "evidence_bundle", "expected_investigation_objectives", "mitre_attack_mapping", "evaluation_criteria", "analyst_decision_checkpoints", "ai_boundary_tests", "version"}
        invalid = []
        for item in scenarios:
            bundle = item.get("evidence_bundle") if isinstance(item, dict) else None
            if not isinstance(item, dict) or not required.issubset(item) or item.get("synthetic") is not True or not isinstance(bundle, dict) or bundle.get("customer_data_included") is not False or bundle.get("raw_payload_included") is not False:
                invalid.append(item.get("scenario_id") if isinstance(item, dict) else "unknown")
        passed = len(scenarios) == len(FAVP_EXECUTION_SCENARIOS) and set(item.get("scenario_id") for item in scenarios) == set(FAVP_EXECUTION_SCENARIOS) and not invalid
        return passed, {"catalog_size": len(scenarios), "required_size": len(FAVP_EXECUTION_SCENARIOS), "invalid_scenarios": invalid}

    def _reporting(self) -> tuple[bool, dict[str, Any]]:
        if self.execution is None:
            return False, {"template_status": "unavailable", "sections": []}
        try:
            report = self.execution.final_report_template(tenant_id="launch-readiness")
            organization = self.execution.organization_summary(tenant_id="launch-readiness")
            sections = list((report.get("sections") or {}).keys())
            passed = (
                report.get("data_status") == "template_not_filled"
                and report.get("no_fabricated_values") is True
                and report.get("synthetic_only") is True
                and organization.get("synthetic_only") is True
                and organization.get("ai_boundary") == "advisory_only"
                and set(_REPORT_SECTIONS).issubset(sections)
            )
            return passed, {
                "template_status": report.get("data_status"),
                "organization_report": organization.get("report_version"),
                "sections": sections,
            }
        except Exception:
            return False, {"template_status": "unavailable", "sections": []}

    def _compose(self) -> tuple[bool, dict[str, Any]]:
        if self.compose_path is None:
            return True, {"checked": False}
        try:
            import yaml
            compose = yaml.safe_load(self.compose_path.read_text(encoding="utf-8")) or {}
            services = compose.get("services", {})
            postgres = services.get("postgres", {})
            migration = services.get("migration", {})
            app = services.get("app", {})
            networks = compose.get("networks", {})
            url_ok = all(str(services.get(name, {}).get("environment", {}).get("DATABASE_URL", "")).startswith("postgresql://") for name in ("app", "migration"))
            migration_ready = (
                migration.get("command") == ["python", "-m", "database.run_migrations"]
                and "staging_favp_evidence:/var/lib/sentinel/favp-evidence" in migration.get("volumes", [])
                and app.get("depends_on", {}).get("migration", {}).get("condition") == "service_completed_successfully"
                and migration.get("environment", {}).get("SENTINEL_DNA_FAVP_EVIDENCE_DIR") == "/var/lib/sentinel/favp-evidence"
            )
            passed = (
                "postgres" in services and postgres.get("healthcheck") and "staging_postgres_data:/var/lib/postgresql/data" in postgres.get("volumes", [])
                and "staging_internal" in networks and networks["staging_internal"].get("internal") is True and url_ok and migration_ready
            )
            return passed, {"checked": True, "postgres_service": "postgres" in services, "private_staging_network": networks.get("staging_internal", {}).get("internal") is True, "staging_initializer": migration_ready}
        except Exception:
            return False, {"checked": True}

    def check(self) -> dict[str, Any]:
        env = self.environ
        checks = [
            _check("staging_environment", env.get("SENTINEL_DNA_ENV") == "staging", "staging environment confirmed" if env.get("SENTINEL_DNA_ENV") == "staging" else "SENTINEL_DNA_ENV must be staging"),
            _check("favp_feature_flag", env.get("SENTINEL_DNA_FAVP_OPERATIONS_ENABLED") == "1", "FAVP operations explicitly enabled" if env.get("SENTINEL_DNA_FAVP_OPERATIONS_ENABLED") == "1" else "SENTINEL_DNA_FAVP_OPERATIONS_ENABLED must be 1"),
            _check("production_isolation", env.get("SENTINEL_DNA_ENV") == "staging" and env.get("SENTINEL_DNA_FAVP_PRODUCTION_ACCESS", "0") == "0", "production access is disabled" if env.get("SENTINEL_DNA_FAVP_PRODUCTION_ACCESS", "0") == "0" else "production access must remain disabled"),
            _check("synthetic_only", env.get("SENTINEL_DNA_FAVP_SYNTHETIC_ONLY") == "1", "synthetic-only mode confirmed" if env.get("SENTINEL_DNA_FAVP_SYNTHETIC_ONLY") == "1" else "SENTINEL_DNA_FAVP_SYNTHETIC_ONLY must be 1"),
            _check("config_source", env.get("SENTINEL_DNA_CONFIG_SOURCE_CLASSIFICATION") == "external_non_production", "external non-production configuration source confirmed" if env.get("SENTINEL_DNA_CONFIG_SOURCE_CLASSIFICATION") == "external_non_production" else "configuration source must be external_non_production"),
            _check("disposable_database_target", env.get("SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION") == "disposable_staging", "disposable staging database target confirmed" if env.get("SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION") == "disposable_staging" else "database target must be disposable_staging"),
        ]
        url = str(env.get("DATABASE_URL", "")).strip()
        parsed = urlparse(url) if url else None
        backend_ok = self.db is not None and getattr(self.db, "backend_name", None) == "postgresql" and parsed is not None and parsed.scheme in {"postgres", "postgresql"} and bool(parsed.netloc)
        checks.append(_check("postgres_backend", backend_ok, "authoritative disposable PostgreSQL backend is configured" if backend_ok else "DATABASE_URL must select PostgreSQL for staging"))
        try:
            healthy = bool(self.db and self.db.health_check())
        except Exception:
            healthy = False
        checks.append(_check("postgres_health", healthy, "PostgreSQL health probe passed" if healthy else "disposable PostgreSQL health probe failed"))
        schema_ok, schema_details = self._database_schema()
        checks.append(_check("favp_database_schema", schema_ok, "FAVP and audit tables are present" if schema_ok else "required FAVP or audit tables are missing", **schema_details))
        evidence_ok = bool(
            self.evidence_dir
            and self.evidence_dir.is_absolute()
            and self.evidence_dir.is_dir()
            and not self.evidence_dir.is_symlink()
            and os.access(self.evidence_dir, os.W_OK)
        )
        evidence_details: dict[str, Any] = {}
        # The staging initializer writes this marker inside the dedicated
        # named volume. SQLite fixtures retain directory-only compatibility;
        # the PostgreSQL launch gate requires the custody declaration.
        if evidence_ok and getattr(self.db, "backend_name", None) == "postgresql":
            marker = self.evidence_dir / ".favp-storage-manifest.json"
            try:
                manifest = json.loads(marker.read_text(encoding="utf-8"))
                evidence_ok = (
                    manifest.get("storage_classification") == "disposable_staging_favp_evidence"
                    and manifest.get("synthetic_only") is True
                    and manifest.get("production_access") == "0"
                    and manifest.get("schema") == "favp-evidence-storage-v1"
                )
                evidence_details = {"manifest": str(marker), "storage_classification": manifest.get("storage_classification")}
            except (OSError, UnicodeError, ValueError, TypeError):
                evidence_ok = False
                evidence_details = {"manifest": str(marker), "manifest_status": "missing_or_invalid"}
        checks.append(_check("evidence_storage", evidence_ok, "approved evidence directory is absolute, dedicated, writable, and marked for disposable staging" if evidence_ok else "FAVP evidence directory must be an absolute writable disposable-staging volume with a valid manifest", **evidence_details))
        audit_ok, audit_details = self._audit_trail()
        checks.append(_check("audit_trail", audit_ok, "audit events and append-only guards are verified" if audit_ok else "audit table, append-only guards, or audit history is unavailable", **audit_details))
        isolation_ok, isolation_details = self._tenant_isolation()
        checks.append(_check("tenant_isolation", isolation_ok, "tenant columns and existing permission boundary are verified" if isolation_ok else "tenant isolation control or required permission boundary is missing", **isolation_details))
        checks.append(_check("permissions", {"pilot:read", "pilot:manage", "validation:execute"}.issubset(PERMISSIONS), "existing FAVP permission boundary is available" if {"pilot:read", "pilot:manage", "validation:execute"}.issubset(PERMISSIONS) else "required FAVP permissions are missing"))
        onboarding_ok, onboarding_details = self._onboarding()
        checks.append(_check("participant_onboarding", onboarding_ok, "at least one operator-onboarded active participant has unexpired access" if onboarding_ok else "no valid active onboarded participant is available", **onboarding_details))
        activation_audit_ok, activation_audit_details = self._activation_audit()
        checks.append(_check("participant_activation_audit", activation_audit_ok, "required invitation, compliance, and activation audit events are present" if activation_audit_ok else "required participant activation audit events are missing", **activation_audit_details))
        scenarios_ok, scenario_details = self._scenarios()
        checks.append(_check("scenario_packages", scenarios_ok, "eight synthetic scenario packages are valid" if scenarios_ok else "scenario catalog is missing, incomplete, or not synthetic-only", **scenario_details))
        reporting_ok, report_details = self._reporting()
        checks.append(_check("report_generation", reporting_ok, "final FAVP report template generates without fabricated values" if reporting_ok else "FAVP report template is unavailable or invalid", **report_details))
        compose_ok, compose_details = self._compose()
        checks.append(_check("disposable_postgres_provisioning", compose_ok, "staging Compose PostgreSQL contract is valid" if compose_ok else "staging Compose PostgreSQL contract is missing or not private/disposable", **compose_details))
        blocked = [item for item in checks if item["status"] != "PASS"]
        return {
            "status": FAVP_LAUNCH_BLOCKED if blocked else FAVP_LAUNCH_READY,
            "dashboard": "FAVP Launch Readiness Dashboard",
            "environment": {"name": env.get("SENTINEL_DNA_ENV") or "unknown", "synthetic_only": env.get("SENTINEL_DNA_FAVP_SYNTHETIC_ONLY") == "1", "production_access": env.get("SENTINEL_DNA_FAVP_PRODUCTION_ACCESS", "0")},
            "summary": {"checks": len(checks), "passed": len(checks) - len(blocked), "blocked": len(blocked), "blocking_checks": [item["name"] for item in blocked]},
            "checks": checks,
            "launch_gate": {"ready": not blocked, "human_program_owner_authorization_required": True, "activation_performed": False},
            "operator_actions": [item["reason"] for item in blocked] if blocked else ["Human program owner may authorize the bounded staging cycle."],
            "no_fabricated_values": True,
        }


__all__ = ["FAVP_LAUNCH_BLOCKED", "FAVP_LAUNCH_READY", "FAVPStagingLaunchReadiness"]

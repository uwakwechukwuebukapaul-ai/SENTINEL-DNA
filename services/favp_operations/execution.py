"""Controlled execution workflow for the first non-production FAVP cycle."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any
from uuid import uuid4

from database.portability import append_only_statements
from .execution_scenarios import FAVP_EXECUTION_SCENARIOS, get_execution_scenario
from .readiness import FAVPExecutionReadiness


EXECUTION_STATES = ("INVITED", "APPLIED", "APPROVED", "ONBOARDED", "ACTIVE", "SUSPENDED", "COMPLETED", "REVOKED")
EXECUTION_TRANSITIONS = {
    "INVITED": {"APPLIED", "REVOKED"},
    "APPLIED": {"APPROVED", "REVOKED"},
    "APPROVED": {"ONBOARDED", "REVOKED"},
    "ONBOARDED": {"ACTIVE", "REVOKED"},
    "ACTIVE": {"SUSPENDED", "COMPLETED", "REVOKED"},
    "SUSPENDED": {"ACTIVE", "REVOKED"},
    "COMPLETED": {"REVOKED"},
    "REVOKED": set(),
}
VALIDATION_FIELDS = ("evidence_completeness", "provenance_integrity", "timestamp_consistency", "chain_of_custody", "reproducibility", "ai_explanation_quality", "uncertainty_reporting")
VALIDATION_STATUSES = {"PASS", "FAIL", "NOT_MEASURED"}
SHA256 = re.compile(r"^[0-9a-f]{64}$", re.I)


class FAVPExecutionError(ValueError):
    """Raised when a controlled execution operation cannot be authorized."""


def _text(value: Any, field: str, limit: int = 512) -> str:
    result = str(value or "").strip()
    if not result:
        raise FAVPExecutionError(f"{field}_required")
    if len(result) > limit:
        raise FAVPExecutionError(f"{field}_too_long")
    return result


def _time(value: Any, field: str) -> datetime:
    value = _text(value, field)
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise FAVPExecutionError(f"{field}_must_be_iso8601") from exc
    if parsed.tzinfo is None:
        raise FAVPExecutionError(f"{field}_must_include_utc_offset")
    return parsed.astimezone(timezone.utc)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: Any) -> Any:
    """Reject credential-shaped fields before advisory output is persisted."""
    if isinstance(value, dict):
        for key, item in value.items():
            if any(word in str(key).lower() for word in ("password", "secret", "token", "cookie", "credential", "session", "private_key")):
                raise FAVPExecutionError("sensitive_data_prohibited")
            _safe(item)
    elif isinstance(value, (list, tuple)):
        if len(value) > 50:
            raise FAVPExecutionError("collection_too_large")
        for item in value:
            _safe(item)
    elif isinstance(value, str):
        if len(value) > 4000:
            raise FAVPExecutionError("text_too_long")
        if re.search(r"(?i)\b(?:bearer\s+|password\s*[=:]|secret\s*[=:])", value):
            raise FAVPExecutionError("sensitive_data_prohibited")
    try:
        json.dumps(value, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise FAVPExecutionError("value_must_be_json") from exc
    return value


def _decode(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    item = dict(row)
    for field in ("ai_recommendation_json", "features_used_json"):
        if field in item:
            item[field.removesuffix("_json")] = json.loads(item.pop(field) or "null")
    return item


class FAVPExecutionService:
    """Manage linked execution profiles and controlled synthetic sessions."""

    def __init__(self, operations: Any, audit_service: Any, *, clock=_now) -> None:
        if operations is None or audit_service is None or not callable(getattr(audit_service, "record", None)):
            raise FAVPExecutionError("execution_dependencies_required")
        self.operations = operations
        self.repository = operations.repository
        self.db = self.repository.db
        self.audit_service = audit_service
        self.clock = clock
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        statements = (
            """CREATE TABLE IF NOT EXISTS favp_execution_profiles (
                profile_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
                participant_id TEXT NOT NULL, organization_id TEXT NOT NULL,
                state TEXT NOT NULL, nda_status TEXT NOT NULL,
                terms_status TEXT NOT NULL, onboarding_status TEXT NOT NULL,
                access_expires_at TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, revoked_at TEXT,
                UNIQUE(tenant_id, participant_id)
            )""",
            """CREATE TABLE IF NOT EXISTS favp_execution_scenarios (
                scenario_id TEXT PRIMARY KEY, scenario_json TEXT NOT NULL,
                version TEXT NOT NULL, synthetic INTEGER NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS favp_execution_sessions (
                session_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
                profile_id TEXT NOT NULL, participant_id TEXT NOT NULL,
                scenario_id TEXT NOT NULL, started_at TEXT NOT NULL,
                completed_at TEXT, status TEXT NOT NULL,
                ai_investigation_version TEXT NOT NULL,
                platform_build_version TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS favp_execution_reviews (
                review_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
                session_id TEXT NOT NULL, profile_id TEXT NOT NULL,
                analyst_decision TEXT NOT NULL, ai_recommendation_json TEXT NOT NULL,
                disagreement INTEGER NOT NULL, confidence_score INTEGER NOT NULL,
                usability_score INTEGER NOT NULL, explanation_usefulness INTEGER NOT NULL,
                uncertainty_reported INTEGER NOT NULL, features_used_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS favp_evidence_validations (
                validation_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
                session_id TEXT NOT NULL, profile_id TEXT NOT NULL,
                evidence_reference TEXT NOT NULL, provenance_reference TEXT NOT NULL,
                evidence_completeness TEXT NOT NULL, provenance_integrity TEXT NOT NULL,
                timestamp_consistency TEXT NOT NULL, chain_of_custody TEXT NOT NULL,
                reproducibility TEXT NOT NULL, ai_explanation_quality TEXT NOT NULL,
                uncertainty_reporting TEXT NOT NULL, validator_ref TEXT NOT NULL,
                validation_hash TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL
            )""",
        )
        with self.db.session() as connection:
            for statement in statements:
                connection.execute(statement)
            for table, prefix in (("favp_execution_reviews", "favp_execution_reviews_append_only"), ("favp_evidence_validations", "favp_evidence_validations_append_only")):
                for statement in append_only_statements(self.db.backend_name, table_name=table, trigger_prefix=prefix, error_message=f"{table}_are_append_only"):
                    connection.execute(statement)
            for scenario in FAVP_EXECUTION_SCENARIOS.values():
                connection.execute("INSERT INTO favp_execution_scenarios(scenario_id,scenario_json,version,synthetic) VALUES(?,?,?,1) ON CONFLICT(scenario_id) DO NOTHING", (scenario["scenario_id"], json.dumps(scenario, sort_keys=True, separators=(",", ":")), scenario["version"]))
            for index in (
                "CREATE INDEX IF NOT EXISTS idx_favp_execution_profiles_tenant ON favp_execution_profiles(tenant_id,state,updated_at)",
                "CREATE INDEX IF NOT EXISTS idx_favp_execution_sessions_tenant ON favp_execution_sessions(tenant_id,started_at)",
                "CREATE INDEX IF NOT EXISTS idx_favp_execution_reviews_tenant ON favp_execution_reviews(tenant_id,created_at)",
                "CREATE INDEX IF NOT EXISTS idx_favp_evidence_validations_tenant ON favp_evidence_validations(tenant_id,created_at)",
            ):
                connection.execute(index)

    def _profile(self, tenant_id: str, profile_id: str, connection=None) -> dict[str, Any]:
        query = "SELECT * FROM favp_execution_profiles WHERE tenant_id=? AND profile_id=?"
        if connection is None:
            with self.db.session() as owned:
                row = owned.execute(query, (tenant_id, profile_id)).fetchone()
        else:
            row = connection.execute(query, (tenant_id, profile_id)).fetchone()
        if not row:
            raise FAVPExecutionError("execution_profile_not_found")
        return dict(row)

    def profile_for_participant(self, *, tenant_id: str, participant_id: str, connection=None) -> dict[str, Any] | None:
        """Return the tenant-owned profile linked to a participant, if present."""
        query = "SELECT * FROM favp_execution_profiles WHERE tenant_id=? AND participant_id=?"
        if connection is None:
            with self.db.session() as owned:
                row = owned.execute(query, (tenant_id, participant_id)).fetchone()
        else:
            row = connection.execute(query, (tenant_id, participant_id)).fetchone()
        return dict(row) if row else None

    def _participant(self, tenant_id: str, participant_id: str, connection=None):
        item = self.operations.repository.get_participant(tenant_id, participant_id, connection=connection)
        if not item:
            raise FAVPExecutionError("participant_not_found")
        return item

    def _authorize(self, profile: dict[str, Any], actor_ref: str, manager: bool) -> None:
        if manager:
            return
        participant = self._participant(profile["tenant_id"], profile["participant_id"])
        allowed = {profile["participant_id"], participant.get("actor_identity_ref")}
        if actor_ref not in allowed:
            raise FAVPExecutionError("execution_profile_forbidden")

    def create_profile(self, *, tenant_id: str, participant_id: str, access_expires_at: str, actor_ref: str, manager: bool = True) -> dict[str, Any]:
        tenant_id = _text(tenant_id, "tenant_id")
        actor_ref = _text(actor_ref, "actor_ref")
        expiry = _time(access_expires_at, "access_expires_at")
        if expiry <= datetime.now(timezone.utc):
            raise FAVPExecutionError("access_expires_at_must_be_future")
        profile_id = f"FAVP-PRF-{uuid4().hex}"
        now = self.clock()
        with self.db.session() as connection:
            participant = self._participant(tenant_id, participant_id, connection=connection)
            existing = connection.execute("SELECT profile_id FROM favp_execution_profiles WHERE tenant_id=? AND participant_id=?", (tenant_id, participant_id)).fetchone()
            if existing:
                raise FAVPExecutionError("execution_profile_already_exists")
            connection.execute("""INSERT INTO favp_execution_profiles(
                profile_id,tenant_id,participant_id,organization_id,state,nda_status,
                terms_status,onboarding_status,access_expires_at,created_at,updated_at,revoked_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL)""", (profile_id, tenant_id, participant_id, participant["organization_id"], "INVITED", "NOT_STARTED", "NOT_STARTED", "NOT_STARTED", expiry.isoformat(), now, now,))
            self.audit_service.record("FAVP_EXECUTION_PROFILE_CREATED", details={}, connection=connection, tenant_id=tenant_id, actor_id=actor_ref, resource_type="favp_execution_profile", resource_id=profile_id, operation="profile_created", outcome="success")
        return self._profile(tenant_id, profile_id)

    def update_compliance(self, *, tenant_id: str, profile_id: str, actor_ref: str, nda_status: str | None = None, terms_status: str | None = None, onboarding_status: str | None = None, manager: bool = True) -> dict[str, Any]:
        profile = self._profile(tenant_id, profile_id)
        self._authorize(profile, actor_ref, manager)
        values = {}
        for field, value, allowed in (("nda_status", nda_status, {"NOT_STARTED", "ACCEPTED", "DECLINED"}), ("terms_status", terms_status, {"NOT_STARTED", "ACCEPTED", "DECLINED"}), ("onboarding_status", onboarding_status, {"NOT_STARTED", "IN_PROGRESS", "COMPLETED"})):
            if value is not None:
                value = _text(value, field).upper()
                if value not in allowed:
                    raise FAVPExecutionError(f"invalid_{field}")
                values[field] = value
        if not values:
            raise FAVPExecutionError("compliance_update_required")
        values["updated_at"] = self.clock()
        with self.db.session() as connection:
            self._profile(tenant_id, profile_id, connection=connection)
            assignment = ",".join(f"{key}=?" for key in values)
            connection.execute(f"UPDATE favp_execution_profiles SET {assignment} WHERE tenant_id=? AND profile_id=?", (*values.values(), tenant_id, profile_id))
            self.audit_service.record("FAVP_EXECUTION_COMPLIANCE_UPDATED", details={"fields": sorted(key for key in values if key != "updated_at")}, connection=connection, tenant_id=tenant_id, actor_id=actor_ref, resource_type="favp_execution_profile", resource_id=profile_id, operation="compliance_updated", outcome="success")
        return self._profile(tenant_id, profile_id)

    def transition_profile(self, *, tenant_id: str, profile_id: str, to_state: str, actor_ref: str, manager: bool = True) -> dict[str, Any]:
        profile = self._profile(tenant_id, profile_id)
        self._authorize(profile, actor_ref, manager)
        to_state = _text(to_state, "to_state").upper()
        if to_state not in EXECUTION_STATES or to_state not in EXECUTION_TRANSITIONS[profile["state"]]:
            raise FAVPExecutionError("invalid_execution_state_transition")
        if to_state == "ONBOARDED" and not (profile["nda_status"] == profile["terms_status"] == "ACCEPTED"):
            raise FAVPExecutionError("nda_and_terms_acceptance_required")
        if to_state == "ACTIVE" and profile["onboarding_status"] != "COMPLETED":
            raise FAVPExecutionError("onboarding_completion_required")
        now = self.clock()
        with self.db.session() as connection:
            connection.execute("UPDATE favp_execution_profiles SET state=?,updated_at=?,revoked_at=? WHERE tenant_id=? AND profile_id=?", (to_state, now, now if to_state == "REVOKED" else profile["revoked_at"], tenant_id, profile_id))
            self.audit_service.record("FAVP_EXECUTION_PROFILE_STATE_CHANGED", details={"from_state": profile["state"], "to_state": to_state}, connection=connection, tenant_id=tenant_id, actor_id=actor_ref, resource_type="favp_execution_profile", resource_id=profile_id, operation="profile_state_changed", outcome="success")
        return self._profile(tenant_id, profile_id)

    def revoke_profile(self, *, tenant_id: str, profile_id: str, actor_ref: str, manager: bool = True) -> dict[str, Any]:
        return self.transition_profile(tenant_id=tenant_id, profile_id=profile_id, to_state="REVOKED", actor_ref=actor_ref, manager=manager)

    def suspend_expired_profiles(self, *, tenant_id: str, actor_ref: str) -> int:
        """Expire access without reviving, extending, or provisioning it."""
        changed = 0
        now = datetime.now(timezone.utc)
        with self.db.session() as connection:
            rows = connection.execute("SELECT profile_id,access_expires_at FROM favp_execution_profiles WHERE tenant_id=? AND state='ACTIVE'", (tenant_id,)).fetchall()
            for row in rows:
                if _time(row["access_expires_at"], "access_expires_at") <= now:
                    connection.execute("UPDATE favp_execution_profiles SET state='SUSPENDED',updated_at=? WHERE tenant_id=? AND profile_id=?", (self.clock(), tenant_id, row["profile_id"]))
                    self.audit_service.record("FAVP_EXECUTION_ACCESS_EXPIRED", details={}, connection=connection, tenant_id=tenant_id, actor_id=actor_ref, resource_type="favp_execution_profile", resource_id=row["profile_id"], operation="access_expired", outcome="success")
                    changed += 1
        return changed

    def list_scenarios(self) -> list[dict[str, Any]]:
        return [dict(item) for item in FAVP_EXECUTION_SCENARIOS.values()]

    def start_session(self, *, tenant_id: str, profile_id: str, scenario_id: str, actor_ref: str, ai_investigation_version: str, platform_build_version: str, manager: bool = False) -> dict[str, Any]:
        profile = self._profile(tenant_id, profile_id)
        self._authorize(profile, actor_ref, manager)
        scenario = get_execution_scenario(scenario_id)
        if not scenario:
            raise FAVPExecutionError("execution_scenario_not_found")
        if profile["state"] != "ACTIVE":
            raise FAVPExecutionError("execution_profile_not_active")
        if _time(profile["access_expires_at"], "access_expires_at") <= datetime.now(timezone.utc):
            self.transition_profile(tenant_id=tenant_id, profile_id=profile_id, to_state="SUSPENDED", actor_ref=actor_ref, manager=True)
            raise FAVPExecutionError("execution_access_expired")
        ai_version = _text(ai_investigation_version, "ai_investigation_version")
        build_version = _text(platform_build_version, "platform_build_version")
        session_id = f"FAVP-SES-{uuid4().hex}"
        started = self.clock()
        with self.db.session() as connection:
            connection.execute("INSERT INTO favp_execution_sessions(session_id,tenant_id,profile_id,participant_id,scenario_id,started_at,completed_at,status,ai_investigation_version,platform_build_version) VALUES(?,?,?,?,?,?,NULL,?,?,?)", (session_id, tenant_id, profile_id, profile["participant_id"], scenario_id, started, "OPEN", ai_version, build_version))
            self.audit_service.record("FAVP_EXECUTION_SESSION_STARTED", details={"scenario_id": scenario_id}, connection=connection, tenant_id=tenant_id, actor_id=actor_ref, resource_type="favp_execution_session", resource_id=session_id, operation="session_started", outcome="success")
        return self._session(tenant_id, session_id)

    def _session(self, tenant_id: str, session_id: str, connection=None):
        query = "SELECT * FROM favp_execution_sessions WHERE tenant_id=? AND session_id=?"
        if connection is None:
            with self.db.session() as owned:
                row = owned.execute(query, (tenant_id, session_id)).fetchone()
        else:
            row = connection.execute(query, (tenant_id, session_id)).fetchone()
        if not row:
            raise FAVPExecutionError("execution_session_not_found")
        return dict(row)

    def submit_review(self, *, tenant_id: str, session_id: str, analyst_decision: str, ai_recommendation: dict[str, Any], disagreement: bool, confidence_score: int, usability_score: int, explanation_usefulness: int, uncertainty_reported: bool, features_used: list[str], actor_ref: str, manager: bool = False) -> dict[str, Any]:
        session = self._session(tenant_id, session_id)
        profile = self._profile(tenant_id, session["profile_id"])
        self._authorize(profile, actor_ref, manager)
        if session["status"] != "OPEN":
            raise FAVPExecutionError("execution_session_not_open")
        if not isinstance(ai_recommendation, dict):
            raise FAVPExecutionError("ai_recommendation_must_be_object")
        _safe(ai_recommendation)
        if ai_recommendation.get("advisory_only") is False or ai_recommendation.get("autonomous_action") is True:
            raise FAVPExecutionError("ai_must_remain_advisory")
        if not isinstance(disagreement, bool) or not isinstance(uncertainty_reported, bool):
            raise FAVPExecutionError("boolean_review_fields_required")
        scores = (confidence_score, usability_score, explanation_usefulness)
        if any(isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 5 for score in scores):
            raise FAVPExecutionError("review_scores_must_be_1_to_5")
        if not isinstance(features_used, list) or not features_used or len(features_used) > 30:
            raise FAVPExecutionError("features_used_required")
        features = [_text(item, "features_used", 256) for item in features_used]
        decision = _text(analyst_decision, "analyst_decision", 4000)
        _safe(decision)
        _safe(features)
        output = dict(ai_recommendation)
        output["advisory_only"] = True
        review_id = f"FAVP-REV-{uuid4().hex}"
        now = self.clock()
        with self.db.session() as connection:
            connection.execute("UPDATE favp_execution_sessions SET status='COMPLETED',completed_at=? WHERE tenant_id=? AND session_id=?", (now, tenant_id, session_id))
            connection.execute("INSERT INTO favp_execution_reviews(review_id,tenant_id,session_id,profile_id,analyst_decision,ai_recommendation_json,disagreement,confidence_score,usability_score,explanation_usefulness,uncertainty_reported,features_used_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (review_id, tenant_id, session_id, profile["profile_id"], decision, json.dumps(output, sort_keys=True, separators=(",", ":")), int(disagreement), confidence_score, usability_score, explanation_usefulness, int(uncertainty_reported), json.dumps(features, sort_keys=True, separators=(",", ":")), now))
            self.audit_service.record("FAVP_EXECUTION_REVIEW_RECORDED", details={"disagreement_recorded": disagreement, "analyst_decision_recorded": True}, connection=connection, tenant_id=tenant_id, actor_id=actor_ref, resource_type="favp_execution_review", resource_id=review_id, operation="review_recorded", outcome="success")
        with self.db.session() as connection:
            row = connection.execute("SELECT * FROM favp_execution_reviews WHERE tenant_id=? AND review_id=?", (tenant_id, review_id)).fetchone()
        return _decode(dict(row))

    def validate_evidence(self, *, tenant_id: str, session_id: str, evidence_reference: str, provenance_reference: str, statuses: dict[str, str], validator_ref: str, actor_ref: str, manager: bool = True) -> dict[str, Any]:
        session = self._session(tenant_id, session_id)
        profile = self._profile(tenant_id, session["profile_id"])
        self._authorize(profile, actor_ref, manager)
        if session["status"] != "COMPLETED":
            raise FAVPExecutionError("evidence_requires_completed_session")
        if not isinstance(statuses, dict) or set(statuses) != set(VALIDATION_FIELDS):
            raise FAVPExecutionError("all_evidence_validation_fields_required")
        statuses = {field: _text(statuses[field], field).upper() for field in VALIDATION_FIELDS}
        if any(value not in VALIDATION_STATUSES for value in statuses.values()):
            raise FAVPExecutionError("invalid_evidence_validation_status")
        evidence_reference = _text(evidence_reference, "evidence_reference")
        provenance_reference = _text(provenance_reference, "provenance_reference")
        validator_ref = _text(validator_ref, "validator_ref")
        payload = {"tenant_id": tenant_id, "session_id": session_id, "profile_id": profile["profile_id"], "evidence_reference": evidence_reference, "provenance_reference": provenance_reference, **statuses, "validator_ref": validator_ref}
        validation_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        validation_id = f"FAVP-EVAL-{uuid4().hex}"
        now = self.clock()
        with self.db.session() as connection:
            connection.execute("INSERT INTO favp_evidence_validations(validation_id,tenant_id,session_id,profile_id,evidence_reference,provenance_reference,evidence_completeness,provenance_integrity,timestamp_consistency,chain_of_custody,reproducibility,ai_explanation_quality,uncertainty_reporting,validator_ref,validation_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (validation_id, tenant_id, session_id, profile["profile_id"], evidence_reference, provenance_reference, *(statuses[field] for field in VALIDATION_FIELDS), validator_ref, validation_hash, now))
            self.audit_service.record("FAVP_EVIDENCE_VALIDATED", details={"validation_statuses_recorded": True}, connection=connection, tenant_id=tenant_id, actor_id=actor_ref, resource_type="favp_evidence_validation", resource_id=validation_id, operation="evidence_validated", outcome="success")
        with self.db.session() as connection:
            row = connection.execute("SELECT * FROM favp_evidence_validations WHERE tenant_id=? AND validation_id=?", (tenant_id, validation_id)).fetchone()
        return dict(row)

    def workspace(self, *, tenant_id: str, profile_id: str, actor_ref: str, manager: bool = False) -> dict[str, Any]:
        profile = self._profile(tenant_id, profile_id)
        self._authorize(profile, actor_ref, manager)
        with self.db.session() as connection:
            sessions = [dict(row) for row in connection.execute("SELECT * FROM favp_execution_sessions WHERE tenant_id=? AND profile_id=? ORDER BY started_at,session_id", (tenant_id, profile_id)).fetchall()]
            reviews = [_decode(dict(row)) for row in connection.execute("SELECT * FROM favp_execution_reviews WHERE tenant_id=? AND profile_id=? ORDER BY created_at,review_id", (tenant_id, profile_id)).fetchall()]
            validations = [dict(row) for row in connection.execute("SELECT * FROM favp_evidence_validations WHERE tenant_id=? AND profile_id=? ORDER BY created_at,validation_id", (tenant_id, profile_id)).fetchall()]
        return {"profile": profile, "sessions": sessions, "reviews": reviews, "evidence_validations": validations, "ai_boundary": "advisory_only", "synthetic_only": True}

    def progress_dashboard(self, *, tenant_id: str) -> dict[str, Any]:
        with self.db.session() as connection:
            profiles = [dict(row) for row in connection.execute("SELECT profile_id,state FROM favp_execution_profiles WHERE tenant_id=?", (tenant_id,)).fetchall()]
            sessions = [dict(row) for row in connection.execute("SELECT status FROM favp_execution_sessions WHERE tenant_id=?", (tenant_id,)).fetchall()]
            reviews = [dict(row) for row in connection.execute("SELECT disagreement,confidence_score,usability_score,explanation_usefulness FROM favp_execution_reviews WHERE tenant_id=?", (tenant_id,)).fetchall()]
            session_profiles = [dict(row) for row in connection.execute("SELECT profile_id,status FROM favp_execution_sessions WHERE tenant_id=?", (tenant_id,)).fetchall()]
            evidence = [dict(row) for row in connection.execute("SELECT * FROM favp_evidence_validations WHERE tenant_id=?", (tenant_id,)).fetchall()]
        state_counts = {state: sum(item["state"] == state for item in profiles) for state in EXECUTION_STATES}
        average = lambda field: round(sum(item[field] for item in reviews) / len(reviews), 2) if reviews else None
        return {"data_status": "measured" if profiles or sessions else "insufficient_data", "synthetic_only": True, "program": {"profiles": len(profiles), "active": state_counts["ACTIVE"], "completed": state_counts["COMPLETED"], "revoked": state_counts["REVOKED"], "state_counts": state_counts}, "usage": {"investigations_completed": sum(item["status"] == "COMPLETED" for item in session_profiles), "sessions_started": len(session_profiles), "repeated_usage_profiles": sum(sum(1 for session in session_profiles if session["profile_id"] == profile.get("profile_id")) > 1 for profile in profiles)}, "trust": {"evidence_confidence": average("confidence_score"), "analyst_trust_rating": average("usability_score"), "explanation_usefulness": average("explanation_usefulness")}, "evidence": {"validations": len(evidence), "provenance_pass": sum(item["provenance_integrity"] == "PASS" for item in evidence), "reproducibility_pass": sum(item["reproducibility"] == "PASS" for item in evidence), "audit_quality": "measured_by_audit_events" if evidence else "insufficient_data"}, "commercial": self.operations.kpis(tenant_id=tenant_id)["commercial"], "limitations": {"disagreements_recorded": sum(item["disagreement"] == 1 for item in reviews), "uncertainty_not_inferred": True}}

    def individual_report(self, *, tenant_id: str, profile_id: str, actor_ref: str, manager: bool = True) -> dict[str, Any]:
        workspace = self.workspace(tenant_id=tenant_id, profile_id=profile_id, actor_ref=actor_ref, manager=manager)
        return {"report_type": "FAVP Individual Analyst Report", "report_version": "favp-execution-report-v1", "observed_evidence": {"profile": workspace["profile"], "sessions": workspace["sessions"], "evidence_validations": workspace["evidence_validations"]}, "analyst_feedback": {"reviews": workspace["reviews"]}, "system_measurements": {"sessions": len(workspace["sessions"]), "completed_sessions": sum(item["status"] == "COMPLETED" for item in workspace["sessions"])}, "limitations": ["This report contains only recorded synthetic validation activity.", "It is not a certification or customer outcome."], "future_improvements": ["Review disagreement records with the analyst.", "Repeat validation where reproducibility is not PASS."], "synthetic_only": True, "ai_boundary": "advisory_only"}

    def organization_summary(self, *, tenant_id: str) -> dict[str, Any]:
        dashboard = self.progress_dashboard(tenant_id=tenant_id)
        return {
            "report_type": "FAVP Organization Summary Report",
            "report_version": "favp-organization-summary-v1",
            "tenant_id": tenant_id,
            "observed_evidence": {"scope": "recorded synthetic execution data only", "scenario_sessions": dashboard["usage"], "evidence_validations": dashboard["evidence"]},
            "analyst_feedback": dashboard["trust"],
            "system_measurements": dashboard["program"],
            "commercial_signals": dashboard["commercial"],
            "limitations": ["No organization outcome is inferred from missing data.", "Commercial signals are recorded feedback, not revenue or a purchase commitment."],
            "future_improvements": ["Increase scenario coverage only after the bounded catalog is reviewed.", "Repeat evidence validation for failed or not-measured criteria."],
            "synthetic_only": True,
            "ai_boundary": "advisory_only",
        }

    def final_report_template(self, *, tenant_id: str) -> dict[str, Any]:
        return {"report_type": "FAVP Final Validation Report", "report_version": "favp-final-template-v1", "tenant_id": tenant_id, "sections": {"Executive Summary": None, "Program Scope": {"duration_days": 30, "synthetic_only": True}, "Participant Summary": None, "Scenario Coverage": {"catalog_size": len(FAVP_EXECUTION_SCENARIOS)}, "Analyst Feedback Summary": None, "Evidence Quality Assessment": None, "AI Boundary Findings": {"recommendations_advisory": True, "analyst_authority": True, "autonomous_actions": False}, "Security Controls Tested": None, "Limitations": [], "Commercial Signals": None, "Next Recommendations": []}, "data_status": "template_not_filled", "no_fabricated_values": True, "synthetic_only": True, "ai_boundary": "advisory_only"}

    def readiness(self, *, evidence_dir=None, environ=None) -> dict[str, Any]:
        return FAVPExecutionReadiness(self.db, self.audit_service, evidence_dir=evidence_dir, environ=environ).check()

    def launch_readiness(self, *, tenant_id=None, evidence_dir=None, environ=None, compose_path=None) -> dict[str, Any]:
        from .launch_readiness import FAVPStagingLaunchReadiness
        return FAVPStagingLaunchReadiness(
            self.db,
            self.audit_service,
            self,
            environ=environ,
            evidence_dir=evidence_dir,
            compose_path=compose_path,
            tenant_id=tenant_id,
        ).check()

    def verify_evidence_validation(self, *, tenant_id: str, validation_id: str) -> bool:
        with self.db.session() as connection:
            row = connection.execute("SELECT * FROM favp_evidence_validations WHERE tenant_id=? AND validation_id=?", (tenant_id, validation_id)).fetchone()
        if not row:
            return False
        item = dict(row)
        payload = {"tenant_id": item["tenant_id"], "session_id": item["session_id"], "profile_id": item["profile_id"], "evidence_reference": item["evidence_reference"], "provenance_reference": item["provenance_reference"], **{field: item[field] for field in VALIDATION_FIELDS}, "validator_ref": item["validator_ref"]}
        expected = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return expected == item["validation_hash"]


__all__ = ["EXECUTION_STATES", "FAVPExecutionError", "FAVPExecutionService", "VALIDATION_FIELDS"]

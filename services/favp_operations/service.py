"""Application service for the synthetic FAVP operations platform."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import re
from typing import Any, Callable
from uuid import uuid4

from .models import (
    FAVP_PROGRAM_STATES,
    FAVP_PROGRAM_STATE_TRANSITIONS,
    FAVP_SCORES,
)
from .repository import FAVPOperationsRepository, _json


class FAVPOperationsError(ValueError):
    """Raised for invalid, unauthorized, or unsafe FAVP operations."""


_SENSITIVE_KEY_PARTS = (
    "password", "secret", "token", "cookie", "credential", "session",
    "bearer", "private_key", "api_key", "raw_payload", "raw_body",
    "access_key", "client_secret", "authorization_header",
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
_ALLOWED_INVITATION_STATUSES = {"SENT", "OPENED", "ACCEPTED", "EXPIRED", "DECLINED"}
_ALLOWED_CONTACT_CHANNELS = {"operator_handoff", "approved_email_reference", "approved_messaging_reference"}
_ALLOWED_TIERS = {"UNSPECIFIED", "FOUNDATION", "PROFESSIONAL", "ENTERPRISE"}
_ALLOWED_DOCUMENT_STATUSES = {"NOT_STARTED", "SENT", "ACCEPTED", "DECLINED", "EXPIRED"}
_ALLOWED_ONBOARDING_STATUSES = {"NOT_STARTED", "IN_PROGRESS", "COMPLETED", "BLOCKED"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _now_text(clock: Callable[[], datetime]) -> str:
    return clock().astimezone(timezone.utc).isoformat()


def _required(value: Any, field: str, maximum: int = 256) -> str:
    text = str(value or "").strip()
    if not text:
        raise FAVPOperationsError(f"{field}_required")
    if len(text) > maximum:
        raise FAVPOperationsError(f"{field}_too_long")
    return text


def _optional(value: Any, field: str, maximum: int = 512) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    return _required(value, field, maximum)


def _parse_time(value: Any, field: str) -> datetime:
    text = _required(value, field)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        result = datetime.fromisoformat(text)
    except ValueError as exc:
        raise FAVPOperationsError(f"{field}_must_be_iso8601") from exc
    if result.tzinfo is None:
        raise FAVPOperationsError(f"{field}_must_include_utc_offset")
    return result.astimezone(timezone.utc)


def _sensitive_key(key: Any) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _reject_sensitive(value: Any, *, depth: int = 0) -> None:
    """Reject credential-shaped input instead of persisting it redacted."""
    if depth > 4:
        raise FAVPOperationsError("payload_too_deep")
    if isinstance(value, dict):
        for key, item in value.items():
            if _sensitive_key(key):
                raise FAVPOperationsError("sensitive_data_prohibited")
            _reject_sensitive(item, depth=depth + 1)
    elif isinstance(value, (list, tuple)):
        if len(value) > 100:
            raise FAVPOperationsError("collection_too_large")
        for item in value:
            _reject_sensitive(item, depth=depth + 1)
    elif isinstance(value, str):
        if len(value) > 4096:
            raise FAVPOperationsError("text_too_long")
        if re.search(r"(?i)\b(?:bearer\s+|password\s*[=:]|secret\s*[=:])", value):
            raise FAVPOperationsError("sensitive_data_prohibited")


def _safe_json(value: Any, field: str) -> Any:
    _reject_sensitive(value)
    try:
        json.dumps(value, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise FAVPOperationsError(f"{field}_must_be_json") from exc
    return value


def _list_of_text(value: Any, field: str, *, maximum: int = 50) -> list[str]:
    if not isinstance(value, (list, tuple)):
        raise FAVPOperationsError(f"{field}_must_be_list")
    if not value or len(value) > maximum:
        raise FAVPOperationsError(f"{field}_must_contain_one_to_{maximum}")
    return [_required(item, field, 512) for item in value]


def _decode_record(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for field in (
        "ai_recommendation_json", "evidence_references_json",
        "provenance_references_json", "features_used_json", "limitations_json",
        "requested_integrations_json", "deployment_requirements_json",
    ):
        if field in result:
            result[field.removesuffix("_json")] = json.loads(result.pop(field) or "null")
    return result


class FAVPOperationsService:
    """Coordinate program records without provisioning access or taking action."""

    def __init__(
        self,
        repository: FAVPOperationsRepository,
        audit_service: Any,
        *,
        clock: Callable[[], datetime] = _utcnow,
        platform_build_version: str | None = None,
    ) -> None:
        if repository is None or audit_service is None or not callable(getattr(audit_service, "record", None)):
            raise FAVPOperationsError("audit_service_required")
        self.repository = repository
        self.audit_service = audit_service
        self.clock = clock
        self.platform_build_version = platform_build_version or os.getenv(
            "SENTINEL_DNA_IMAGE_REVISION_FULL", "not_recorded"
        )

    def _audit(self, connection: Any, *, tenant_id: str, actor_ref: str, resource_type: str, resource_id: str, operation: str, outcome: str = "success", details: dict[str, Any] | None = None) -> None:
        self.audit_service.record(
            f"FAVP_{operation.upper()}",
            details=details or {},
            connection=connection,
            tenant_id=tenant_id,
            actor_id=actor_ref,
            resource_type=resource_type,
            resource_id=resource_id,
            operation=operation,
            outcome=outcome,
        )

    def _organization(self, tenant_id: str, organization_id: str, *, connection: Any | None = None) -> dict[str, Any]:
        tenant_id = _required(tenant_id, "tenant_id")
        organization_id = _required(organization_id, "organization_id")
        item = self.repository.get_organization(tenant_id, organization_id, connection=connection)
        if not item:
            raise FAVPOperationsError("organization_not_found")
        return item

    def _participant(self, tenant_id: str, participant_id: str, *, connection: Any | None = None) -> dict[str, Any]:
        tenant_id = _required(tenant_id, "tenant_id")
        participant_id = _required(participant_id, "participant_id")
        item = self.repository.get_participant(tenant_id, participant_id, connection=connection)
        if not item:
            raise FAVPOperationsError("participant_not_found")
        return item

    def create_organization(self, *, tenant_id: str, organization_ref: str, display_name: str, actor_ref: str, sector: str | None = None, size_band: str | None = None) -> dict[str, Any]:
        tenant_id = _required(tenant_id, "tenant_id")
        actor_ref = _required(actor_ref, "actor_ref")
        organization_ref = _required(organization_ref, "organization_ref")
        display_name = _required(display_name, "display_name")
        sector = _optional(sector, "sector")
        size_band = _optional(size_band, "size_band")
        organization_id = f"FAVP-ORG-{uuid4().hex}"
        now = _now_text(self.clock)
        with self.repository.db.session() as connection:
            connection.execute(
                """INSERT INTO favp_organizations(
                    organization_id,tenant_id,organization_ref,display_name,
                    sector,size_band,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?)""",
                (organization_id, tenant_id, organization_ref, display_name, sector, size_band, now, now),
            )
            self._audit(connection, tenant_id=tenant_id, actor_ref=actor_ref, resource_type="favp_organization", resource_id=organization_id, operation="organization_created")
        return self._organization(tenant_id, organization_id)

    def create_participant(self, *, tenant_id: str, organization_id: str, participant_ref: str, display_name: str, actor_ref: str, actor_identity_ref: str | None = None, role_title: str | None = None, contact_reference: str | None = None) -> dict[str, Any]:
        tenant_id = _required(tenant_id, "tenant_id")
        actor_ref = _required(actor_ref, "actor_ref")
        participant_ref = _required(participant_ref, "participant_ref")
        display_name = _required(display_name, "display_name")
        actor_identity_ref = _optional(actor_identity_ref, "actor_identity_ref")
        role_title = _optional(role_title, "role_title")
        contact_reference = _optional(contact_reference, "contact_reference")
        participant_id = f"FAVP-ANALYST-{uuid4().hex}"
        now = _now_text(self.clock)
        with self.repository.db.session() as connection:
            self._organization(tenant_id, organization_id, connection=connection)
            connection.execute(
                """INSERT INTO favp_participants(
                    participant_id,tenant_id,organization_id,participant_ref,
                    display_name,actor_identity_ref,role_title,contact_reference,state,nda_status,
                    terms_status,onboarding_status,access_status,validation_phase,
                    created_at,updated_at,completed_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (participant_id, tenant_id, organization_id, participant_ref, display_name,
                 actor_identity_ref, role_title, contact_reference, "INVITED", "NOT_STARTED", "NOT_STARTED",
                 "NOT_STARTED", "NOT_GRANTED", "PROGRAM_SCOPING", now, now, None),
            )
            connection.execute(
                """INSERT INTO favp_timeline(
                    timeline_id,tenant_id,participant_id,event_type,from_state,
                    to_state,actor_ref,notes,occurred_at
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (f"FAVP-TL-{uuid4().hex}", tenant_id, participant_id, "PARTICIPANT_CREATED", None, "INVITED", actor_ref, None, now),
            )
            self._audit(connection, tenant_id=tenant_id, actor_ref=actor_ref, resource_type="favp_participant", resource_id=participant_id, operation="participant_created")
        return self._participant(tenant_id, participant_id)

    def transition_participant(self, *, tenant_id: str, participant_id: str, to_state: str, actor_ref: str, notes: str | None = None) -> dict[str, Any]:
        tenant_id = _required(tenant_id, "tenant_id")
        actor_ref = _required(actor_ref, "actor_ref")
        to_state = _required(to_state, "to_state").upper()
        if to_state not in FAVP_PROGRAM_STATES:
            raise FAVPOperationsError("invalid_program_state")
        notes = _optional(notes, "notes", 2000)
        now = _now_text(self.clock)
        with self.repository.db.session() as connection:
            participant = self._participant(tenant_id, participant_id, connection=connection)
            old_state = participant["state"]
            if to_state not in FAVP_PROGRAM_STATE_TRANSITIONS.get(old_state, set()):
                raise FAVPOperationsError("invalid_program_state_transition")
            access_status = "REVOKED" if to_state == "REVOKED" else ("ACTIVE" if to_state == "ACTIVE_VALIDATION" else participant["access_status"])
            phase = "ACTIVE_VALIDATION" if to_state == "ACTIVE_VALIDATION" else ("CLOSEOUT" if to_state in {"COMPLETED", "DESIGN_PARTNER_CANDIDATE"} else participant["validation_phase"])
            onboarding_status = "COMPLETED" if to_state in {"ACTIVE_VALIDATION", "COMPLETED", "DESIGN_PARTNER_CANDIDATE"} else participant["onboarding_status"]
            completed_at = now if to_state in {"COMPLETED", "DESIGN_PARTNER_CANDIDATE"} else participant["completed_at"]
            connection.execute(
                """UPDATE favp_participants SET state=?,access_status=?,validation_phase=?,
                   onboarding_status=?,updated_at=?,completed_at=?
                   WHERE tenant_id=? AND participant_id=?""",
                (to_state, access_status, phase, onboarding_status, now, completed_at, tenant_id, participant_id),
            )
            connection.execute(
                """INSERT INTO favp_timeline(
                    timeline_id,tenant_id,participant_id,event_type,from_state,
                    to_state,actor_ref,notes,occurred_at
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (f"FAVP-TL-{uuid4().hex}", tenant_id, participant_id, "STATE_CHANGED", old_state, to_state, actor_ref, notes, now),
            )
            self._audit(connection, tenant_id=tenant_id, actor_ref=actor_ref, resource_type="favp_participant", resource_id=participant_id, operation="participant_state_changed", details={"from_state": old_state, "to_state": to_state})
        return self._participant(tenant_id, participant_id)

    def update_participation_requirements(self, *, tenant_id: str, participant_id: str, actor_ref: str, nda_status: str | None = None, terms_status: str | None = None, onboarding_status: str | None = None) -> dict[str, Any]:
        """Record NDA/terms/onboarding status without granting access."""
        tenant_id = _required(tenant_id, "tenant_id")
        actor_ref = _required(actor_ref, "actor_ref")
        values = {}
        if nda_status is not None:
            value = _required(nda_status, "nda_status").upper()
            if value not in _ALLOWED_DOCUMENT_STATUSES:
                raise FAVPOperationsError("invalid_nda_status")
            values["nda_status"] = value
        if terms_status is not None:
            value = _required(terms_status, "terms_status").upper()
            if value not in _ALLOWED_DOCUMENT_STATUSES:
                raise FAVPOperationsError("invalid_terms_status")
            values["terms_status"] = value
        if onboarding_status is not None:
            value = _required(onboarding_status, "onboarding_status").upper()
            if value not in _ALLOWED_ONBOARDING_STATUSES:
                raise FAVPOperationsError("invalid_onboarding_status")
            values["onboarding_status"] = value
        if not values:
            raise FAVPOperationsError("participation_status_update_required")
        now = _now_text(self.clock)
        with self.repository.db.session() as connection:
            self._participant(tenant_id, participant_id, connection=connection)
            assignments = ", ".join(f"{field}=?" for field in values)
            connection.execute(
                f"UPDATE favp_participants SET {assignments},updated_at=? WHERE tenant_id=? AND participant_id=?",
                (*values.values(), now, tenant_id, participant_id),
            )
            connection.execute(
                """INSERT INTO favp_timeline(
                    timeline_id,tenant_id,participant_id,event_type,from_state,
                    to_state,actor_ref,notes,occurred_at
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (f"FAVP-TL-{uuid4().hex}", tenant_id, participant_id, "PARTICIPATION_REQUIREMENTS_UPDATED", None, None, actor_ref, _json(values), now),
            )
            self._audit(connection, tenant_id=tenant_id, actor_ref=actor_ref, resource_type="favp_participant", resource_id=participant_id, operation="participation_requirements_updated", details={"fields": sorted(values)} )
        return self._participant(tenant_id, participant_id)

    def record_invitation(self, *, tenant_id: str, participant_id: str, invitation_ref: str, channel: str, status: str, actor_ref: str, sent_at: str | None = None, response_at: str | None = None) -> dict[str, Any]:
        tenant_id = _required(tenant_id, "tenant_id")
        actor_ref = _required(actor_ref, "actor_ref")
        invitation_ref = _required(invitation_ref, "invitation_ref")
        channel = _required(channel, "channel")
        if channel not in _ALLOWED_CONTACT_CHANNELS:
            raise FAVPOperationsError("invalid_invitation_channel")
        status = _required(status, "status").upper()
        if status not in _ALLOWED_INVITATION_STATUSES:
            raise FAVPOperationsError("invalid_invitation_status")
        sent = _parse_time(sent_at, "sent_at") if sent_at else self.clock().astimezone(timezone.utc)
        response = _parse_time(response_at, "response_at") if response_at else None
        invitation_id = f"FAVP-INV-{uuid4().hex}"
        now = _now_text(self.clock)
        with self.repository.db.session() as connection:
            self._participant(tenant_id, participant_id, connection=connection)
            connection.execute(
                """INSERT INTO favp_invitations(
                    invitation_id,tenant_id,participant_id,invitation_ref,channel,
                    status,sent_at,response_at,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (invitation_id, tenant_id, participant_id, invitation_ref, channel, status, sent.isoformat(), response.isoformat() if response else None, now),
            )
            self._audit(
                connection,
                tenant_id=tenant_id,
                actor_ref=actor_ref,
                resource_type="favp_invitation",
                resource_id=invitation_id,
                operation="invitation_accepted" if status == "ACCEPTED" else "invitation_recorded",
                details={"status": status},
            )
        return {"invitation_id": invitation_id, "tenant_id": tenant_id, "participant_id": participant_id, "invitation_ref": invitation_ref, "channel": channel, "status": status, "sent_at": sent.isoformat(), "response_at": response.isoformat() if response else None, "created_at": now}

    def list_scenarios(self) -> list[dict[str, Any]]:
        return [item for item in self.repository.all_scenarios() if item]

    def assign_scenario(self, *, tenant_id: str, participant_id: str, scenario_id: str, actor_ref: str) -> dict[str, Any]:
        tenant_id = _required(tenant_id, "tenant_id")
        actor_ref = _required(actor_ref, "actor_ref")
        scenario_id = _required(scenario_id, "scenario_id")
        assignment_id = f"FAVP-ASG-{uuid4().hex}"
        now = _now_text(self.clock)
        with self.repository.db.session() as connection:
            participant = self._participant(tenant_id, participant_id, connection=connection)
            if participant["state"] != "ACTIVE_VALIDATION":
                raise FAVPOperationsError("participant_not_active_validation")
            scenario = self.repository.scenario(scenario_id)
            if not scenario:
                raise FAVPOperationsError("scenario_not_found")
            existing = self.repository.get_assignment(tenant_id, participant_id, scenario_id, connection=connection)
            if existing:
                return existing
            connection.execute(
                """INSERT INTO favp_assignments(
                    assignment_id,tenant_id,participant_id,scenario_id,assigned_by,
                    assigned_at,status
                ) VALUES(?,?,?,?,?,?,?)""",
                (assignment_id, tenant_id, participant_id, scenario_id, actor_ref, now, "ASSIGNED"),
            )
            self._audit(connection, tenant_id=tenant_id, actor_ref=actor_ref, resource_type="favp_assignment", resource_id=assignment_id, operation="scenario_assigned", details={"scenario_id": scenario_id})
        return {"assignment_id": assignment_id, "tenant_id": tenant_id, "participant_id": participant_id, "scenario_id": scenario_id, "assigned_by": actor_ref, "assigned_at": now, "status": "ASSIGNED"}

    def record_result(self, *, tenant_id: str, participant_id: str, scenario_id: str, started_at: str, completed_at: str, analyst_decision: str, ai_recommendation: dict[str, Any], evidence_references: list[dict[str, Any]], provenance_references: list[str], features_used: list[str], limitations: list[str], ai_investigation_version: str, platform_build_version: str | None, actor_ref: str) -> dict[str, Any]:
        tenant_id = _required(tenant_id, "tenant_id")
        actor_ref = _required(actor_ref, "actor_ref")
        scenario_id = _required(scenario_id, "scenario_id")
        analyst_decision = _required(analyst_decision, "analyst_decision", 2000)
        ai_version = _required(ai_investigation_version, "ai_investigation_version")
        build_version = _required(platform_build_version or self.platform_build_version, "platform_build_version")
        _reject_sensitive(ai_recommendation)
        if not isinstance(ai_recommendation, dict):
            raise FAVPOperationsError("ai_recommendation_must_be_object")
        if ai_recommendation.get("advisory_only") is False or ai_recommendation.get("autonomous_action") is True:
            raise FAVPOperationsError("ai_must_remain_advisory")
        ai_output = dict(ai_recommendation)
        ai_output["advisory_only"] = True
        evidence = self._normalize_evidence(evidence_references)
        provenance = _list_of_text(provenance_references, "provenance_references")
        features = _list_of_text(features_used, "features_used", maximum=30)
        if not isinstance(limitations, (list, tuple)) or len(limitations) > 50:
            raise FAVPOperationsError("limitations_must_be_list")
        limitations_list = [_required(item, "limitations", 1000) for item in limitations]
        started = _parse_time(started_at, "started_at")
        completed = _parse_time(completed_at, "completed_at")
        duration = (completed - started).total_seconds()
        if duration < 0:
            raise FAVPOperationsError("completed_at_must_follow_started_at")
        result_id = f"FAVP-RES-{uuid4().hex}"
        now = _now_text(self.clock)
        with self.repository.db.session() as connection:
            participant = self._participant(tenant_id, participant_id, connection=connection)
            if participant["state"] != "ACTIVE_VALIDATION" or participant["access_status"] != "ACTIVE":
                raise FAVPOperationsError("participant_access_not_active")
            assignment = self.repository.get_assignment(tenant_id, participant_id, scenario_id, connection=connection)
            if not assignment or assignment["status"] != "ASSIGNED":
                raise FAVPOperationsError("scenario_not_assigned")
            connection.execute(
                """INSERT INTO favp_results(
                    result_id,tenant_id,participant_id,scenario_id,started_at,completed_at,
                    duration_seconds,analyst_decision,ai_recommendation_json,
                    evidence_references_json,provenance_references_json,features_used_json,
                    limitations_json,ai_investigation_version,platform_build_version,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (result_id, tenant_id, participant_id, scenario_id, started.isoformat(), completed.isoformat(), duration, analyst_decision, _json(ai_output), _json(evidence), _json(provenance), _json(features), _json(limitations_list), ai_version, build_version, now),
            )
            connection.execute("UPDATE favp_assignments SET status='COMPLETED' WHERE tenant_id=? AND participant_id=? AND scenario_id=?", (tenant_id, participant_id, scenario_id))
            self._append_evidence(connection, tenant_id=tenant_id, participant_id=participant_id, result_id=result_id, evidence=evidence, provenance=provenance, ai_version=ai_version, build_version=build_version, now=now)
            self._audit(connection, tenant_id=tenant_id, actor_ref=actor_ref, resource_type="favp_result", resource_id=result_id, operation="scenario_result_recorded", details={"scenario_id": scenario_id, "analyst_decision_recorded": True, "ai_boundary": "advisory_only"})
        return _decode_record(self.repository.get_result(tenant_id, result_id))

    @staticmethod
    def _normalize_evidence(value: Any) -> list[dict[str, str]]:
        if not isinstance(value, (list, tuple)) or not value or len(value) > 50:
            raise FAVPOperationsError("evidence_references_must_contain_one_to_50")
        normalized = []
        for item in value:
            if not isinstance(item, dict):
                raise FAVPOperationsError("evidence_reference_must_be_object")
            _reject_sensitive(item)
            reference_id = _required(item.get("reference_id"), "evidence_reference_id", 512)
            digest = _required(item.get("sha256"), "evidence_sha256", 64).lower()
            if not _SHA256.fullmatch(digest):
                raise FAVPOperationsError("evidence_sha256_invalid")
            normalized.append({"reference_id": reference_id, "sha256": digest})
        return normalized

    @staticmethod
    def _append_evidence(connection: Any, *, tenant_id: str, participant_id: str, result_id: str, evidence: list[dict[str, str]], provenance: list[str], ai_version: str, build_version: str, now: str) -> None:
        # One provenance record is required for each evidence reference.  If
        # more provenance references are supplied, the first one is paired
        # deterministically and the remainder remain in the result record.
        previous_sequence = None
        previous_hash = None
        try:
            row = connection.execute("SELECT sequence_number,record_hash FROM favp_evidence_records WHERE tenant_id=? ORDER BY sequence_number DESC LIMIT 1", (tenant_id,)).fetchone()
            if row:
                previous_sequence = int(row["sequence_number"] if hasattr(row, "keys") else row[0])
                previous_hash = row["record_hash"] if hasattr(row, "keys") else row[1]
        except Exception as exc:
            raise FAVPOperationsError("evidence_chain_unavailable") from exc
        for offset, item in enumerate(evidence, start=1):
            sequence = (previous_sequence or 0) + offset
            provenance_reference = provenance[min(offset - 1, len(provenance) - 1)]
            payload = {
                "tenant_id": tenant_id,
                "participant_id": participant_id,
                "result_id": result_id,
                "evidence_reference": item["reference_id"],
                "provenance_reference": provenance_reference,
                "evidence_sha256": item["sha256"],
                "ai_investigation_version": ai_version,
                "platform_build_version": build_version,
                "sequence_number": sequence,
                "previous_record_hash": previous_hash,
            }
            record_hash = hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()
            evidence_id = f"FAVP-EVD-{uuid4().hex}"
            connection.execute(
                """INSERT INTO favp_evidence_records(
                    evidence_record_id,tenant_id,participant_id,result_id,evidence_reference,
                    provenance_reference,evidence_sha256,ai_investigation_version,
                    platform_build_version,sequence_number,previous_record_hash,record_hash,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (evidence_id, tenant_id, participant_id, result_id, item["reference_id"], provenance_reference, item["sha256"], ai_version, build_version, sequence, previous_hash, record_hash, now),
            )
            previous_hash = record_hash

    def record_feedback(self, *, tenant_id: str, participant_id: str, scenario_id: str, result_id: str, scores: dict[str, Any], would_pay: bool | None, requested_tier: str | None, requested_integrations: list[str], deployment_requirements: list[str], incorrect_reasoning: str | None, limitations: str | None, comments: str | None, actor_ref: str) -> dict[str, Any]:
        tenant_id = _required(tenant_id, "tenant_id")
        actor_ref = _required(actor_ref, "actor_ref")
        scenario_id = _required(scenario_id, "scenario_id")
        result_id = _required(result_id, "result_id")
        if not isinstance(scores, dict) or set(scores) != set(FAVP_SCORES):
            raise FAVPOperationsError("all_feedback_scores_required")
        normalized_scores = {}
        for field in FAVP_SCORES:
            value = scores[field]
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
                raise FAVPOperationsError(f"{field}_must_be_1_to_5")
            normalized_scores[field] = value
        if would_pay is not None and not isinstance(would_pay, bool):
            raise FAVPOperationsError("would_pay_must_be_boolean")
        tier = (str(requested_tier or "UNSPECIFIED").strip().upper())
        if tier not in _ALLOWED_TIERS:
            raise FAVPOperationsError("invalid_requested_tier")
        integrations = _list_of_text(requested_integrations or ["NONE_REPORTED"], "requested_integrations", maximum=30)
        deployments = _list_of_text(deployment_requirements or ["NONE_REPORTED"], "deployment_requirements", maximum=30)
        incorrect = _optional(incorrect_reasoning, "incorrect_reasoning", 4000)
        limitations_text = _optional(limitations, "limitations", 4000)
        comments_text = _optional(comments, "comments", 4000)
        _reject_sensitive({"scores": normalized_scores, "incorrect_reasoning": incorrect, "limitations": limitations_text, "comments": comments_text})
        feedback_id = f"FAVP-FBK-{uuid4().hex}"
        now = _now_text(self.clock)
        with self.repository.db.session() as connection:
            participant = self._participant(tenant_id, participant_id, connection=connection)
            if participant["state"] not in {"ACTIVE_VALIDATION", "COMPLETED", "DESIGN_PARTNER_CANDIDATE"}:
                raise FAVPOperationsError("participant_not_in_feedback_phase")
            result = connection.execute("SELECT result_id FROM favp_results WHERE tenant_id=? AND result_id=? AND participant_id=? AND scenario_id=?", (tenant_id, result_id, participant_id, scenario_id)).fetchone()
            if not result:
                raise FAVPOperationsError("result_not_found")
            connection.execute(
                """INSERT INTO favp_feedback(
                    feedback_id,tenant_id,participant_id,scenario_id,result_id,
                    trust_evidence,reasoning_understanding,confidence_rating,
                    provenance_clarity,timeline_usefulness,ioc_enrichment_usefulness,
                    evidence_quality,would_pay,requested_tier,requested_integrations_json,
                    deployment_requirements_json,incorrect_reasoning,limitations,comments,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (feedback_id, tenant_id, participant_id, scenario_id, result_id,
                 *(normalized_scores[field] for field in FAVP_SCORES),
                 None if would_pay is None else int(would_pay), tier, _json(integrations), _json(deployments), incorrect, limitations_text, comments_text, now),
            )
            self._audit(connection, tenant_id=tenant_id, actor_ref=actor_ref, resource_type="favp_feedback", resource_id=feedback_id, operation="feedback_recorded", details={"scenario_id": scenario_id, "scores_recorded": True})
        item = next(item for item in self.repository.list_feedback(tenant_id, participant_id) if item["feedback_id"] == feedback_id)
        return _decode_record(item)

    def workspace(self, *, tenant_id: str, participant_id: str, actor_participant_id: str | None = None, actor_identity_ref: str | None = None) -> dict[str, Any]:
        participant = self._participant(tenant_id, participant_id)
        identity = actor_identity_ref if actor_identity_ref is not None else actor_participant_id
        if identity is not None and str(identity) not in {str(participant_id), str(participant.get("actor_identity_ref"))}:
            raise FAVPOperationsError("participant_workspace_forbidden")
        assignments = self.repository.list_assignments(tenant_id, participant_id)
        scenarios = []
        for assignment in assignments:
            scenario = self.repository.scenario(assignment["scenario_id"])
            if scenario:
                scenarios.append({"assignment": assignment, "scenario": scenario})
        return {
            "participant": participant,
            "scenarios": scenarios,
            "results": [_decode_record(item) for item in self.repository.list_results(tenant_id, participant_id)],
            "feedback": [_decode_record(item) for item in self.repository.list_feedback(tenant_id, participant_id)],
            "evidence": self.repository.list_evidence(tenant_id),
            "timeline": self.repository.list_timeline(tenant_id, participant_id),
            "ai_boundary": "advisory_only",
            "synthetic_only": True,
        }

    def kpis(self, *, tenant_id: str) -> dict[str, Any]:
        participants = self.repository.list_participants(tenant_id)
        results = self.repository.list_results(tenant_id)
        feedback = self.repository.list_feedback(tenant_id)
        state_count = {state: sum(item["state"] == state for item in participants) for state in FAVP_PROGRAM_STATES}
        def average(fields: tuple[str, ...]) -> float | None:
            values = [sum(item[field] for field in fields) / len(fields) for item in feedback]
            return round(sum(values) / len(values), 2) if values else None
        requested_features: list[str] = []
        tiers: dict[str, int] = {}
        pay_signals = 0
        for item in feedback:
            requested_features.extend(json.loads(item["requested_integrations_json"] or "[]"))
            tier = item["requested_tier"]
            tiers[tier] = tiers.get(tier, 0) + 1
            if item["would_pay"] == 1:
                pay_signals += 1
        return {
            "data_status": "measured" if participants or results or feedback else "insufficient_data",
            "synthetic_only": True,
            "program": {
                "applicants": state_count["APPLIED"] + state_count["SCREENING"] + state_count["ACCEPTED"] + state_count["ONBOARDING"] + state_count["ACTIVE_VALIDATION"] + state_count["COMPLETED"] + state_count["DESIGN_PARTNER_CANDIDATE"],
                "accepted_analysts": state_count["ACCEPTED"] + state_count["ONBOARDING"] + state_count["ACTIVE_VALIDATION"] + state_count["COMPLETED"] + state_count["DESIGN_PARTNER_CANDIDATE"],
                "active_participants": state_count["ACTIVE_VALIDATION"],
                "completed_validations": state_count["COMPLETED"] + state_count["DESIGN_PARTNER_CANDIDATE"],
                "state_counts": state_count,
            },
            "product": {
                "investigations_completed": len(results),
                "analyst_satisfaction": average(("confidence_rating", "evidence_quality")),
                "evidence_usefulness_score": average(("provenance_clarity", "timeline_usefulness", "ioc_enrichment_usefulness", "evidence_quality")),
                "trust_score": average(("trust_evidence", "reasoning_understanding", "confidence_rating")),
                "false_positive_feedback": sum(item["scenario_id"] == "FAVP-SCN-010" for item in feedback),
                "ai_limitation_findings": sum(bool(item["limitations"] or item["incorrect_reasoning"]) for item in feedback),
                "feedback_count": len(feedback),
            },
            "commercial": {
                "design_partner_candidates": state_count["DESIGN_PARTNER_CANDIDATE"],
                "pilot_interest_signals": pay_signals,
                "requested_features": sorted(set(requested_features)),
                "pricing_feedback": tiers,
            },
        }

    def report(self, *, tenant_id: str, generated_by: str) -> dict[str, Any]:
        generated_by = _required(generated_by, "generated_by")
        tenant_id = _required(tenant_id, "tenant_id")
        participants = self.repository.list_participants(tenant_id)
        results = self.repository.list_results(tenant_id)
        scenario_ids = {item["scenario_id"] for item in results}
        report = {
            "report_type": "FAVP Validation Report",
            "report_version": "favp-report-v1",
            "generated_at": _now_text(self.clock),
            "generated_by": generated_by,
            "tenant_id": tenant_id,
            "synthetic_only": True,
            "executive_summary": {"status": "measured" if participants or results else "insufficient_data", "message": "This report contains only recorded FAVP operations data; it does not infer customer outcomes."},
            "program_scope": {"duration_days": 30, "scope": "Founding Analyst Validation Program", "data_boundary": "synthetic_or_sanitized_only"},
            "participant_summary": self.kpis(tenant_id=tenant_id)["program"],
            "scenario_coverage": {"catalog_size": len(self.list_scenarios()), "scenarios_with_results": sorted(scenario_ids), "investigations_completed": len(results)},
            "analyst_feedback_summary": self.kpis(tenant_id=tenant_id)["product"],
            "evidence_quality_assessment": {"status": "measured" if results else "insufficient_data", "provenance_records": len(self.repository.list_evidence(tenant_id)), "raw_evidence_stored": False},
            "ai_boundary_findings": {"recommendations_are_advisory": True, "analyst_decision_is_separate": True, "autonomous_security_actions": False},
            "security_controls_tested": {"tenant_isolation": "enforced_in_repository_queries", "audit_logging": "required_for_mutations", "access_revocation": "enforced_by_participant_state", "evidence_provenance": "hash_chained_references", "credentials": "prohibited", "production_access": "not_available"},
            "limitations": ["No customer-sensitive data is accepted or stored.", "No result, satisfaction, revenue, certification, or payment outcome is inferred without a recorded observation.", "Operational deployment and human release approval remain outside this module."],
            "commercial_signals": self.kpis(tenant_id=tenant_id)["commercial"],
            "next_recommendations": ["Review each analyst decision against the recorded AI recommendation.", "Investigate every limitation finding before design-partner conversion.", "Require human program-owner approval before any state is advanced to design-partner candidate."],
        }
        # Report generation is read-only with respect to FAVP data.  The
        # caller may persist/export this object through a separately governed
        # process; this service does not create a certification artifact.
        return report


__all__ = ["FAVPOperationsError", "FAVPOperationsService"]

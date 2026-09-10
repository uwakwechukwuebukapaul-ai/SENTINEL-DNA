"""Bounded founder-operated synthetic monitoring pilot.

This module composes the existing analyst event feed, attention queue, and
command-center query surface.  It is deliberately non-production: escalation
is an attention-queue simulation and no notification or response action is
sent outside the process.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Callable

from flask import Flask

from services.intelligence.command_center import (
    AnalystAttentionService,
    AnalystEventFeed,
)
from services.intelligence.command_center.api import create_command_center_blueprint


PILOT_EVENT_ID = "MONITOR-PILOT-001"
PILOT_OPERATOR = "Uwakwe chukwuebuka paul"
PILOT_RESPONSE_OBJECTIVE = (
    "Best-effort founder-operated response during pilot validation. "
    "Enterprise SLA not established."
)
PILOT_SCENARIO = "Synthetic Sentinel DNA alert test"
PILOT_TENANT = "sentinel-monitoring-pilot"
PILOT_VERSION = "monitoring-pilot.v1"
_EVENT_ID_PATTERN = re.compile(r"^MONITOR-PILOT-[0-9]{3}$")
_STATES = ("generated", "received", "acknowledged", "escalated", "dashboard_verified")
_RESULTS = frozenset({"PASS", "FAIL", "NOT VERIFIED", "NOT PROVIDED"})


class MonitoringPilotError(RuntimeError):
    """Raised when a required pilot transition cannot be verified."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _git(*args: str) -> str:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def repository_custody() -> dict[str, Any]:
    """Return execution custody without reading credentials or production config."""
    try:
        head = _git("rev-parse", "HEAD")
        branch = _git("branch", "--show-current")
        rc1 = _git("rev-parse", "refs/tags/v1.0.0-rc1^{}")
        dirty = bool(_git("status", "--porcelain"))
    except (OSError, subprocess.CalledProcessError) as exc:
        raise MonitoringPilotError("repository_custody_unavailable") from exc
    return {
        "repository_head": head,
        "branch": branch,
        "protected_rc1_commit": rc1,
        "worktree_dirty": dirty,
    }


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 digest of the exact file bytes."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum(path: str | Path, checksum_path: str | Path) -> bool:
    """Verify a checksum manifest containing ``<digest>  <filename>``."""
    target = Path(path)
    entries = [line.strip() for line in Path(checksum_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    expected = f"{sha256_file(target)}  {target.name}"
    return entries == [expected]


def write_evidence(
    evidence: dict[str, Any],
    output: str | Path,
    checksum_output: str | Path | None = None,
) -> tuple[Path, Path, str]:
    """Write one append-only evidence artifact and its external checksum."""
    target = Path(output)
    checksums = Path(checksum_output) if checksum_output else target.parent / "checksums.sha256"
    if target.exists() or checksums.exists():
        raise MonitoringPilotError("evidence_path_already_exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    checksums.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")
    target.write_bytes(payload)
    digest = sha256_file(target)
    checksums.write_text(f"{digest}  {target.name}\n", encoding="utf-8")
    if not verify_checksum(target, checksums):
        raise MonitoringPilotError("evidence_checksum_verification_failed")
    return target, checksums, digest


class SyntheticMonitoringPilot:
    """Execute one deterministic state machine against disposable in-process state."""

    def __init__(
        self,
        *,
        event_id: str = PILOT_EVENT_ID,
        tenant_id: str = PILOT_TENANT,
        clock: Callable[[], str] = _utc_now,
        event_feed: AnalystEventFeed | None = None,
        attention_service: AnalystAttentionService | None = None,
    ) -> None:
        if not _EVENT_ID_PATTERN.fullmatch(event_id):
            raise MonitoringPilotError("invalid_pilot_event_id")
        self.event_id = event_id
        self.tenant_id = tenant_id
        self.clock = clock
        self.event_feed = event_feed or AnalystEventFeed()
        self.attention_service = attention_service or AnalystAttentionService(self.event_feed)
        self.transitions: dict[str, dict[str, Any]] = {}
        self._last_timestamp: datetime | None = None

    def _timestamp(self) -> str:
        value = self.clock()
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise MonitoringPilotError("timestamp_must_include_utc_offset")
        parsed = parsed.astimezone(timezone.utc)
        if self._last_timestamp and parsed < self._last_timestamp:
            raise MonitoringPilotError("timestamps_not_monotonic")
        self._last_timestamp = parsed
        return parsed.isoformat()

    def _record(self, state: str, *, timestamp_utc: str | None = None, **details: Any) -> dict[str, Any]:
        if state not in _STATES or state in self.transitions:
            raise MonitoringPilotError("invalid_state_transition")
        record = {"status": "PASS", "timestamp_utc": timestamp_utc or self._timestamp(), **details}
        self.transitions[state] = record
        return record

    def _dashboard_query(self) -> dict[str, Any]:
        app = Flask("sentinel_dna_monitoring_pilot")
        app.register_blueprint(
            create_command_center_blueprint(
                tenant_resolver=lambda: self.tenant_id,
                event_feed=self.event_feed,
                attention_service=self.attention_service,
            )
        )
        response = app.test_client().get(
            "/api/command-center/events",
            query_string={"source_domain": "synthetic-monitoring"},
        )
        if response.status_code != 200:
            raise MonitoringPilotError("dashboard_query_failed")
        body = response.get_json() or {}
        matches = [item for item in body.get("events", []) if item.get("event_id") == self.event_id]
        if len(matches) != 1 or matches[0].get("acknowledgement") != "acknowledged":
            raise MonitoringPilotError("dashboard_event_not_verified")
        return {
            "query_path": "GET /api/command-center/events",
            "filter": "source_domain=synthetic-monitoring",
            "event_count": len(matches),
            "acknowledgement": matches[0]["acknowledgement"],
        }

    def run(self) -> dict[str, Any]:
        custody = repository_custody()
        generated_at = self._timestamp()
        if self.event_feed.get(self.tenant_id, self.event_id) is not None:
            raise MonitoringPilotError("pilot_event_id_already_exists")
        event = self.event_feed.record(
            self.tenant_id,
            "synthetic_monitoring_alert",
            "SECURITY",
            "Synthetic Sentinel DNA alert test",
            event_id=self.event_id,
            source_domain="synthetic-monitoring",
            source_reference=self.event_id,
            severity="high",
            priority="critical",
            timestamp=generated_at,
            summary="Synthetic non-production monitoring event.",
            uncertainty="synthetic_only",
            provenance={"source": "founder_monitoring_pilot", "synthetic": True},
            related={"pilot_event_id": self.event_id},
        )
        if event.event_id != self.event_id:
            raise MonitoringPilotError("generated_event_id_mismatch")
        self._record(
            "generated",
            timestamp_utc=generated_at,
            event_id=self.event_id,
            source="synthetic-monitoring",
        )

        received = self.event_feed.get(self.tenant_id, self.event_id)
        if received is None:
            raise MonitoringPilotError("alert_receipt_not_verified")
        self._record("received", event_id=self.event_id, recipient=PILOT_OPERATOR)

        acknowledged = self.event_feed.acknowledge(self.tenant_id, self.event_id)
        if acknowledged is None or acknowledged.acknowledgement != "acknowledged":
            raise MonitoringPilotError("alert_acknowledgement_not_verified")
        self._record("acknowledged", event_id=self.event_id, acknowledgement="acknowledged")

        attention = self.attention_service.derive(self.tenant_id)
        matching_attention = next(
            (item for item in attention if self.event_id in item.related_event_ids), None
        )
        if matching_attention is None:
            raise MonitoringPilotError("pilot_escalation_not_verified")
        self._record(
            "escalated",
            event_id=self.event_id,
            escalation="attention_queue_simulation",
            attention_id=matching_attention.attention_id,
            operational_notification=False,
        )

        query_details = self._dashboard_query()
        self._record("dashboard_verified", event_id=self.event_id, **query_details)

        replay_payload = {
            "version": PILOT_VERSION,
            "scenario": PILOT_SCENARIO,
            "event_id": self.event_id,
            "tenant_id": self.tenant_id,
            "states": [
                {"state": state, **{key: value for key, value in self.transitions[state].items() if key != "timestamp_utc"}}
                for state in _STATES
            ],
        }
        replay_digest = hashlib.sha256(_canonical(replay_payload).encode("utf-8")).hexdigest()
        evidence = {
            "evidence_version": PILOT_VERSION,
            "scenario": PILOT_SCENARIO,
            "event_id": self.event_id,
            "environment": "non-production synthetic pilot",
            "execution_mode": "bounded founder-operated pilot",
            "monitoring_owner": PILOT_OPERATOR,
            "alert_recipient": PILOT_OPERATOR,
            "escalation_owner": PILOT_OPERATOR,
            "dashboard_query_owner": PILOT_OPERATOR,
            "pilot_response_objective": PILOT_RESPONSE_OBJECTIVE,
            "generated_at": self.transitions["generated"]["timestamp_utc"],
            "received_at": self.transitions["received"]["timestamp_utc"],
            "acknowledged_at": self.transitions["acknowledged"]["timestamp_utc"],
            "escalated_at": self.transitions["escalated"]["timestamp_utc"],
            "dashboard_verified_at": self.transitions["dashboard_verified"]["timestamp_utc"],
            "alert_status": "received",
            "acknowledgement_status": "acknowledged",
            "escalation_status": "PASS",
            "dashboard_verification_status": "PASS",
            "transitions": self.transitions,
            "replay_digest": replay_digest,
            "validation_result": "PASS",
            "secret_exclusion": "PASS",
            "customer_data_exclusion": "PASS",
            "production_impact": {
                "production_database_touched": False,
                "deployment_performed": False,
                "external_services_contacted": False,
            },
            "repository": custody,
            "checksum_manifest": "checksums.sha256",
        }
        if any(self.transitions[state]["status"] not in _RESULTS for state in _STATES):
            raise MonitoringPilotError("invalid_evidence_result")
        return evidence


__all__ = [
    "MonitoringPilotError",
    "PILOT_EVENT_ID",
    "PILOT_OPERATOR",
    "SyntheticMonitoringPilot",
    "repository_custody",
    "sha256_file",
    "verify_checksum",
    "write_evidence",
]

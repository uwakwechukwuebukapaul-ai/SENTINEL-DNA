from datetime import datetime, timezone
import json

import pytest

from services.monitoring.pilot import (
    MonitoringPilotError,
    SyntheticMonitoringPilot,
    verify_checksum,
    write_evidence,
)


def timestamps():
    values = iter(
        f"2026-08-26T12:00:0{index}+00:00" for index in range(5)
    )
    return lambda: next(values)


def test_monitoring_pilot_records_complete_ordered_workflow(tmp_path):
    pilot = SyntheticMonitoringPilot(clock=timestamps())
    evidence = pilot.run()

    assert evidence["event_id"] == "MONITOR-PILOT-001"
    assert evidence["validation_result"] == "PASS"
    assert evidence["environment"] == "non-production synthetic pilot"
    assert all(evidence[f"{state}_status"] == "PASS" for state in ("escalation", "dashboard_verification"))
    ordered = [evidence[f"{state}_at"] for state in ("generated", "received", "acknowledged", "escalated", "dashboard_verified")]
    parsed = [datetime.fromisoformat(value) for value in ordered]
    assert all(item.tzinfo == timezone.utc for item in parsed)
    assert parsed == sorted(parsed)
    assert pilot.event_feed.get("sentinel-monitoring-pilot", "MONITOR-PILOT-001").acknowledgement == "acknowledged"


def test_monitoring_pilot_rejects_invalid_or_reused_event_ids():
    with pytest.raises(MonitoringPilotError, match="invalid_pilot_event_id"):
        SyntheticMonitoringPilot(event_id="not-a-monitor-event")

    pilot = SyntheticMonitoringPilot(clock=timestamps())
    pilot.run()
    with pytest.raises(MonitoringPilotError, match="pilot_event_id_already_exists"):
        SyntheticMonitoringPilot(event_feed=pilot.event_feed, clock=timestamps()).run()


def test_monitoring_pilot_fails_closed_on_non_utc_or_non_monotonic_clock():
    with pytest.raises(MonitoringPilotError, match="timestamp_must_include_utc_offset"):
        SyntheticMonitoringPilot(clock=lambda: "2026-08-26T12:00:00").run()

    values = iter(("2026-08-26T12:00:01+00:00", "2026-08-26T12:00:00+00:00"))
    with pytest.raises(MonitoringPilotError, match="timestamps_not_monotonic"):
        SyntheticMonitoringPilot(clock=lambda: next(values)).run()


def test_evidence_writer_is_append_only_and_checksum_verifiable(tmp_path):
    evidence = SyntheticMonitoringPilot(clock=timestamps()).run()
    target = tmp_path / "MONITOR-PILOT-001.json"
    checksum = tmp_path / "checksums.sha256"

    written, checksums, digest = write_evidence(evidence, target, checksum)

    assert written == target
    assert checksums == checksum
    assert len(digest) == 64
    assert verify_checksum(target, checksum)
    assert json.loads(target.read_text(encoding="utf-8"))["event_id"] == "MONITOR-PILOT-001"
    with pytest.raises(MonitoringPilotError, match="evidence_path_already_exists"):
        write_evidence(evidence, target, checksum)


def test_evidence_contains_no_secret_material():
    evidence = SyntheticMonitoringPilot(clock=timestamps()).run()
    serialized = json.dumps(evidence, sort_keys=True).lower()

    assert "password" not in serialized
    assert "api_key" not in serialized
    assert "token" not in serialized
    assert "private_key" not in serialized
    assert evidence["production_impact"] == {
        "production_database_touched": False,
        "deployment_performed": False,
        "external_services_contacted": False,
    }


def test_replay_digest_is_structurally_deterministic():
    first = SyntheticMonitoringPilot(clock=timestamps()).run()
    second = SyntheticMonitoringPilot(clock=timestamps()).run()

    assert first["replay_digest"] == second["replay_digest"]

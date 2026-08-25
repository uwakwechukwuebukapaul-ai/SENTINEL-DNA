from __future__ import annotations

import json
from pathlib import Path
import tempfile

import pytest

from services.billing.validation import BillingEntitlementValidationRunner, write_immutable_report


ROOT = Path(__file__).resolve().parents[2]
FIXED_ONE = "2026-01-01T00:00:00+00:00"
FIXED_TWO = "2027-01-01T00:00:00+00:00"


def test_all_billing_lifecycle_scenarios_pass_without_provider_calls():
    report = BillingEntitlementValidationRunner(generated_at=FIXED_ONE).run()

    assert report.validation_result == "passed"
    assert [item["scenario_id"] for item in report.scenarios] == [
        "unpaid-tenant-lifecycle",
        "subscription-activation",
        "paid-tenant-downgrade",
        "pre-billing-investigation-preservation",
        "billing-failure-handling",
    ]
    assert all(item["status"] == "passed" for item in report.scenarios)
    assert all(report.security_invariants.values())
    assert report.evidence_policy["real_payment_provider_calls"] is False
    assert report.evidence_policy["production_billing_changes"] is False


def test_report_contains_required_operational_evidence_without_secrets():
    report = BillingEntitlementValidationRunner(generated_at=FIXED_ONE).run()
    payload = report.to_json()

    assert "billing-validation-tenant-a" in payload
    assert "transitions" in payload
    assert "access_decisions" in payload
    assert "audit_validation" in payload
    assert "provenance_validation" in payload
    assert "investigation_preservation" in payload
    assert "replay_digest" in payload
    assert "sk_live" not in payload
    assert "provider_payload" not in payload
    assert "password_value" not in payload
    failure = next(item for item in report.scenarios if item["scenario_id"] == "billing-failure-handling")
    assert failure["checks"]["no_partial_entitlement_activation"] is True
    assert failure["checks"]["failed_billing_event_not_recorded"] is True


def test_replay_digest_is_deterministic_and_report_digest_is_timestamp_bound():
    first = BillingEntitlementValidationRunner(generated_at=FIXED_ONE).run()
    second = BillingEntitlementValidationRunner(generated_at=FIXED_TWO).run()

    assert first.replay_digest == second.replay_digest
    assert first.report_digest != second.report_digest


def test_immutable_report_writer_refuses_replacement_and_repository_local_output():
    report = BillingEntitlementValidationRunner(generated_at=FIXED_ONE).run()
    output = Path(tempfile.mkdtemp(prefix="sentinel-billing-evidence-")) / "billing-entitlements.json"

    write_immutable_report(report, output, repository_root=ROOT)
    assert json.loads(output.read_text(encoding="utf-8"))["replay_digest"] == report.replay_digest
    with pytest.raises(FileExistsError):
        write_immutable_report(report, output, repository_root=ROOT)
    with pytest.raises(ValueError, match="outside_repository"):
        write_immutable_report(report, ROOT / "billing-entitlements.json", repository_root=ROOT)

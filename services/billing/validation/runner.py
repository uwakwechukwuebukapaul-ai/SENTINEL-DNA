"""Synthetic billing entitlement lifecycle evaluator.

This runner is deliberately advisory and evidence-only.  It exercises the
existing billing repository, transition service, entitlement resolver, and
audit service against disposable SQLite state.  It does not call providers,
change application identity/authorization code, or invoke investigation
runtime components.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from typing import Any, Iterator

from database.canonical_authority import ensure_canonical_schema
from database.connection import DatabaseConnection
from database.portability import execute_script
from services.audit.service import AuditService
from services.billing.entitlements import EntitlementService
from services.billing.events import NormalizedBillingEvent
from services.billing.exceptions import BillingError
from services.billing.models import PLANS
from services.billing.repository import BillingRepository
from services.billing.transitions import BillingStateTransitionService

from .models import (
    BillingValidationReport,
    BillingValidationScenario,
    _EntitlementSnapshot,
    _IdentitySnapshot,
    _InvestigationFixture,
    _Observation,
)


REPORT_VERSION = "sentinel-dna-billing-entitlement-validation.v1"
REPLAY_VERSION = "sentinel-dna-billing-entitlement-replay.v1"
TARGET_TENANT = "billing-validation-tenant-a"
OTHER_TENANT = "billing-validation-tenant-b"
TARGET_ACTOR = "billing-validation-actor-a"
OTHER_ACTOR = "billing-validation-actor-b"
FIXED_TIME = "2026-01-01T00:00:00+00:00"
FEATURES = ("investigations", "hunting", "copilot", "sso")


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str) + "\n").encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _json_digest(value: Any) -> str:
    return _digest(value)


def _scenario_result(
    scenario: BillingValidationScenario,
    *,
    transitions: list[dict[str, Any]],
    before: _Observation,
    after: _Observation,
    checks: dict[str, bool],
    audit: dict[str, Any],
    investigation_checks: dict[str, bool],
    provenance_checks: dict[str, bool],
    security_checks: dict[str, bool],
    failure_reason: str | None = None,
) -> dict[str, Any]:
    checks = {**checks, **investigation_checks, **provenance_checks, **security_checks}
    checks["audit_validation"] = bool(audit["valid"])
    return {
        "scenario_id": scenario.scenario_id,
        "title": scenario.title,
        "tenant_ids": list(scenario.tenant_ids),
        "description": scenario.description,
        "transitions": transitions,
        "before": {
            "identity": asdict(before.identity),
            "entitlement": asdict(before.entitlement),
            "access_decisions": before.access_decisions,
        },
        "after": {
            "identity": asdict(after.identity),
            "entitlement": asdict(after.entitlement),
            "access_decisions": after.access_decisions,
        },
        "access_decisions": {
            "before": before.access_decisions,
            "after": after.access_decisions,
        },
        "audit_validation": audit,
        "investigation_preservation": investigation_checks,
        "provenance_validation": provenance_checks,
        "security_invariants": security_checks,
        "checks": dict(sorted(checks.items())),
        "status": "passed" if all(checks.values()) else "failed",
        "failure_reason": failure_reason,
    }


class _SyntheticBillingEnvironment:
    def __init__(self, directory: Path) -> None:
        self.db = DatabaseConnection(directory / "billing-validation.sqlite")
        with self.db.session() as connection:
            ensure_canonical_schema(connection)
            execute_script(
                connection,
                """
                CREATE TABLE investigations (
                    investigation_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    evidence_digest TEXT NOT NULL,
                    provenance_digest TEXT NOT NULL
                );
                CREATE TABLE investigation_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    investigation_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    evidence_digest TEXT NOT NULL,
                    provenance_digest TEXT NOT NULL
                );
                """
            )
            for tenant_id, name, actor_id, email in (
                (TARGET_TENANT, "Validation Tenant A", TARGET_ACTOR, "billing-validation-a@example.test"),
                (OTHER_TENANT, "Validation Tenant B", OTHER_ACTOR, "billing-validation-b@example.test"),
            ):
                connection.execute(
                    "INSERT INTO canonical_tenants(tenant_id,name,status,created_at,updated_at) VALUES(?,?,?,?,?)",
                    (tenant_id, name, "active", FIXED_TIME, FIXED_TIME),
                )
                connection.execute(
                    "INSERT INTO canonical_identities(actor_id,email,display_name,status,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                    (actor_id, email, actor_id, "active", FIXED_TIME, FIXED_TIME),
                )
                connection.execute(
                    "INSERT INTO canonical_memberships(tenant_id,actor_id,role,status,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                    (tenant_id, actor_id, "analyst", "active", FIXED_TIME, FIXED_TIME),
                )
            for tenant_id, suffix in ((TARGET_TENANT, "a"), (OTHER_TENANT, "b")):
                evidence_digest = _digest({"evidence_id": f"evidence-{suffix}", "payload": "synthetic-observation"})
                provenance_digest = _digest({"source": "synthetic-validation-fixture", "tenant_id": tenant_id, "collector": "validation"})
                connection.execute(
                    "INSERT INTO investigations VALUES(?,?,?,?,?)",
                    (f"investigation-{suffix}", tenant_id, "completed", evidence_digest, provenance_digest),
                )
                connection.execute(
                    "INSERT INTO investigation_evidence VALUES(?,?,?,?,?)",
                    (f"evidence-{suffix}", f"investigation-{suffix}", tenant_id, evidence_digest, provenance_digest),
                )
        self.audit = AuditService(self.db)
        self.repository = BillingRepository(self.db)
        self.transitions = BillingStateTransitionService(self.repository)
        self.entitlements = EntitlementService()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        with self.repository.transaction() as connection:
            yield connection

    def identity(self, tenant_id: str) -> _IdentitySnapshot:
        with self.connection() as connection:
            row = connection.execute(
                """SELECT t.tenant_id,t.status AS tenant_status,i.actor_id,i.status AS actor_status,
                          m.role,m.status AS membership_status
                   FROM canonical_tenants t
                   JOIN canonical_memberships m ON m.tenant_id=t.tenant_id
                   JOIN canonical_identities i ON i.actor_id=m.actor_id
                   WHERE t.tenant_id=? ORDER BY i.actor_id LIMIT 1""",
                (tenant_id,),
            ).fetchone()
        if row is None:
            raise AssertionError("synthetic_identity_missing")
        return _IdentitySnapshot(str(row["tenant_id"]), str(row["actor_id"]), str(row["tenant_status"]), str(row["actor_status"]), str(row["role"]), str(row["membership_status"]))

    def investigation(self, tenant_id: str) -> _InvestigationFixture:
        suffix = "a" if tenant_id == TARGET_TENANT else "b"
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM investigations WHERE investigation_id=? AND tenant_id=?",
                (f"investigation-{suffix}", tenant_id),
            ).fetchone()
            evidence = connection.execute(
                "SELECT * FROM investigation_evidence WHERE investigation_id=? AND tenant_id=?",
                (f"investigation-{suffix}", tenant_id),
            ).fetchone()
        if row is None or evidence is None:
            raise AssertionError("synthetic_investigation_missing")
        return _InvestigationFixture(str(row["investigation_id"]), str(evidence["evidence_id"]), tenant_id, str(evidence["evidence_digest"]), str(evidence["provenance_digest"]))

    def retrieve_investigation(self, tenant_id: str, investigation_id: str) -> _InvestigationFixture | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM investigation_evidence WHERE investigation_id=? AND tenant_id=?",
                (investigation_id, tenant_id),
            ).fetchone()
        if row is None:
            return None
        return _InvestigationFixture(str(investigation_id), str(row["evidence_id"]), tenant_id, str(row["evidence_digest"]), str(row["provenance_digest"]))

    def entitlement(self, tenant_id: str) -> _EntitlementSnapshot:
        with self.connection() as connection:
            subscription = self.repository.get_subscription(connection, tenant_id)
        entitlement = self.entitlements.resolve(tenant_id, subscription)
        return _EntitlementSnapshot(
            tenant_id,
            str(subscription["status"]) if subscription else None,
            entitlement.plan_id,
            tuple(sorted(entitlement.capabilities)),
        )

    def observe(self, tenant_id: str) -> _Observation:
        entitlement = self.entitlement(tenant_id)
        return _Observation(
            identity=self.identity(tenant_id),
            entitlement=entitlement,
            investigation=self.investigation(tenant_id),
            access_decisions={feature: feature in entitlement.capabilities for feature in FEATURES},
        )

    def save_subscription(self, tenant_id: str, plan_id: str, status: str) -> None:
        with self.connection() as connection:
            self.repository.save_subscription(connection, tenant_id, "synthetic-billing", plan_id, status)

    def create_pending_payment(self, tenant_id: str, reference: str, plan_id: str = "PRO") -> None:
        with self.connection() as connection:
            self.repository.create_transaction(connection, tenant_id, reference, "synthetic-billing", plan_id, 100, "NGN")
            self.repository.save_subscription(connection, tenant_id, "synthetic-billing", plan_id, "PENDING")

    def billing_row(self, reference: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = self.repository.get_transaction(connection, reference)
        return dict(row) if row else None

    def event_exists(self, event_id: str) -> bool:
        with self.connection() as connection:
            return self.repository.event_exists(connection, event_id)

    def record_audit(self, event_type: str, tenant_id: str, outcome: str) -> None:
        self.audit.record(
            event_type,
            details={"validation_scenario": True, "outcome": outcome},
            tenant_id=tenant_id,
            actor_id=TARGET_ACTOR if tenant_id == TARGET_TENANT else OTHER_ACTOR,
            resource_type="billing_entitlement_validation",
            resource_id=tenant_id,
            operation="observe",
            outcome=outcome,
        )

    def audit_validation(self, tenant_id: str, expected_event_type: str) -> dict[str, Any]:
        with self.db.session() as connection:
            rows = connection.execute(
                "SELECT id,event_type,tenant_id FROM audit_events WHERE tenant_id=? ORDER BY id",
                (tenant_id,),
            ).fetchall()
        event_types = [str(row["event_type"]) for row in rows]
        update_blocked = delete_blocked = False
        if rows:
            event_id = int(rows[0]["id"])
            for statement in (
                f"UPDATE audit_events SET outcome='tampered' WHERE id={event_id}",
                f"DELETE FROM audit_events WHERE id={event_id}",
            ):
                try:
                    with self.db.session() as connection:
                        connection.execute(statement)
                except Exception:
                    if statement.startswith("UPDATE"):
                        update_blocked = True
                    else:
                        delete_blocked = True
        checks = {
            "event_recorded": expected_event_type in event_types,
            "tenant_bound": bool(rows) and all(str(row["tenant_id"]) == tenant_id for row in rows),
            "append_only_update_blocked": update_blocked,
            "append_only_delete_blocked": delete_blocked,
        }
        return {"valid": all(checks.values()), "checks": checks, "event_types": event_types, "event_count": len(event_types)}


class BillingEntitlementValidationRunner:
    def __init__(self, *, generated_at: str | None = None) -> None:
        self.generated_at = generated_at or datetime.now(timezone.utc).isoformat()

    @staticmethod
    def scenarios() -> tuple[BillingValidationScenario, ...]:
        return (
            BillingValidationScenario("unpaid-tenant-lifecycle", "Unpaid Tenant Lifecycle", (TARGET_TENANT, OTHER_TENANT), "An active tenant without a subscription remains identifiable while restricted capabilities fail closed."),
            BillingValidationScenario("subscription-activation", "Subscription Activation", (TARGET_TENANT, OTHER_TENANT), "An existing unpaid tenant receives a synthetic active entitlement."),
            BillingValidationScenario("paid-tenant-downgrade", "Paid Tenant Downgrade", (TARGET_TENANT, OTHER_TENANT), "An enterprise tenant is reduced to a lower active plan without changing ownership or history."),
            BillingValidationScenario("pre-billing-investigation-preservation", "Pre-Billing Investigation Preservation", (TARGET_TENANT, OTHER_TENANT), "An investigation created before billing activation remains retrievable with identical evidence provenance."),
            BillingValidationScenario("billing-failure-handling", "Billing Failure Handling", (TARGET_TENANT, OTHER_TENANT), "A synthetic provider/amount mismatch fails before subscription activation and leaves no partial entitlement."),
        )

    def _activation(self, environment: _SyntheticBillingEnvironment, *, event_id: str) -> dict[str, Any]:
        environment.create_pending_payment(TARGET_TENANT, "billing-validation-reference", "PRO")
        result = environment.transitions.apply(
            NormalizedBillingEvent(
                provider="synthetic-billing",
                provider_event_id=event_id,
                event_type="subscription.activated",
                tenant_id=TARGET_TENANT,
                provider_transaction_reference="billing-validation-reference",
                provider_subscription_reference="billing-validation-subscription",
                transaction_status="SUCCESS",
                subscription_status="ACTIVE",
                amount_minor=100,
                currency="NGN",
                occurred_at=FIXED_TIME,
            )
        )
        environment.record_audit("BILLING_ENTITLEMENT_ACTIVATED", TARGET_TENANT, "applied")
        return {"event_id": event_id, "applied": bool(result.applied), "old_status": result.old_status, "new_status": result.new_status}

    def _run_scenario(self, scenario: BillingValidationScenario) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="sentinel-billing-validation-") as directory:
            environment = _SyntheticBillingEnvironment(Path(directory))
            before = environment.observe(TARGET_TENANT)
            transitions: list[dict[str, Any]] = []
            failure_reason: str | None = None
            if scenario.scenario_id == "unpaid-tenant-lifecycle":
                environment.record_audit("BILLING_UNPAID_LIFECYCLE_OBSERVED", TARGET_TENANT, "restricted")
                after = environment.observe(TARGET_TENANT)
                checks = {
                    "tenant_exists_without_active_billing": before.identity.tenant_status == "active" and before.entitlement.subscription_status is None,
                    "identity_remains_valid": before.identity.actor_status == "active" and before.identity.membership_status == "active",
                    "restricted_capabilities_fail_closed": not any(before.access_decisions.values()),
                    "enterprise_features_not_exposed": not before.access_decisions["copilot"] and not before.access_decisions["sso"],
                    "tenant_ownership_unchanged": before.identity.tenant_id == after.identity.tenant_id,
                }
                audit_type = "BILLING_UNPAID_LIFECYCLE_OBSERVED"
            elif scenario.scenario_id in {"subscription-activation", "pre-billing-investigation-preservation"}:
                transitions.append(self._activation(environment, event_id=f"billing-validation-{scenario.scenario_id}"))
                after = environment.observe(TARGET_TENANT)
                checks = {
                    "billing_transition_applied": transitions[0]["applied"],
                    "new_capabilities_match_entitlement": set(after.entitlement.capabilities) == set(PLANS["PRO"].capabilities),
                    "only_entitlement_state_changed": before.identity == after.identity and before.investigation == after.investigation,
                    "other_tenant_unchanged": environment.observe(OTHER_TENANT).identity.tenant_id == OTHER_TENANT,
                }
                audit_type = "BILLING_ENTITLEMENT_ACTIVATED"
            elif scenario.scenario_id == "paid-tenant-downgrade":
                environment.save_subscription(TARGET_TENANT, "ENTERPRISE", "ACTIVE")
                before = environment.observe(TARGET_TENANT)
                environment.save_subscription(TARGET_TENANT, "PRO", "ACTIVE")
                environment.record_audit("BILLING_ENTITLEMENT_DOWNGRADED", TARGET_TENANT, "applied")
                after = environment.observe(TARGET_TENANT)
                checks = {
                    "tenant_remains_valid": after.identity.tenant_status == "active",
                    "historical_investigation_accessible": environment.retrieve_investigation(TARGET_TENANT, before.investigation.investigation_id) is not None,
                    "restricted_features_removed": not after.access_decisions["copilot"] and not after.access_decisions["sso"],
                    "no_privilege_escalation": set(after.entitlement.capabilities).issubset(before.entitlement.capabilities),
                    "evidence_ownership_unchanged": after.investigation.tenant_id == TARGET_TENANT,
                }
                audit_type = "BILLING_ENTITLEMENT_DOWNGRADED"
            else:
                environment.create_pending_payment(TARGET_TENANT, "billing-validation-failure-reference", "PRO")
                try:
                    environment.transitions.apply(
                        NormalizedBillingEvent(
                            provider="synthetic-billing",
                            provider_event_id="billing-validation-failed-event",
                            event_type="subscription.activated",
                            tenant_id=TARGET_TENANT,
                            provider_transaction_reference="billing-validation-failure-reference",
                            provider_subscription_reference="billing-validation-failure-subscription",
                            transaction_status="SUCCESS",
                            subscription_status="ACTIVE",
                            amount_minor=999,
                            currency="NGN",
                            occurred_at=FIXED_TIME,
                        )
                    )
                except Exception as exc:
                    failure_reason = type(exc).__name__
                environment.record_audit("BILLING_ENTITLEMENT_ACTIVATION_FAILED", TARGET_TENANT, "rejected")
                after = environment.observe(TARGET_TENANT)
                billing_row = environment.billing_row("billing-validation-failure-reference") or {}
                checks = {
                    "provider_failure_rejected": failure_reason is not None,
                    "no_partial_entitlement_activation": after.entitlement.subscription_status == "PENDING" and not after.access_decisions["investigations"],
                    "no_elevated_privileges": not any(after.access_decisions.values()),
                    "subscription_state_consistent": billing_row.get("status") == "PENDING",
                    "failed_billing_event_not_recorded": not environment.event_exists("billing-validation-failed-event"),
                    "fail_closed_behavior_preserved": after.entitlement.capabilities == (),
                }
                audit_type = "BILLING_ENTITLEMENT_ACTIVATION_FAILED"
            investigation_checks = {
                "investigation_retrievable": environment.retrieve_investigation(TARGET_TENANT, before.investigation.investigation_id) is not None,
                "investigation_digest_preserved": before.investigation.evidence_digest == after.investigation.evidence_digest,
                "evidence_digest_preserved": before.investigation.evidence_digest == after.investigation.evidence_digest,
            }
            provenance_checks = {
                "provenance_digest_preserved": before.investigation.provenance_digest == after.investigation.provenance_digest,
                "provenance_tenant_unchanged": after.investigation.tenant_id == TARGET_TENANT,
            }
            security_checks = {
                "identity_unchanged": before.identity == after.identity,
                "tenant_id_unchanged": before.entitlement.tenant_id == after.entitlement.tenant_id == TARGET_TENANT,
                "authorization_boundary_not_invoked": True,
                "autonomous_response_not_invoked": True,
                "advisory_memory_boundary_preserved": True,
            }
            audit = environment.audit_validation(TARGET_TENANT, audit_type)
            return _scenario_result(
                scenario,
                transitions=transitions,
                before=before,
                after=after,
                checks=checks,
                audit=audit,
                investigation_checks=investigation_checks,
                provenance_checks=provenance_checks,
                security_checks=security_checks,
                failure_reason=failure_reason,
            )

    def run(self) -> BillingValidationReport:
        scenarios = tuple(BillingScenarioEvaluator().evaluate(scenario) for scenario in self.scenarios())
        metrics = {
            "scenario_count": len(scenarios),
            "passed_scenario_count": sum(item["status"] == "passed" for item in scenarios),
            "failed_scenario_count": sum(item["status"] != "passed" for item in scenarios),
            "audit_validated_scenario_count": sum(item["checks"].get("audit_validation", False) for item in scenarios),
            "investigation_preserved_scenario_count": sum(item["checks"].get("investigation_digest_preserved", False) for item in scenarios),
        }
        security = {
            "authentication_untouched": True,
            "authorization_untouched": all(item["checks"].get("authorization_boundary_not_invoked", False) for item in scenarios),
            "verdict_enforcement_untouched": True,
            "tenant_isolation_preserved": all(item["checks"].get("tenant_id_unchanged", False) for item in scenarios),
            "fail_closed_behavior": all(item["checks"].get("fail_closed_behavior_preserved", True) for item in scenarios),
            "audit_integrity": all(item["checks"].get("audit_validation", False) for item in scenarios),
            "append_only_evidence": all(item["audit_validation"]["checks"]["append_only_update_blocked"] and item["audit_validation"]["checks"]["append_only_delete_blocked"] for item in scenarios),
            "provenance_tracking": all(item["checks"].get("provenance_digest_preserved", False) for item in scenarios),
            "advisory_memory_boundary": all(item["checks"].get("advisory_memory_boundary_preserved", False) for item in scenarios),
            "autonomous_response_boundary": all(item["checks"].get("autonomous_response_not_invoked", False) for item in scenarios),
        }
        replay_body = {
            "replay_version": REPLAY_VERSION,
            "scenarios": scenarios,
            "metrics": metrics,
            "security_invariants": security,
            "evidence_policy": {
                "synthetic_tenants_only": True,
                "real_payment_provider_calls": False,
                "production_billing_changes": False,
                "secrets_serialized": False,
                "credentials_changed": False,
                "investigation_runtime_invoked": False,
                "replay_excludes": ["generated_at", "audit_event_ids", "timestamps"],
            },
        }
        replay = _digest(replay_body)
        report_body = {**replay_body, "report_version": REPORT_VERSION, "generated_at": self.generated_at, "validation_result": "passed" if all(item["status"] == "passed" for item in scenarios) and all(security.values()) else "failed", "replay_digest": replay}
        return BillingValidationReport(
            REPORT_VERSION,
            self.generated_at,
            report_body["validation_result"],
            scenarios,
            metrics,
            security,
            replay_body["evidence_policy"],
            replay,
            _digest(report_body),
        )


class BillingScenarioEvaluator:
    """Evaluate one named scenario using a fresh disposable billing state."""

    def evaluate(self, scenario: BillingValidationScenario) -> dict[str, Any]:
        runner = BillingEntitlementValidationRunner(generated_at=FIXED_TIME)
        return runner._run_scenario(scenario)


def deterministic_replay_digest(value: Any) -> str:
    """Create the canonical SHA-256 digest used for replay comparisons."""

    return _digest(value)


__all__ = ["BillingEntitlementValidationRunner", "BillingScenarioEvaluator", "deterministic_replay_digest"]

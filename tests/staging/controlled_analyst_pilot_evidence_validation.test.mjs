import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import {
  validateAuthenticatedAnalystAccess,
  validateAuditTrail,
  validateRbacEnforcement,
  validateSessionRevocation,
  validateTenantIsolation,
} from "../../deployment/staging/scripts/controlled_analyst_pilot_evidence_validation.mjs";

// This is an in-memory contract fixture only. It is not pilot evidence, does
// not represent a real analyst or authentication event, and is never written
// to pilot-evidence/.
function gate(observation = "Direct operator observation recorded") {
  return {
    status: "PASS",
    observed_at_utc: "2026-09-02T12:00:00Z",
    evidence_reference: "custody:gate4-test-reference",
    observation,
  };
}

function completeEvidence() {
  const gates = Object.fromEntries([
    "manager_authentication",
    "csrf_protection",
    "analyst_rbac",
    "audit_logging",
    "provenance_verification",
    "investigation_workflow",
    "ai_advisory_only",
    "deny_cross_tenant",
    "deny_admin_escalation",
    "deny_database",
    "deny_shell_container",
    "deny_destructive",
    "session_revocation",
  ].map((name) => [name, gate()]));
  gates.tenant_isolation = {
    ...gate(),
    details: { foreign_tenant_denied: true, foreign_data_leakage: false },
  };

  return {
    schema_version: "1.0",
    evidence_class: "authenticated_controlled_analyst_pilot",
    status: "VERIFIED",
    run_id: "pilot-test-contract-001",
    source_commit: "fa8aa1fef3010beb00dff84bd7f76fec4e0fbaaf",
    scope: {
      synthetic_data_only: true,
      synthetic_tenant_count: 1,
      synthetic_analyst_count: 1,
      tenant_id: "tenant-test-001",
      analyst_id: "analyst-test-001",
      role: "analyst",
      production_data_used: false,
    },
    boundary: {
      edge_binding: "127.0.0.1:18443->443/tcp",
      private_edge_verified: "PASS",
      public_exposure: false,
      tls_san_verified: "PASS",
      app_postgres_redis_host_ports: "PASS",
      docker_network_isolation: "PASS",
    },
    controls: {
      private_edge: "PASS",
      public_exposure: false,
      secret_free_evidence: true,
      credentials_or_tokens_in_evidence: false,
      customer_data_in_evidence: false,
    },
    gates,
    audit: {
      action_references: ["custody:action-test-001"],
      audit_references: ["custody:audit-test-001"],
      provenance_references: ["custody:provenance-test-001"],
      all_sensitive_actions_audited: true,
    },
    revocation: {
      authorization_revoked: "PASS",
      analyst_deactivated: "PASS",
      sessions_invalidated: "PASS",
      post_revocation_fail_closed: "PASS",
    },
    decision: { human_release_approval: "PASS", analyst_url_issued: false },
  };
}

test("all five focused validators pass only the complete pilot evidence contract", () => {
  const evidence = completeEvidence();
  for (const validator of [
    validateAuthenticatedAnalystAccess,
    validateRbacEnforcement,
    validateTenantIsolation,
    validateAuditTrail,
    validateSessionRevocation,
  ]) assert.equal(validator(evidence).status, "PASS");
});

test("rehearsal evidence cannot satisfy authenticated analyst access", () => {
  const evidence = completeEvidence();
  evidence.evidence_class = "rehearsal";
  const result = validateAuthenticatedAnalystAccess(evidence);
  assert.equal(result.status, "BLOCKED_WITH_REASON");
  assert.match(result.failures.join(" "), /evidence_class/);
});

test("unmeasured or missing RBAC gates fail closed", () => {
  const evidence = completeEvidence();
  evidence.gates.analyst_rbac.status = "NOT_MEASURED";
  const result = validateRbacEnforcement(evidence);
  assert.equal(result.status, "BLOCKED_WITH_REASON");
  assert.match(result.failures.join(" "), /analyst_rbac/);
});

test("tenant isolation requires direct foreign-tenant denial and no leakage", () => {
  const evidence = completeEvidence();
  evidence.gates.tenant_isolation.details.foreign_data_leakage = true;
  const result = validateTenantIsolation(evidence);
  assert.equal(result.status, "BLOCKED_WITH_REASON");
  assert.match(result.failures.join(" "), /foreign tenant leakage/);
});

test("audit validation requires action, audit, provenance, and sensitive-action coverage", () => {
  const evidence = completeEvidence();
  evidence.audit.audit_references = [];
  evidence.audit.all_sensitive_actions_audited = false;
  const result = validateAuditTrail(evidence);
  assert.equal(result.status, "BLOCKED_WITH_REASON");
  assert.match(result.failures.join(" "), /audit event reference/);
  assert.match(result.failures.join(" "), /sensitive actions/);
});

test("session revocation validation requires every post-revocation control", () => {
  const evidence = completeEvidence();
  evidence.revocation.sessions_invalidated = "NOT_MEASURED";
  const result = validateSessionRevocation(evidence);
  assert.equal(result.status, "BLOCKED_WITH_REASON");
  assert.match(result.failures.join(" "), /sessions_invalidated/);
});

test("secret-shaped values are rejected without echoing the value", () => {
  const evidence = completeEvidence();
  const secret = "Bearer do-not-store-this-value";
  evidence.gates.audit_logging.observation = secret;
  const result = validateAuditTrail(evidence);
  assert.equal(result.status, "BLOCKED_WITH_REASON");
  assert.doesNotMatch(JSON.stringify(result), /do-not-store-this-value/);
});

test("authenticated pilot schema keeps evidence class and required control families explicit", async () => {
  const schema = JSON.parse(await readFile(
    new URL("../../deployment/staging/CONTROLLED_ANALYST_PILOT_EVIDENCE.schema.json", import.meta.url),
    "utf8",
  ));
  assert.equal(schema.properties.evidence_class.const, "authenticated_controlled_analyst_pilot");
  assert.equal(schema.properties.status.const, "VERIFIED");
  assert.deepEqual(schema.required, [
    "schema_version",
    "evidence_class",
    "status",
    "run_id",
    "source_commit",
    "started_at_utc",
    "completed_at_utc",
    "scope",
    "boundary",
    "controls",
    "gates",
    "audit",
    "revocation",
    "decision",
  ]);
});

test("remote access evidence schema separates preflight, rehearsal, and authenticated classes", async () => {
  const schema = JSON.parse(await readFile(
    new URL("../../deployment/staging/GATE5_ANALYST_ACCESS_EVIDENCE.schema.json", import.meta.url),
    "utf8",
  ));
  assert.deepEqual(schema.properties.evidence_class.enum, [
    "rehearsal",
    "remote_access_preflight",
    "authenticated_controlled_analyst_pilot",
  ]);
  assert.equal(schema.properties.origin.const, "https://uwakwe-desktop.taile388cc.ts.net");
  assert.deepEqual(schema.properties.observations.required, [
    "authenticated_analyst_access",
    "rbac_enforcement",
    "tenant_isolation",
    "audit_trail",
    "session_revocation",
  ]);
});

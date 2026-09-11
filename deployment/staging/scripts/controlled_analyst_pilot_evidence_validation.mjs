/**
 * Shared, read-only validators for authenticated controlled-analyst-pilot
 * evidence. These validators inspect a human-captured evidence record only;
 * they do not authenticate, provision, call the application, or mutate state.
 */

import { readFile } from "node:fs/promises";

const PASS = "PASS";
const UTC_TIMESTAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/;
const SENSITIVE_VALUE = /-----BEGIN|\bBearer\s+[A-Za-z0-9._~-]+|\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/i;

const REQUIRED_BOUNDARY_PASSES = Object.freeze([
  "private_edge_verified",
  "tls_san_verified",
  "app_postgres_redis_host_ports",
  "docker_network_isolation",
]);

const REQUIRED_GATES = Object.freeze({
  authenticated_analyst_access: ["manager_authentication", "analyst_rbac"],
  rbac_enforcement: [
    "csrf_protection",
    "analyst_rbac",
    "deny_admin_escalation",
    "deny_database",
    "deny_shell_container",
    "deny_destructive",
  ],
  tenant_isolation: ["tenant_isolation", "deny_cross_tenant"],
  audit_trail: ["audit_logging", "provenance_verification", "investigation_workflow", "ai_advisory_only"],
  session_revocation: ["session_revocation"],
});

function nonEmpty(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function validUtc(value) {
  return typeof value === "string" && UTC_TIMESTAMP.test(value) && !Number.isNaN(Date.parse(value));
}

function inspectStrings(value, path, failures) {
  if (typeof value === "string") {
    if (SENSITIVE_VALUE.test(value)) failures.push(`secret-shaped value at ${path}`);
    return;
  }
  if (!value || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) inspectStrings(child, `${path}.${key}`, failures);
}

function fail(failures, condition, message) {
  if (!condition) failures.push(message);
}

/** Validate the non-gate envelope common to every authenticated pilot record. */
export function validatePilotEvidenceEnvelope(evidence) {
  const failures = [];
  if (!evidence || typeof evidence !== "object" || Array.isArray(evidence)) {
    return ["evidence must be a JSON object"];
  }

  fail(failures, evidence.evidence_class === "authenticated_controlled_analyst_pilot", "evidence_class must identify authenticated controlled analyst pilot evidence");
  fail(failures, evidence.status === "VERIFIED", "evidence status must be VERIFIED");
  fail(failures, nonEmpty(evidence.run_id) && !evidence.run_id.includes("REPLACE_WITH"), "run_id is missing or still a placeholder");

  const scope = evidence.scope ?? {};
  fail(failures, scope.synthetic_data_only === true, "synthetic_data_only must be true");
  fail(failures, scope.synthetic_tenant_count === 1, "exactly one synthetic tenant is required");
  fail(failures, scope.synthetic_analyst_count === 1, "exactly one synthetic analyst is required");
  fail(failures, nonEmpty(scope.tenant_id) && nonEmpty(scope.analyst_id), "tenant and analyst identifiers are required");
  fail(failures, String(scope.role).toLowerCase() === "analyst", "analyst role is required");
  fail(failures, scope.production_data_used === false, "production data must be false");

  const boundary = evidence.boundary ?? {};
  fail(failures, boundary.edge_binding === "127.0.0.1:18443->443/tcp", "certified loopback edge binding is not confirmed");
  for (const field of REQUIRED_BOUNDARY_PASSES) fail(failures, boundary[field] === PASS, `boundary.${field} must be PASS`);
  fail(failures, boundary.public_exposure === false, "boundary.public_exposure must be false");

  const controls = evidence.controls ?? {};
  fail(failures, controls.private_edge === PASS, "controls.private_edge must be PASS");
  fail(failures, controls.public_exposure === false, "controls.public_exposure must be false");
  fail(failures, controls.secret_free_evidence === true, "evidence must be marked secret-free");
  fail(failures, controls.credentials_or_tokens_in_evidence === false, "credentials or tokens must not be in evidence");
  fail(failures, controls.customer_data_in_evidence === false, "customer data must not be in evidence");

  inspectStrings(evidence, "evidence", failures);
  return [...new Set(failures)];
}

function validateGate(evidence, gateName, failures) {
  const gate = evidence.gates?.[gateName];
  fail(failures, gate?.status === PASS, `gate ${gateName} is not PASS`);
  if (gate?.status !== PASS) return;
  fail(failures, validUtc(gate.observed_at_utc), `gate ${gateName} lacks a valid UTC timestamp`);
  fail(failures, nonEmpty(gate.evidence_reference), `gate ${gateName} lacks an evidence reference`);
  fail(failures, nonEmpty(gate.observation), `gate ${gateName} lacks a direct observation`);
}

function validateCommon(evidence, gateSet) {
  const failures = validatePilotEvidenceEnvelope(evidence);
  for (const gateName of gateSet) validateGate(evidence, gateName, failures);
  return [...new Set(failures)];
}

export function validateAuthenticatedAnalystAccess(evidence) {
  const failures = validateCommon(evidence, REQUIRED_GATES.authenticated_analyst_access);
  return result("authenticated_analyst_access", failures);
}

export function validateRbacEnforcement(evidence) {
  const failures = validateCommon(evidence, REQUIRED_GATES.rbac_enforcement);
  return result("rbac_enforcement", failures);
}

export function validateTenantIsolation(evidence) {
  const failures = validateCommon(evidence, REQUIRED_GATES.tenant_isolation);
  const tenant = evidence?.gates?.tenant_isolation?.details ?? {};
  fail(failures, tenant.foreign_tenant_denied === true, "foreign tenant denial is not directly confirmed");
  fail(failures, tenant.foreign_data_leakage === false, "foreign tenant leakage must be false");
  return result("tenant_isolation", [...new Set(failures)]);
}

export function validateAuditTrail(evidence) {
  const failures = validateCommon(evidence, REQUIRED_GATES.audit_trail);
  const audit = evidence?.audit ?? {};
  fail(failures, Array.isArray(audit.action_references) && audit.action_references.length > 0, "audit action reference is missing");
  fail(failures, Array.isArray(audit.audit_references) && audit.audit_references.length > 0, "audit event reference is missing");
  fail(failures, Array.isArray(audit.provenance_references) && audit.provenance_references.length > 0, "provenance reference is missing");
  fail(failures, audit.all_sensitive_actions_audited === true, "all sensitive actions are not confirmed audited");
  return result("audit_trail", [...new Set(failures)]);
}

export function validateSessionRevocation(evidence) {
  const failures = validateCommon(evidence, REQUIRED_GATES.session_revocation);
  const revocation = evidence?.revocation ?? {};
  for (const field of ["authorization_revoked", "analyst_deactivated", "sessions_invalidated", "post_revocation_fail_closed"]) {
    fail(failures, revocation[field] === PASS, `revocation.${field} must be PASS`);
  }
  return result("session_revocation", [...new Set(failures)]);
}

function result(control, failures) {
  return failures.length === 0
    ? { status: PASS, control }
    : { status: "BLOCKED_WITH_REASON", control, failure_category: "TB_PILOT_EVIDENCE_INVALID", failures };
}

export async function readEvidenceAndValidate(inputPath, validator) {
  if (!inputPath) return { status: "BLOCKED_WITH_REASON", reason: "evidence path is required" };
  try {
    const evidence = JSON.parse(await readFile(inputPath, "utf8"));
    return validator(evidence);
  } catch {
    return { status: "BLOCKED_WITH_REASON", reason: "evidence could not be read or parsed" };
  }
}

export { REQUIRED_GATES };

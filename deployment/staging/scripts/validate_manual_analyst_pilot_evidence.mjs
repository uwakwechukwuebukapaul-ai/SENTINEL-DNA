/**
 * Read-only, fail-closed validator for manually captured pilot evidence.
 *
 * This tool never contacts Sentinel DNA, creates identities, changes state, or
 * issues an endpoint. It returns READY only for a completed, human-reviewed,
 * secret-free evidence record with every required gate and revocation check.
 */

import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

const REQUIRED_GATES = Object.freeze([
  "manager_authentication",
  "csrf_protection",
  "analyst_rbac",
  "tenant_isolation",
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
]);

const SAFE_STATUS = "PASS";
const UTC_TIMESTAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/;
const SENSITIVE_VALUE = /-----BEGIN|\bBearer\s+[A-Za-z0-9._~-]+|\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/i;

function addFailure(failures, message) {
  failures.push(message);
}

function nonEmpty(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function isUtcTimestamp(value) {
  return typeof value === "string" && UTC_TIMESTAMP.test(value) && !Number.isNaN(Date.parse(value));
}

function inspectStringValues(value, path, failures) {
  if (typeof value === "string") {
    if (SENSITIVE_VALUE.test(value)) addFailure(failures, `secret-shaped value at ${path}`);
    return;
  }
  if (!value || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) inspectStringValues(child, `${path}.${key}`, failures);
}

export function validateEvidence(evidence) {
  const failures = [];
  if (!evidence || typeof evidence !== "object" || Array.isArray(evidence)) {
    return ["evidence must be a JSON object"];
  }

  if (evidence.evidence_class !== "authenticated_controlled_analyst_pilot") {
    addFailure(failures, "evidence_class must identify authenticated controlled analyst pilot evidence");
  }
  if (evidence.status !== "VERIFIED") addFailure(failures, "evidence status must be VERIFIED");
  if (!nonEmpty(evidence.run_id) || evidence.run_id.includes("REPLACE_WITH")) addFailure(failures, "run_id is missing or still a placeholder");
  if (evidence.scope?.synthetic_data_only !== true) addFailure(failures, "synthetic_data_only must be true");
  if (evidence.scope?.synthetic_tenant_count !== 1) addFailure(failures, "exactly one synthetic tenant is required");
  if (evidence.scope?.synthetic_analyst_count !== 1) addFailure(failures, "exactly one synthetic analyst is required");
  if (!nonEmpty(evidence.scope?.tenant_id) || !nonEmpty(evidence.scope?.analyst_id)) addFailure(failures, "tenant and analyst identifiers are required");
  if (String(evidence.scope?.role).toLowerCase() !== "analyst") addFailure(failures, "analyst role is required");
  if (evidence.scope?.production_data_used !== false) addFailure(failures, "production data must be false");

  const boundary = evidence.boundary ?? {};
  if (boundary.edge_binding !== "127.0.0.1:18443->443/tcp") addFailure(failures, "certified loopback edge binding is not confirmed");
  for (const field of ["private_edge_verified", "public_exposure", "tls_san_verified", "app_postgres_redis_host_ports", "docker_network_isolation"]) {
    if (boundary[field] !== SAFE_STATUS) addFailure(failures, `boundary.${field} must be PASS`);
  }
  if (evidence.controls?.private_edge !== SAFE_STATUS) addFailure(failures, "controls.private_edge must be PASS");
  if (evidence.controls?.public_exposure !== false) addFailure(failures, "public_exposure must be false");
  if (evidence.controls?.secret_free_evidence !== true) addFailure(failures, "evidence must be marked secret-free");
  if (evidence.controls?.credentials_or_tokens_in_evidence !== false) addFailure(failures, "credentials or tokens must not be in evidence");
  if (evidence.controls?.customer_data_in_evidence !== false) addFailure(failures, "customer data must not be in evidence");

  for (const gate of REQUIRED_GATES) {
    const result = evidence.gates?.[gate];
    if (result?.status !== SAFE_STATUS) {
      addFailure(failures, `gate ${gate} is not PASS`);
      continue;
    }
    if (!isUtcTimestamp(result.observed_at_utc)) addFailure(failures, `gate ${gate} lacks a valid UTC timestamp`);
    if (!nonEmpty(result.evidence_reference)) addFailure(failures, `gate ${gate} lacks an evidence reference`);
  }

  const audit = evidence.audit ?? {};
  if (!Array.isArray(audit.action_references) || audit.action_references.length === 0) addFailure(failures, "audit action reference is missing");
  if (!Array.isArray(audit.audit_references) || audit.audit_references.length === 0) addFailure(failures, "audit event reference is missing");
  if (!Array.isArray(audit.provenance_references) || audit.provenance_references.length === 0) addFailure(failures, "provenance reference is missing");
  if (audit.all_sensitive_actions_audited !== true) addFailure(failures, "all sensitive actions are not confirmed audited");

  const revocation = evidence.revocation ?? {};
  for (const field of ["authorization_revoked", "analyst_deactivated", "sessions_invalidated", "post_revocation_fail_closed"]) {
    if (revocation[field] !== SAFE_STATUS) addFailure(failures, `revocation.${field} must be PASS`);
  }
  if (evidence.decision?.human_release_approval !== SAFE_STATUS) addFailure(failures, "human release approval is not PASS");
  if (evidence.decision?.analyst_url_issued !== false) addFailure(failures, "analyst URL must remain unissued");

  inspectStringValues(evidence, "evidence", failures);
  return [...new Set(failures)];
}

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  const input = process.argv[2];
  if (!input) {
    console.error(JSON.stringify({ status: "BLOCKED_WITH_REASON", reason: "evidence path is required" }));
    process.exit(2);
  }
  try {
    const evidence = JSON.parse(await readFile(input, "utf8"));
    const failures = validateEvidence(evidence);
    const status = failures.length === 0 ? "READY_FOR_CONTROLLED_ANALYST_PILOT" : "BLOCKED_WITH_REASON";
    console.log(JSON.stringify({ status, analyst_url_issued: false, failures }));
    process.exit(failures.length === 0 ? 0 : 2);
  } catch {
    console.error(JSON.stringify({ status: "BLOCKED_WITH_REASON", reason: "cannot validate evidence" }));
    process.exit(2);
  }
}

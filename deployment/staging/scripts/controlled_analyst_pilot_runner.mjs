/**
 * Browser-bound controlled analyst pilot gate runner.
 *
 * This module is intentionally not a standalone HTTP client. It must receive
 * the approved browser object from the trusted browser service. It never
 * accepts passwords, cookies, activation tokens, or CSRF tokens as arguments;
 * browserAuth and page-local fetches keep those values out of model-visible
 * output. Provisioning is disabled unless explicitly enabled by a later
 * operator-authorized run.
 */

import { createHash } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";
import {
  createTrustedBrowserDiagnostics,
  safeTrustedBrowserCode,
  TRUSTED_BROWSER_TIMEOUTS,
} from "./trusted_browser_diagnostics.mjs";

export const DEFAULT_ORIGIN = "https://uwakwe-desktop.taile388cc.ts.net";
export const DEFAULT_EVIDENCE_DIR = "C:/ProgramData/Sentinel-DNA/release/evidence";

const SECRET_KEYS = new Set([
  "password",
  "password_hash",
  "activation_token",
  "csrf_token",
  "token",
  "cookie",
  "set-cookie",
  "authorization",
  "private_key",
  "secret",
]);

const MANAGER_ROLES = new Set(["admin", "soc_manager"]);

export const PILOT_GATE_CATALOG = Object.freeze([
  "manager_login_session",
  "csrf_protection",
  "analyst_rbac",
  "analyst_tenant_scope",
  "audit_event_generation",
  "evidence_provenance",
  "synthetic_investigation_workflow",
  "ai_advisory_only",
  "deny_cross_tenant",
  "deny_admin",
  "deny_database",
  "deny_shell_container",
  "deny_destructive",
]);

function requireRunId(runId) {
  if (typeof runId !== "string" || !/^[A-Za-z0-9][A-Za-z0-9._-]{2,96}$/.test(runId)) {
    throw new Error("runId must be an operator-assigned non-secret identifier");
  }
  return runId;
}

function validateOrigin(origin) {
  const parsed = new URL(origin);
  if (parsed.protocol !== "https:") throw new Error("pilot origin must use HTTPS");
  if (parsed.hostname !== "uwakwe-desktop.taile388cc.ts.net") throw new Error("pilot origin hostname is not the certified Tailscale staging host");
  if (parsed.port !== "") throw new Error("pilot origin must use the certified HTTPS port");
  if (parsed.pathname !== "/" || parsed.search || parsed.hash) throw new Error("pilot origin must not contain a path, query, or fragment");
  return parsed.origin;
}

function scrub(value, seen = new WeakSet()) {
  if (value === null || typeof value !== "object") return value;
  if (seen.has(value)) return "[cycle omitted]";
  seen.add(value);
  if (Array.isArray(value)) return value.map((item) => scrub(item, seen));
  const result = {};
  for (const [key, child] of Object.entries(value)) {
    if (SECRET_KEYS.has(key.toLowerCase())) continue;
    result[key] = scrub(child, seen);
  }
  return result;
}

function assertNoSecrets(value) {
  const text = JSON.stringify(value).toLowerCase();
  for (const key of SECRET_KEYS) {
    if (text.includes(`"${key}"`)) throw new Error(`secret-shaped field reached evidence: ${key}`);
  }
}

function record(check, status, observation, extra = {}) {
  return { check, status, observation, ...scrub(extra) };
}

async function visibleAndEnabled(locator, label, diagnostics) {
  const check = async () => {
    if (await locator.count() !== 1) throw new Error(`${label} selector did not resolve exactly once`);
    if (!(await locator.isVisible()) || !(await locator.isEnabled())) throw new Error(`${label} is not visible and enabled`);
  };
  return diagnostics
    ? diagnostics.run("PLAYWRIGHT", "locator.visibility", check, { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.PLAYWRIGHT })
    : check();
}

async function requestCredentials(tab, origin, diagnostics) {
  const run = (phase, operation, work, options = {}) => diagnostics.run(phase, operation, work, options);
  await run("STAGING_NAVIGATION", "tab.goto_login", () => tab.goto(`${origin}/login`), {
    timeoutMs: TRUSTED_BROWSER_TIMEOUTS.STAGING_NAVIGATION,
  });
  await run("STAGING_NAVIGATION", "tab.visible_dom_login", () => tab.dom_cua.get_visible_dom(), {
    timeoutMs: TRUSTED_BROWSER_TIMEOUTS.DOM_INSPECTION,
  });
  const username = tab.playwright.locator("#login-username");
  const password = tab.playwright.locator("#login-password");
  const submit = tab.playwright.locator("#login-form button[type='submit']");
  await visibleAndEnabled(username, "manager username", diagnostics);
  await visibleAndEnabled(password, "manager password", diagnostics);
  await visibleAndEnabled(submit, "manager sign-in submit", diagnostics);
  const browserAuth = await run("AUTH_CAPABILITY", "browserAuth.get", () => tab.capabilities.get("browserAuth"), {
    timeoutMs: TRUSTED_BROWSER_TIMEOUTS.AUTH_CAPABILITY,
  });
  await run("AUTH_CAPABILITY", "browserAuth.validate", () => {
    if (!browserAuth || typeof browserAuth.request !== "function") {
      const error = new Error("approved browserAuth capability is unavailable");
      error.code = "TB_AUTH_CAPABILITY_MISSING";
      throw error;
    }
  }, { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.AUTH_CAPABILITY });
  const result = await run("AUTH_BRIDGE", "browserAuth.request", () => browserAuth.request({
    origin,
    fields: [
      { id: "username", label: "Email or username", type: "text", autocomplete: "username", required: true, selector: "#login-username" },
      { id: "password", label: "Password", type: "password", autocomplete: "current-password", required: true, selector: "#login-password" },
    ],
    submit: { selector: "#login-form button[type='submit']", action: "click" },
  }), { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.AUTH_BRIDGE });
  await run("AUTH_COMPLETE", "browserAuth.result", () => {
    if (result.status !== "submitted") throw new Error("secure manager authentication did not submit");
  }, { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.AUTH_COMPLETE });
  await run("AUTH_COMPLETE", "tab.visible_dom_authenticated", () => tab.dom_cua.get_visible_dom(), {
    timeoutMs: TRUSTED_BROWSER_TIMEOUTS.DOM_INSPECTION,
  });
  return record("manager_login_session", "SUBMITTED", "Secure browser authentication handoff submitted; session verification follows.");
}

async function pageJson(tab, path, { method = "GET", body = undefined, csrf = false, diagnostics = undefined } = {}) {
  if (!path.startsWith("/") || path.startsWith("//")) throw new Error("API path must be same-origin and relative");
  const request = () => tab.playwright.evaluate(async ({ path: requestPath, method: requestMethod, body: requestBody, csrfRequired }) => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10_000);
    const headers = { Accept: "application/json" };
    if (requestBody !== undefined) headers["Content-Type"] = "application/json";
    let csrfToken;
    if (csrfRequired) {
      const csrfResponse = await fetch("/api/auth/csrf", { credentials: "same-origin", signal: controller.signal });
      const csrfPayload = await csrfResponse.json().catch(() => ({}));
      csrfToken = csrfPayload.csrf_token;
      headers["X-CSRF-Token"] = csrfToken;
    }
    const response = await fetch(requestPath, {
      method: requestMethod,
      credentials: "same-origin",
      headers,
      signal: controller.signal,
      body: requestBody === undefined ? undefined : JSON.stringify(requestBody),
    });
    const payload = await response.json().catch(() => null);
    const strip = (value) => {
      if (value === null || typeof value !== "object") return value;
      if (Array.isArray(value)) return value.map(strip);
      const result = {};
      for (const [key, child] of Object.entries(value)) {
        if (["password", "password_hash", "activation_token", "csrf_token", "token", "cookie", "set-cookie", "authorization", "private_key", "secret"].includes(key.toLowerCase())) continue;
        result[key] = strip(child);
      }
      return result;
    };
    clearTimeout(timeout);
    return { status: response.status, body: strip(payload), contentType: response.headers.get("content-type") };
  }, { path, method, body, csrfRequired: csrf });
  return diagnostics
    ? diagnostics.run("APPLICATION_REQUEST", "page.same_origin_request", request, {
      timeoutMs: TRUSTED_BROWSER_TIMEOUTS.APPLICATION_REQUEST,
    })
    : request();
}

function expectStatus(result, expected, check, observation) {
  const allowed = Array.isArray(expected) ? expected : [expected];
  const pass = allowed.includes(result.status);
  return record(check, pass ? "PASS" : "FAIL", pass ? observation : `${observation}; observed HTTP ${result.status}`, { http_status: result.status, expected_status: allowed, response: result.body });
}

export async function verifyManagerSession(tab, { diagnostics = undefined } = {}) {
  const result = await pageJson(tab, "/api/auth/me", { diagnostics });
  const body = result.body ?? {};
  const role = typeof body.role === "string" ? body.role.toLowerCase() : "";
  const pass = result.status === 200 && MANAGER_ROLES.has(role);
  return record("manager_login_session", pass ? "PASS" : "FAIL", pass ? "Authenticated manager role confirmed" : "Authenticated manager role was not confirmed", { http_status: result.status, manager_role: role || "NOT_RECORDED" });
}

export async function verifyCsrf(tab, { diagnostics = undefined } = {}) {
  const result = await pageJson(tab, "/api/pilot-provisioning", { method: "POST", body: {}, csrf: false, diagnostics });
  return expectStatus(result, 403, "csrf_protection", "Missing CSRF on provisioning write is denied without provisioning state change");
}

export async function provisionSyntheticPilot(tab, { username, email, displayName, tenantName, expiresAt, approvedScenarios, activationExpiresAt, diagnostics = undefined } = {}) {
  for (const [name, value] of Object.entries({ username, email, displayName, tenantName, expiresAt, activationExpiresAt })) {
    if (typeof value !== "string" || value.length === 0) throw new Error(`missing non-secret provisioning field: ${name}`);
  }
  if (!Array.isArray(approvedScenarios) || approvedScenarios.length === 0 || approvedScenarios.some((item) => typeof item !== "string")) throw new Error("approvedScenarios must be a non-empty list of approved identifiers");
  const result = await pageJson(tab, "/api/pilot-provisioning", {
    method: "POST",
    csrf: true,
    body: { username, email, display_name: displayName, tenant_name: tenantName, expires_at: expiresAt, activation_expires_at: activationExpiresAt, approved_scenarios: approvedScenarios },
    diagnostics,
  });
  if (result.status !== 201) throw new Error(`synthetic pilot provisioning failed with HTTP ${result.status}`);
  const body = result.body ?? {};
  return scrub({
    provisioning_id: body.provisioning_id,
    tenant_id: body.tenant_id,
    analyst_id: body.analyst_id,
    authorization_id: body.authorization_id,
    account_status: body.account_status,
    authorization_status: body.authorization_status,
    activation_required: true,
  });
}

export async function runAnalystGates(tab, {
  runId,
  expectedTenantId,
  foreignTenantResourcePath,
  auditPath,
  provenancePath,
  aiVerificationPath,
  investigationCaseId,
  denialPaths = {},
  diagnostics = undefined,
} = {}) {
  const safeRunId = requireRunId(runId);
  if (typeof expectedTenantId !== "string" || !expectedTenantId) throw new Error("expectedTenantId is required");
  for (const [name, path] of Object.entries({ foreignTenantResourcePath, auditPath, provenancePath, aiVerificationPath })) {
    if (typeof path !== "string" || !path.startsWith("/")) throw new Error(`${name} must be an operator-supplied same-origin path`);
  }
  const results = [];
  const identity = await pageJson(tab, "/api/auth/me", { diagnostics });
  const identityBody = identity.body ?? {};
  const identityPass = identity.status === 200 && String(identityBody.role).toLowerCase() === "analyst" && identityBody.tenant_id === expectedTenantId;
  results.push(record("analyst_rbac", identityPass ? "PASS" : "FAIL", identityPass ? "Server-derived analyst role and tenant confirmed" : "Analyst role or tenant did not match expected scope", { http_status: identity.status, role: identityBody.role, tenant_id: identityBody.tenant_id }));

  const current = await pageJson(tab, "/api/pilot-authorizations/current", { diagnostics });
  results.push(expectStatus(current, 200, "analyst_tenant_scope", "Current pilot authorization is available to the analyst"));

  const missingCsrf = await pageJson(tab, "/api/investigations/jobs", { method: "POST", body: { case_id: `SAFE-DENY-${safeRunId}`, source: "pilot-runner", alert: { synthetic: true } }, csrf: false, diagnostics });
  results.push(expectStatus(missingCsrf, 403, "csrf_protection", "Synthetic write without CSRF is denied"));

  const syntheticJob = await pageJson(tab, "/api/investigations/jobs", { method: "POST", csrf: true, body: { case_id: investigationCaseId || `PILOT-SYNTHETIC-${safeRunId}`, source: "pilot-runner", alert: { id: `synthetic-alert-${safeRunId}`, synthetic: true, event_type: "suspicious_authentication", severity: "low" } }, diagnostics });
  results.push(expectStatus(syntheticJob, [200, 202], "synthetic_investigation_workflow", "Synthetic investigation intake accepted through the pilot surface"));

  const foreign = await pageJson(tab, foreignTenantResourcePath, { diagnostics });
  results.push(expectStatus(foreign, [403, 404], "analyst_tenant_scope", "Foreign-tenant resource is denied or indistinguishable from not found"));

  const audit = await pageJson(tab, auditPath, { diagnostics });
  results.push(expectStatus(audit, 200, "audit_event_generation", "Tenant-scoped audit evidence is readable"));
  const provenance = await pageJson(tab, provenancePath, { diagnostics });
  results.push(expectStatus(provenance, 200, "evidence_provenance", "Tenant-scoped provenance evidence is readable"));
  const ai = await pageJson(tab, aiVerificationPath, { diagnostics });
  const aiBody = ai.body ?? {};
  const advisory = ai.status === 200 && (aiBody.advisory_only === true || aiBody.advisory === true) && (aiBody.requires_human_review === true || aiBody.human_decision_required === true);
  results.push(record("ai_advisory_only", advisory ? "PASS" : "FAIL", advisory ? "AI output is marked advisory and requires human review" : "AI advisory-only and human-review markers were not both observed", { http_status: ai.status, advisory_only: aiBody.advisory_only, requires_human_review: aiBody.requires_human_review }));

  const defaults = {
    deny_admin: ["/api/pilot-provisioning", "/api/pilot-authorizations"],
  };
  const requiredDenialGates = ["deny_database", "deny_shell_container", "deny_destructive"];
  for (const gate of requiredDenialGates) {
    if (!Array.isArray(denialPaths[gate]) || denialPaths[gate].length === 0) {
      throw new Error(`${gate} requires operator-supplied paths from the current deployment contract`);
    }
  }
  for (const [gate, paths] of Object.entries({ ...defaults, ...denialPaths })) {
    for (const path of paths) {
      const denied = await pageJson(tab, path, { diagnostics });
      results.push(expectStatus(denied, 403, gate, `Analyst access to ${path} is explicitly denied`));
    }
  }
  return results;
}

async function writeAppendOnlyEvidence(evidenceDir, runId, payload) {
  const clean = scrub(payload);
  assertNoSecrets(clean);
  const canonical = JSON.stringify(clean);
  const digest = createHash("sha256").update(canonical, "utf8").digest("hex");
  const finalPayload = { ...clean, sha256: digest };
  const filename = `controlled-analyst-pilot-${runId}.json`;
  const path = join(evidenceDir, filename);
  await mkdir(evidenceDir, { recursive: true });
  await writeFile(path, `${JSON.stringify(finalPayload, null, 2)}\n`, { encoding: "utf8", flag: "wx" });
  return { path, sha256: createHash("sha256").update(JSON.stringify(finalPayload, null, 2) + "\n", "utf8").digest("hex") };
}

export async function runControlledAnalystPilot({
  browser,
  origin = DEFAULT_ORIGIN,
  runId,
  evidenceDir = DEFAULT_EVIDENCE_DIR,
  allowProvisioning = false,
  provisioning = undefined,
  analyst = undefined,
} = {}) {
  if (!browser || typeof browser.tabs?.new !== "function") throw new Error("approved trusted browser object is required");
  const safeOrigin = validateOrigin(origin);
  const safeRunId = requireRunId(runId);
  const started = new Date().toISOString();
  const results = [];
  const diagnostics = createTrustedBrowserDiagnostics();
  let managerTab;
  let provisioningResult = null;
  let executionFailure;
  try {
    managerTab = await diagnostics.run(
      "BROWSER_CREATE",
      "manager_tab.new",
      () => browser.tabs.new(),
      { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.BROWSER_CREATE },
    );
    results.push(await requestCredentials(managerTab, safeOrigin, diagnostics));
    results.push(await verifyManagerSession(managerTab, { diagnostics }));
    results.push(await verifyCsrf(managerTab, { diagnostics }));

    if (allowProvisioning) {
      if (!provisioning) throw new Error("explicit provisioning arguments are required when allowProvisioning=true");
      provisioningResult = await provisionSyntheticPilot(managerTab, { ...provisioning, diagnostics });
    } else {
      results.push(record("pilot_provisioning", "NOT_PERFORMED", "Provisioning disabled for preparation run"));
    }

    if (analyst?.tab) {
      results.push(...await runAnalystGates(analyst.tab, { ...analyst, runId: safeRunId, diagnostics }));
    } else {
      results.push(record("authenticated_analyst_gates", "NOT_MEASURED", "No activated analyst tab supplied; no analyst account was created by this run"));
    }
  } catch (error) {
    const failureCategory = safeTrustedBrowserCode(error);
    executionFailure = failureCategory;
    results.push(record(
      "trusted_browser_execution",
      "FAIL",
      "Trusted browser operation did not complete",
      { failure_category: failureCategory },
    ));
  } finally {
    if (managerTab && typeof managerTab.close === "function") {
      try {
        await diagnostics.run(
          "TAB_CLOSE",
          "manager_tab.close",
          () => managerTab.close(),
          { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.TAB_CLOSE },
        );
      } catch (error) {
        const failureCategory = safeTrustedBrowserCode(error, "TB_TAB_CLOSE");
        results.push(record(
          "tab_resource_lifecycle",
          "FAIL",
          "Trusted browser tab did not close within the bounded cleanup window",
          { failure_category: failureCategory },
        ));
      }
    }
    if (typeof browser.close === "function") {
      try {
        await diagnostics.run(
          "TAB_CLOSE",
          "browser.close",
          () => browser.close(),
          { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.TAB_CLOSE },
        );
      } catch (error) {
        results.push(record(
          "browser_resource_lifecycle",
          "FAIL",
          "Trusted browser did not close within the bounded cleanup window",
          { failure_category: safeTrustedBrowserCode(error, "TB_TAB_CLOSE") },
        ));
      }
    }
  }

  const failed = results.filter((item) => item.status === "FAIL").length;
  const notMeasured = results.filter((item) => ["NOT_MEASURED", "NOT_PERFORMED"].includes(item.status)).length;
  const status = failed || notMeasured ? "BLOCKED_WITH_REASON" : "READY_FOR_CONTROLLED_ANALYST_PILOT";
  const evidence = await writeAppendOnlyEvidence(evidenceDir, safeRunId, {
    schema_version: "1.0",
    generated_at_utc: new Date().toISOString(),
    run_id: safeRunId,
    status,
    origin: safeOrigin,
    started_at_utc: started,
    completed_at_utc: new Date().toISOString(),
    results,
    diagnostics: diagnostics.snapshot(),
    provisioning: provisioningResult ? { ...provisioningResult, activation_token_recorded: false } : { status: "NOT_PERFORMED" },
    controls: { synthetic_data_only: true, customer_data: false, credentials_or_tokens: false, production_impact: false, public_exposure: false, human_decision_authority: true, ai_advisory_only_required: true },
    blockers: executionFailure
      ? [executionFailure]
      : failed
        ? ["One or more authenticated checks failed"]
        : notMeasured
          ? ["One or more authenticated checks were not measured"]
          : [],
  });
  return { status, evidence, results, provisioning: provisioningResult };
}

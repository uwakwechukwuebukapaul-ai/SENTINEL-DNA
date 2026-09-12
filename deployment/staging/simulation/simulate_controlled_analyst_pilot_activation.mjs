/**
 * NON-PRODUCTION controlled analyst pilot activation simulation.
 *
 * This module demonstrates the blocked-to-simulation-ready lifecycle without
 * loading the production provider, opening a network listener, authenticating,
 * or invoking browserAuth. Its synthetic runtime is deliberately scoped to
 * this simulation package and is never registered with production settings.
 */

import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import {
  checkControlledPilotReadiness,
} from "../scripts/check_controlled_pilot_readiness.mjs";
import {
  createTrustedRuntimeProvider,
  TRUSTED_BROWSER_ENVIRONMENT,
} from "../scripts/trusted_browser_service/runtime-provider.mjs";
import {
  CERTIFIED_STAGING_ORIGIN,
} from "../scripts/trusted_browser_activation_manifest.mjs";
import {
  generateSimulationActivationManifest,
  SIMULATION_IMAGE_DIGEST,
  SIMULATION_MODE,
  SIMULATION_OUTPUT_DIRECTORY,
} from "./generate_simulation_activation_manifest.mjs";
import {
  isSyntheticCertifiedOriginReachable,
  syntheticEndpointEvidence,
} from "./fixtures/synthetic-certified-staging-endpoint.mjs";

const SCRIPT_DIRECTORY = dirname(fileURLToPath(import.meta.url));
const TENANT_FIXTURE = join(SCRIPT_DIRECTORY, "fixtures", "tenant-isolation-evidence.json");
const AUDIT_FIXTURE = join(SCRIPT_DIRECTORY, "fixtures", "audit-evidence.json");
const INITIAL_BLOCKED_CODES = Object.freeze([
  "TB_PROVIDER_NOT_CONFIGURED",
  "TB_PROVIDER_MODULE_MISSING",
  "TB_PROVIDER_MANIFEST_MISSING",
  "TB_ORIGIN_UNREACHABLE",
  "TB_SECURITY_CONTROL_MISSING",
]);
const REQUIRED_ENVIRONMENT_KEYS = [
  "SENTINEL_DNA_TRUSTED_BROWSER_CLIENT",
  "SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT",
  "SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME",
  "SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST",
  "SENTINEL_DNA_IMAGE_DIGEST",
  "SENTINEL_DNA_ENV",
  "SENTINEL_DNA_PILOT_ACCESS_REQUIRED",
  "SENTINEL_DNA_SECURE_COOKIES",
  "FLASK_DEBUG",
  "SENTINEL_DNA_TENANT_ISOLATION_ENABLED",
  "SENTINEL_DNA_AUDIT_LOGGING_ENABLED",
];

function simulationError(code) {
  const error = new Error(`[${code}] simulation is unavailable`);
  error.code = code;
  return error;
}

function assertSimulationMode(enabled) {
  if (enabled !== true || process.env?.SENTINEL_DNA_SIMULATION_MODE !== "1") {
    throw simulationError("TB_SIMULATION_MODE_REQUIRED");
  }
}

function result(name, status, reason) {
  return { name, status, reason };
}

function createSimulationTab() {
  return {
    goto: async () => undefined,
    close: async () => undefined,
    playwright: {
      locator: () => ({ simulation_only: true }),
      evaluate: async () => ({ simulation_only: true }),
    },
    dom_cua: {
      get_visible_dom: async () => ({ simulation_only: true }),
    },
    capabilities: {
      get: async (name) => name === "browserAuth"
        ? { request: async () => ({ status: "SIMULATION_ONLY" }) }
        : undefined,
    },
  };
}

function createSimulationExternalProvider() {
  const browser = {
    tabs: {
      new: async () => createSimulationTab(),
    },
  };
  return {
    setupBrowserRuntime: async ({ environment } = {}) => {
      if (environment !== TRUSTED_BROWSER_ENVIRONMENT) {
        throw simulationError("TB_RUNTIME_UNAVAILABLE");
      }
      return {
        browsers: {
          getForUrl: async (origin) => {
            if (origin !== CERTIFIED_STAGING_ORIGIN) {
              throw simulationError("TB_ORIGIN_REJECTED");
            }
            return browser;
          },
        },
      };
    },
  };
}

async function verifySimulationProvider() {
  const checks = {
    provider: "NOT_RUN",
    runtime: "NOT_RUN",
    origin: "NOT_RUN",
    browser_contract: "NOT_RUN",
    browser_auth: "NOT_RUN",
  };
  let tab;
  try {
    const provider = createTrustedRuntimeProvider(createSimulationExternalProvider());
    const runtime = await provider.setupBrowserRuntime({ environment: TRUSTED_BROWSER_ENVIRONMENT });
    if (!runtime?.browsers || typeof runtime.browsers.getForUrl !== "function") {
      throw simulationError("TB_RUNTIME_UNAVAILABLE");
    }
    checks.provider = "PASS";
    checks.runtime = "PASS";
    const browser = await runtime.browsers.getForUrl(CERTIFIED_STAGING_ORIGIN);
    checks.origin = "PASS";
    if (!browser || typeof browser.tabs?.new !== "function") {
      throw simulationError("TB_BROWSER_CONTRACT_FAILED");
    }
    tab = await browser.tabs.new();
    if (
      !tab ||
      typeof tab.goto !== "function" ||
      typeof tab.playwright?.locator !== "function" ||
      typeof tab.playwright?.evaluate !== "function" ||
      typeof tab.dom_cua?.get_visible_dom !== "function" ||
      typeof tab.capabilities?.get !== "function"
    ) {
      throw simulationError("TB_BROWSER_CONTRACT_FAILED");
    }
    checks.browser_contract = "PASS";
    const browserAuth = await tab.capabilities.get("browserAuth");
    if (!browserAuth || typeof browserAuth.request !== "function") {
      throw simulationError("TB_AUTH_CAPABILITY_MISSING");
    }
    checks.browser_auth = "PASS";
    return { status: "PASS", checks };
  } catch (error) {
    const code = /^TB_[A-Z0-9_]+$/.test(error?.code || "")
      ? error.code
      : "TB_RUNTIME_UNAVAILABLE";
    return { status: "BLOCKED_WITH_REASON", checks, failure_category: code };
  } finally {
    if (tab && typeof tab.close === "function") await tab.close().catch(() => {});
  }
}

const SECRET_KEYS = new Set([
  "password",
  "secret",
  "token",
  "cookie",
  "authorization",
  "credential",
  "private_key",
  "session",
]);

function assertSecretFreeFixture(value) {
  if (value === null || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) {
    if (SECRET_KEYS.has(key.toLowerCase())) throw simulationError("TB_SIMULATION_FIXTURE_INVALID");
    assertSecretFreeFixture(child);
  }
}

async function readSimulationFixture(source, requiredFields) {
  let value;
  try {
    value = JSON.parse(await readFile(source, "utf8"));
  } catch {
    throw simulationError("TB_SIMULATION_FIXTURE_INVALID");
  }
  assertSecretFreeFixture(value);
  if (
    value.mode !== SIMULATION_MODE ||
    value.status !== "PASS" ||
    requiredFields.some(([field, expected]) => value[field] !== expected)
  ) {
    throw simulationError("TB_SIMULATION_FIXTURE_INVALID");
  }
  return Object.freeze({ status: "PASS", evidence_reference: value.evidence_reference });
}

function byName(checks, name) {
  return checks.find((check) => check.name === name);
}

function safeCodes(checks) {
  return [...new Set(checks
    .map((check) => check.reason)
    .filter((reason) => /^TB_[A-Z0-9_]+$/.test(reason)))];
}

function simulationReport({ readiness, providerVerification, tenantEvidence, auditEvidence }) {
  const readinessChecks = readiness.checks;
  const checks = [
    result(
      "provider_configured",
      byName(readinessChecks, "provider_configured")?.status === "PASS" ? "PASS" : "BLOCKED",
      byName(readinessChecks, "provider_configured")?.status === "PASS"
        ? "simulation provider registration is present"
        : "TB_PROVIDER_NOT_CONFIGURED",
    ),
    result(
      "runtime_reachable",
      providerVerification.checks.runtime === "PASS" ? "PASS" : "BLOCKED",
      providerVerification.checks.runtime === "PASS" ? "simulation runtime setup completed" : providerVerification.failure_category,
    ),
    result(
      "browser_contract_valid",
      providerVerification.checks.browser_contract === "PASS" ? "PASS" : "BLOCKED",
      providerVerification.checks.browser_contract === "PASS" ? "simulation browser contract is valid" : providerVerification.failure_category,
    ),
    result(
      "origin_reachable",
      byName(readinessChecks, "certified_origin")?.status === "PASS" ? "PASS" : "BLOCKED",
      byName(readinessChecks, "certified_origin")?.status === "PASS" ? "synthetic certified origin is available" : "TB_ORIGIN_UNREACHABLE",
    ),
    result(
      "browser_auth_available",
      providerVerification.checks.browser_auth === "PASS" ? "PASS" : "BLOCKED",
      providerVerification.checks.browser_auth === "PASS" ? "synthetic browserAuth capability is present" : "TB_AUTH_CAPABILITY_MISSING",
    ),
    result(
      "tenant_isolation_evidence",
      tenantEvidence.status === "PASS" ? "PASS" : "BLOCKED",
      tenantEvidence.status === "PASS" ? "synthetic tenant-isolation evidence is valid" : "TB_SIMULATION_FIXTURE_INVALID",
    ),
    result(
      "audit_logging_evidence",
      auditEvidence.status === "PASS" ? "PASS" : "BLOCKED",
      auditEvidence.status === "PASS" ? "synthetic audit evidence is valid" : "TB_SIMULATION_FIXTURE_INVALID",
    ),
    result(
      "analyst_access_approval_workflow",
      "SIMULATION_ONLY",
      "synthetic approval workflow demonstrated; production approval is required",
    ),
  ];
  const blocked = checks.find((check) => check.status === "BLOCKED") ||
    readinessChecks.find((check) => check.status !== "PASS");
  const finalStatus = blocked ? "BLOCKED_WITH_REASON" : "SIMULATION_READY_FOR_ANALYST_PILOT";
  return {
    schema_version: "1.0-simulation",
    mode: SIMULATION_MODE,
    simulation_only: true,
    production_authorization: false,
    status: finalStatus,
    manifest_status: byName(readinessChecks, "activation_manifest")?.status || "BLOCKED",
    provider_status: providerVerification.status === "PASS" ? "PASS" : "BLOCKED",
    image_digest_status: byName(readinessChecks, "image_digest")?.status || "BLOCKED",
    origin_status: byName(readinessChecks, "certified_origin")?.status || "BLOCKED",
    tenant_isolation_status: tenantEvidence.status,
    audit_status: auditEvidence.status,
    final_readiness_decision: finalStatus,
    checks,
    evidence: {
      endpoint: syntheticEndpointEvidence,
      tenant_isolation: tenantEvidence,
      audit_logging: auditEvidence,
      analyst_access_approval: {
        status: "SIMULATION_ONLY",
        human_approval_required: true,
        production_authorization: false,
      },
    },
    blocked_phase: {
      status: "BLOCKED_WITH_REASON",
      codes: [
        "TB_PROVIDER_NOT_CONFIGURED",
        "TB_PROVIDER_MODULE_MISSING",
        "TB_PROVIDER_MANIFEST_MISSING",
        "TB_ORIGIN_UNREACHABLE",
        "TB_SECURITY_CONTROL_MISSING",
      ],
    },
    simulation_phase: {
      status: finalStatus,
      codes: blocked ? safeCodes(checks) : [],
    },
  };
}

async function withSimulationEnvironment(manifestPath, callback) {
  const previous = new Map(REQUIRED_ENVIRONMENT_KEYS.map((key) => [key, process.env[key]]));
  const values = {
    SENTINEL_DNA_TRUSTED_BROWSER_CLIENT: "NON-PRODUCTION_SIMULATION_ONLY",
    SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT: "NON-PRODUCTION_SIMULATION_ONLY",
    SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME: "NON-PRODUCTION_SIMULATION_ONLY",
    SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST: manifestPath,
    SENTINEL_DNA_IMAGE_DIGEST: SIMULATION_IMAGE_DIGEST,
    SENTINEL_DNA_ENV: "staging",
    SENTINEL_DNA_PILOT_ACCESS_REQUIRED: "1",
    SENTINEL_DNA_SECURE_COOKIES: "1",
    FLASK_DEBUG: "0",
    SENTINEL_DNA_TENANT_ISOLATION_ENABLED: "1",
    SENTINEL_DNA_AUDIT_LOGGING_ENABLED: "1",
  };
  try {
    for (const [key, value] of Object.entries(values)) process.env[key] = value;
    return await callback();
  } finally {
    for (const [key, value] of previous) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
}

export async function simulateControlledAnalystPilotActivation({
  outputDirectory = SIMULATION_OUTPUT_DIRECTORY,
  simulationMode = false,
} = {}) {
  assertSimulationMode(simulationMode);
  const runName = `run-${new Date().toISOString().replace(/[-:.]/g, "").replace(/Z$/, "Z")}`;
  const runDirectory = resolve(outputDirectory, runName);
  await mkdir(runDirectory, { recursive: true });

  const blockedReadiness = await withSimulationEnvironment(undefined, async () => {
    for (const key of REQUIRED_ENVIRONMENT_KEYS) delete process.env[key];
    return checkControlledPilotReadiness({
      evidenceDir: runDirectory,
      originReachability: async () => false,
      providerVerification: {
        status: "BLOCKED_WITH_REASON",
        checks: { provider: "FAIL", runtime: "NOT_RUN", origin: "NOT_RUN", browser_contract: "NOT_RUN", browser_auth: "NOT_RUN" },
        failure_category: "TB_PROVIDER_NOT_CONFIGURED",
      },
    });
  });

  const manifest = await generateSimulationActivationManifest({
    outputDirectory: runDirectory,
    simulationMode: true,
  });
  const tenantEvidence = await readSimulationFixture(TENANT_FIXTURE, [
    ["synthetic_data_only", true],
    ["synthetic_tenant_count", 1],
    ["synthetic_analyst_count", 1],
    ["server_derived_scope", "PASS"],
    ["foreign_tenant_denied", "PASS"],
    ["privileged_actions_denied", "PASS"],
    ["production_data_used", false],
  ]);
  const auditEvidence = await readSimulationFixture(AUDIT_FIXTURE, [
    ["audit_logging_enabled", true],
    ["tenant_scoped", true],
    ["all_sensitive_actions_audited", true],
  ]);
  const providerVerification = await verifySimulationProvider();
  const readyReadiness = await withSimulationEnvironment(
    join(runDirectory, manifest.manifest_file),
    () => checkControlledPilotReadiness({
      evidenceDir: runDirectory,
      originReachability: async (origin) => isSyntheticCertifiedOriginReachable(origin),
      providerVerification,
    }),
  );
  const report = simulationReport({
    readiness: readyReadiness,
    providerVerification,
    tenantEvidence,
    auditEvidence,
  });
  report.initial_readiness_status = blockedReadiness.status;
  report.initial_blocked_codes = INITIAL_BLOCKED_CODES;
  report.artifacts = {
    manifest_file: manifest.manifest_file,
    signature_file: manifest.signature_file,
    tenant_evidence_file: "fixtures/tenant-isolation-evidence.json",
    audit_evidence_file: "fixtures/audit-evidence.json",
    readiness_report_file: "controlled-pilot-readiness.simulation.json",
  };
  await writeFile(
    join(runDirectory, report.artifacts.readiness_report_file),
    `${JSON.stringify(report, null, 2)}\n`,
    { encoding: "utf8", flag: "wx" },
  );
  return Object.freeze(report);
}

const invokedAsMain = process.argv[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (invokedAsMain) {
  try {
    const report = await simulateControlledAnalystPilotActivation({
      simulationMode: process.argv.includes("--non-production-simulation"),
    });
    console.log(JSON.stringify(report, null, 2));
    process.exitCode = report.status === "SIMULATION_READY_FOR_ANALYST_PILOT" ? 0 : 1;
  } catch (error) {
    console.log(JSON.stringify({
      mode: SIMULATION_MODE,
      simulation_only: true,
      production_authorization: false,
      status: "BLOCKED_WITH_REASON",
      code: error?.code || "TB_SIMULATION_UNAVAILABLE",
    }, null, 2));
    process.exitCode = 1;
  }
}

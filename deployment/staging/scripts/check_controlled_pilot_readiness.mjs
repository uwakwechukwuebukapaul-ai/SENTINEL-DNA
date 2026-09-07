/**
 * Read-only, fail-closed readiness gate for the controlled analyst pilot.
 *
 * This command checks deployment identity, the configured reviewed browser
 * provider, pilot filesystem prerequisites, certified-origin reachability,
 * and explicit staging security assertions. It does not create evidence,
 * authenticate, navigate, or request browserAuth credentials.
 */

import { constants, existsSync, readFileSync } from "node:fs";
import { access } from "node:fs/promises";
import https from "node:https";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

import {
  SERVICE_KEY_ENV as TRUSTED_BROWSER_SERVICE_KEY_ENV,
  SERVICE_HOST_ENV as TRUSTED_BROWSER_SERVICE_HOST_ENV,
  SERVICE_PORT_ENV as TRUSTED_BROWSER_SERVICE_PORT_ENV,
} from "../trusted_browser_runtime/rpc-client.mjs";
import { configuredCertifiedOrigin } from "./trusted_browser_service/policy/origin-policy.mjs";
import {
  loadActivationManifest,
} from "./trusted_browser_activation_manifest.mjs";
import {
  verifyConfiguredRuntimeDigest,
} from "./verify_gate4_external_artifacts.mjs";
const DEFAULT_EVIDENCE_DIR = "C:/ProgramData/Sentinel-DNA/release/evidence";
const STAGING_TLS_CA_FILE_ENV = "SENTINEL_DNA_STAGING_TLS_CA_FILE";
const STAGING_TLS_DIR_ENV = "SENTINEL_DNA_STAGING_TLS_DIR";
const TRUSTED_BROWSER_CLIENT_ENV = "SENTINEL_DNA_TRUSTED_BROWSER_CLIENT";
const TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV = "SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT";
const APPROVED_PLAYWRIGHT_RUNTIME_ENV = "SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME";
export const READINESS_READY_STATUS = "READY_FOR_ANALYST_PILOT";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const SAFE_FAILURE_CODES = new Set([
  "TB_PROVIDER_NOT_CONFIGURED",
  "TB_PROVIDER_MODULE_MISSING",
  "TB_PROVIDER_EXPORT_INVALID",
  "TB_RUNTIME_UNAVAILABLE",
  "TB_BROWSER_SELECTION_FAILED",
  "TB_BROWSER_CONTRACT_FAILED",
  "TB_AUTH_CAPABILITY_MISSING",
  "TB_AUTH_BRIDGE_MISSING",
  "TB_AUTH_BRIDGE_EXPORT_INVALID",
  "TB_AUTH_BRIDGE_RUNTIME_FAILED",
  "TB_ORIGIN_REJECTED",
  "TB_PROVIDER_MANIFEST_MISSING",
  "TB_PROVIDER_MANIFEST_INVALID",
  "TB_ORIGIN_UNREACHABLE",
  "TB_PROVIDER_LOAD_TIMEOUT",
  "TB_RUNTIME_SETUP_TIMEOUT",
  "TB_BROWSER_SELECTION_TIMEOUT",
  "TB_BROWSER_CREATE_TIMEOUT",
  "TB_STAGING_NAVIGATION_TIMEOUT",
  "TB_AUTH_CAPABILITY_TIMEOUT",
  "TB_AUTH_BRIDGE_TIMEOUT",
  "TB_AUTH_COMPLETE_TIMEOUT",
  "TB_TAB_CLOSE_TIMEOUT",
]);

const BLOCKED_CONTEXT = Object.freeze({
  image_digest: {
    owner: "release/build operator",
    required_action: "provide the immutable candidate-bound image digest through external custody",
    evidence_required: "image reference, sha256 digest, build provenance, commit/tree binding, and custody reference",
  },
  staging_environment: {
    owner: "staging operator",
    required_action: "configure the approved staging environment with external values",
    evidence_required: "environment identity, service health, isolation, and deployment inspection",
  },
  activation_manifest: {
    owner: "release/security owner",
    required_action: "provide and verify the external activation manifest",
    evidence_required: "candidate-bound manifest digest, scope, expiry, rollback, and approval references",
  },
  provider_configured: {
    owner: "trusted-browser operator",
    required_action: "configure the approved trusted-browser provider outside Git",
    evidence_required: "provider identity, runtime identity, browserAuth capability, and custody references",
  },
  provider_verification: {
    owner: "trusted-browser operator",
    required_action: "verify the approved provider and runtime through the reviewed mechanism",
    evidence_required: "provider verification result and safe failure category or immutable runtime references",
  },
  evidence_directory: {
    owner: "staging operator",
    required_action: "provide the approved externally controlled evidence directory",
    evidence_required: "writable custody location and retention/reference metadata",
  },
  validation_scripts: {
    owner: "release engineer",
    required_action: "restore the repository-defined validation scripts or stop",
    evidence_required: "script presence and integrity verification",
  },
  certified_origin: {
    owner: "network/release operator",
    required_action: "establish the approved private origin and run CA/SNI-verified reachability checks",
    evidence_required: "DNS, TLS, /ready response, origin, and private-boundary references",
  },
  secure_cookies: {
    owner: "staging operator",
    required_action: "inject the approved staging security configuration with secure cookies enabled",
    evidence_required: "effective runtime configuration and cookie security observation",
  },
  debug_disabled: {
    owner: "staging operator",
    required_action: "run staging with debug mode disabled",
    evidence_required: "effective runtime configuration and startup inspection",
  },
  pilot_access_gate: {
    owner: "staging operator",
    required_action: "enable the controlled pilot access gate",
    evidence_required: "effective runtime configuration and access-boundary observation",
  },
  tenant_isolation: {
    owner: "staging/security operator",
    required_action: "enable tenant isolation and verify it in the live staging runtime",
    evidence_required: "direct foreign-tenant denial with no leakage",
  },
  audit_logging: {
    owner: "staging/security operator",
    required_action: "enable audit logging and verify the audit sink",
    evidence_required: "actor/role/tenant/action/correlation/time audit references and integrity linkage",
  },
});

function result(name, status, reason) {
  const context = status === "BLOCKED" ? BLOCKED_CONTEXT[name] : undefined;
  return context ? { name, status, reason, ...context } : { name, status, reason };
}

function hasValue(name) {
  return typeof process.env?.[name] === "string" && process.env[name].trim().length > 0;
}

function safeFailureCode(value) {
  return SAFE_FAILURE_CODES.has(value) ? value : "TB_RUNTIME_UNAVAILABLE";
}

function isValidImageDigest(value) {
  return typeof value === "string" && /^sha256:[0-9a-f]{64}$/i.test(value.trim());
}

function configuredStagingCaFile() {
  const configuredCaFile = process.env?.[STAGING_TLS_CA_FILE_ENV]?.trim();
  if (configuredCaFile) return configuredCaFile;

  const configuredTlsDirectory = process.env?.[STAGING_TLS_DIR_ENV]?.trim();
  return configuredTlsDirectory
    ? join(configuredTlsDirectory, "staging-ca.crt")
    : undefined;
}

async function isWritableDirectory(directory) {
  try {
    await access(directory, constants.W_OK);
    return true;
  } catch {
    return false;
  }
}

function certifiedOriginReachable(origin) {
  let parsed;
  try {
    parsed = new URL(origin);
  } catch {
    return Promise.resolve(false);
  }

  const caFile = configuredStagingCaFile();
  if (!caFile) return Promise.resolve(false);

  let ca;
  try {
    ca = readFileSync(caFile);
  } catch {
    return Promise.resolve(false);
  }

  return new Promise((resolve) => {
    const request = https.request({
      protocol: parsed.protocol,
      hostname: parsed.hostname,
      port: parsed.port,
      servername: parsed.hostname,
      path: "/ready",
      method: "GET",
      ca,
      rejectUnauthorized: true,
      timeout: 5000,
    }, (response) => {
      response.resume();
      resolve(Number.isInteger(response.statusCode));
    });
    request.once("error", () => resolve(false));
    request.once("timeout", () => request.destroy());
    request.end();
  });
}

async function providerConfigured(requireRpc = false) {
  if (requireRpc) return hasValue(TRUSTED_BROWSER_SERVICE_KEY_ENV) && hasValue(TRUSTED_BROWSER_SERVICE_HOST_ENV) && hasValue(TRUSTED_BROWSER_SERVICE_PORT_ENV);
  return hasValue(TRUSTED_BROWSER_CLIENT_ENV) &&
    hasValue(TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV) &&
    hasValue(APPROVED_PLAYWRIGHT_RUNTIME_ENV);
}

async function checkProvider(providerVerification, requireRpc = false) {
  if (!(await providerConfigured(requireRpc))) {
    return result("provider_configured", "BLOCKED", "required trusted browser provider configuration is missing");
  }

  if (requireRpc) {
    return result("rpc_configured", "PASS", "authenticated trusted-browser RPC configuration is present");
  }

  let verification;
  try {
    if (providerVerification) verification = providerVerification;
    else verification = await (await import("./verify_trusted_browser_provider.mjs")).verifyTrustedBrowserProvider();
  } catch {
    return result("provider_verification", "BLOCKED", "TB_RUNTIME_UNAVAILABLE");
  }
  if (verification.status !== "PASS") {
    return result(
      "provider_verification",
      "BLOCKED",
      safeFailureCode(verification.failure_category),
    );
  }
  return result("provider_verification", "PASS", "reviewed trusted browser provider verified");
}

export async function checkControlledPilotReadiness({
  evidenceDir = DEFAULT_EVIDENCE_DIR,
  originReachability = certifiedOriginReachable,
  providerVerification = undefined,
  requireRpc = false,
} = {}) {
  const checks = [];
  checks.push(result(
    "image_digest",
    isValidImageDigest(process.env?.SENTINEL_DNA_IMAGE_DIGEST) ? "PASS" : "BLOCKED",
    isValidImageDigest(process.env?.SENTINEL_DNA_IMAGE_DIGEST)
      ? "reviewed image digest is present"
      : "SENTINEL_DNA_IMAGE_DIGEST is missing or invalid",
  ));
  checks.push(result(
    "staging_environment",
    process.env?.SENTINEL_DNA_ENV === "staging" ? "PASS" : "BLOCKED",
    process.env?.SENTINEL_DNA_ENV === "staging"
      ? "staging environment confirmed"
      : "SENTINEL_DNA_ENV must be staging",
  ));

  try {
    const activationManifest = await loadActivationManifest();
    const configuredDigest = process.env?.SENTINEL_DNA_IMAGE_DIGEST?.trim();
    if (isValidImageDigest(configuredDigest) &&
        activationManifest.approved_image_runtime_digest.toLowerCase() !== configuredDigest.toLowerCase()) {
      throw new Error("activation manifest image identity does not match the configured image identity");
    }
    const simulationOnly = process.env?.SENTINEL_DNA_SIMULATION_MODE === "1" &&
      process.env?.SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME === "NON-PRODUCTION_SIMULATION_ONLY";
    if (!simulationOnly) {
      const runtimeDigest = await verifyConfiguredRuntimeDigest(activationManifest, {
        requireOperatorDigest: true,
      });
      if (runtimeDigest.status !== "PASS") {
        const error = new Error("configured runtime digest does not match the activation manifest");
        error.code = runtimeDigest.code;
        throw error;
      }
    }
    checks.push(result("activation_manifest", "PASS", "activation manifest integrity and origin are valid"));
  } catch (error) {
    const code = SAFE_FAILURE_CODES.has(error?.code) ? error.code : "TB_PROVIDER_MANIFEST_INVALID";
    checks.push(result("activation_manifest", "BLOCKED", code));
  }

  const configured = await providerConfigured(requireRpc);
  checks.push(result(
    "provider_configured",
    configured ? "PASS" : "BLOCKED",
    configured
      ? "trusted browser provider configuration is present"
      : "required trusted browser provider configuration is missing",
  ));
  if (configured) checks.push(await checkProvider(providerVerification, requireRpc));
  else checks.push(result("provider_verification", "BLOCKED", "TB_PROVIDER_NOT_CONFIGURED"));

  const evidenceWritable = await isWritableDirectory(evidenceDir);
  checks.push(result(
    "evidence_directory",
    evidenceWritable ? "PASS" : "BLOCKED",
    evidenceWritable
      ? "evidence directory is writable"
      : "evidence directory is missing or not writable",
  ));
  const requiredScripts = [
    "validate_manual_analyst_pilot_evidence.mjs",
    "verify_trusted_browser_provider.mjs",
    "run_controlled_analyst_pilot.mjs",
  ];
  const scriptsAvailable = requiredScripts.every((name) => existsSync(join(SCRIPT_DIR, name)));
  checks.push(result(
    "validation_scripts",
    scriptsAvailable ? "PASS" : "BLOCKED",
    scriptsAvailable ? "pilot validation scripts are available" : "required pilot validation script is missing",
  ));

  let originPass = false;
  try {
    originPass = await originReachability(configuredCertifiedOrigin());
  } catch {
    originPass = false;
  }
  checks.push(result(
    "certified_origin",
    originPass ? "PASS" : "BLOCKED",
    originPass ? "certified staging origin is reachable" : "TB_ORIGIN_UNREACHABLE",
  ));

  const securityControls = [
    ["secure_cookies", "SENTINEL_DNA_SECURE_COOKIES", "1", "secure cookies are enabled"],
    ["debug_disabled", "FLASK_DEBUG", "0", "debug mode is disabled"],
    ["pilot_access_gate", "SENTINEL_DNA_PILOT_ACCESS_REQUIRED", "1", "pilot access gate is enabled"],
    ["tenant_isolation", "SENTINEL_DNA_TENANT_ISOLATION_ENABLED", "1", "tenant isolation is enabled"],
    ["audit_logging", "SENTINEL_DNA_AUDIT_LOGGING_ENABLED", "1", "audit logging is enabled"],
  ];
  for (const [name, variable, expected, passReason] of securityControls) {
    const pass = process.env?.[variable] === expected;
    checks.push(result(name, pass ? "PASS" : "BLOCKED", pass ? passReason : `${variable} must be ${expected}`));
  }

  const blocked = checks.find((item) => item.status !== "PASS");
  return {
    status: blocked ? "BLOCKED_WITH_REASON" : READINESS_READY_STATUS,
    checks,
  };
}

const invokedAsMain = process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url;
if (invokedAsMain) {
  const readiness = await checkControlledPilotReadiness({ requireRpc: true });
  console.log(JSON.stringify(readiness, null, 2));
  process.exitCode = readiness.status === READINESS_READY_STATUS ? 0 : 1;
}

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
  TRUSTED_BROWSER_CLIENT_ENV,
} from "./trusted_browser_execution_adapter.mjs";
import {
  CERTIFIED_ORIGIN,
  APPROVED_PLAYWRIGHT_RUNTIME_ENV,
} from "./trusted_browser_service/providers/playwright-runtime-provider.mjs";
import {
  TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV,
} from "./trusted_browser_service/browser-client.mjs";
import { verifyTrustedBrowserProvider } from "./verify_trusted_browser_provider.mjs";
import {
  loadActivationManifest,
} from "./trusted_browser_activation_manifest.mjs";
import {
  verifyConfiguredRuntimeDigest,
} from "./verify_gate4_external_artifacts.mjs";
const DEFAULT_EVIDENCE_DIR = "C:/ProgramData/Sentinel-DNA/release/evidence";
const STAGING_TLS_CA_FILE_ENV = "SENTINEL_DNA_STAGING_TLS_CA_FILE";
const STAGING_TLS_DIR_ENV = "SENTINEL_DNA_STAGING_TLS_DIR";
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

function result(name, status, reason) {
  return { name, status, reason };
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

async function providerConfigured() {
  return hasValue(TRUSTED_BROWSER_CLIENT_ENV) &&
    hasValue(TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV) &&
    hasValue(APPROVED_PLAYWRIGHT_RUNTIME_ENV);
}

async function checkProvider(providerVerification) {
  if (!(await providerConfigured())) {
    return result("provider_configured", "BLOCKED", "required trusted browser provider configuration is missing");
  }

  let verification;
  try {
    verification = providerVerification || await verifyTrustedBrowserProvider();
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

  const configured = await providerConfigured();
  checks.push(result(
    "provider_configured",
    configured ? "PASS" : "BLOCKED",
    configured
      ? "trusted browser provider configuration is present"
      : "required trusted browser provider configuration is missing",
  ));
  if (configured) checks.push(await checkProvider(providerVerification));
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
    originPass = await originReachability(CERTIFIED_ORIGIN);
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
  const readiness = await checkControlledPilotReadiness();
  console.log(JSON.stringify(readiness, null, 2));
  process.exitCode = readiness.status === READINESS_READY_STATUS ? 0 : 1;
}

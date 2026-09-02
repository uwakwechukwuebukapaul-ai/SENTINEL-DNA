/**
 * Read-only Gate 4 external-artifact onboarding verification.
 *
 * This command verifies custody inputs and then executes the existing provider
 * verifier. It never launches a local browser, invokes browserAuth, navigates,
 * handles credentials, or writes anything other than non-secret evidence.
 */

import { createHash } from "node:crypto";
import { existsSync, realpathSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import {
  ACTIVATION_MANIFEST_ENV,
  loadActivationManifest,
} from "./trusted_browser_activation_manifest.mjs";
import {
  APPROVED_RUNTIME_DIGEST_ENV,
  validateRuntimeModuleCustody,
} from "./trusted_browser_runtime_custody.mjs";
import { verifyTrustedBrowserProvider } from "./verify_trusted_browser_provider.mjs";
import { TRUSTED_BROWSER_CLIENT_ENV } from "./trusted_browser_execution_adapter.mjs";
import { TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV } from "./trusted_browser_service/browser-client.mjs";
import {
  APPROVED_PLAYWRIGHT_RUNTIME_ENV,
} from "./trusted_browser_service/providers/playwright-runtime-provider.mjs";

export const EXTERNAL_ARTIFACT_EVIDENCE_SCHEMA_VERSION = "1.0";
const GATE4_EVIDENCE_DIRECTORY = resolve(
  fileURLToPath(new URL("../../../pilot-evidence/gate4/", import.meta.url)),
);
const UTC_EVIDENCE_STAMP = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
export const DEFAULT_EXTERNAL_ARTIFACT_EVIDENCE_PATH = resolve(
  GATE4_EVIDENCE_DIRECTORY,
  `gate4-external-artifact-verification-${UTC_EVIDENCE_STAMP}.json`,
);
const IMAGE_DIGEST_ENV = "SENTINEL_DNA_IMAGE_DIGEST";
const REPOSITORY_ROOT = resolve(fileURLToPath(new URL("../../../", import.meta.url)));
const READY_STATUS = "READY_FOR_ANALYST_PILOT";
const BLOCKED_STATUS = "BLOCKED_WITH_REASON";
const CERTIFIED_ORIGIN = "https://sentinel-dna-staging:18443";
const SAFE_CODES = new Set([
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
  "TB_IMAGE_IDENTITY_INVALID",
  "TB_ORIGIN_UNREACHABLE",
  "TB_PROVIDER_LOAD_TIMEOUT",
  "TB_RUNTIME_SETUP_TIMEOUT",
  "TB_BROWSER_SELECTION_TIMEOUT",
  "TB_BROWSER_CREATE_TIMEOUT",
  "TB_AUTH_CAPABILITY_TIMEOUT",
  "TB_AUTH_BRIDGE_TIMEOUT",
  "TB_TAB_CLOSE_TIMEOUT",
]);

function safeCode(value, fallback = "TB_RUNTIME_UNAVAILABLE") {
  return SAFE_CODES.has(value) ? value : fallback;
}

function canonicalJson(value) {
  if (Array.isArray(value)) return value.map(canonicalJson);
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonicalJson(value[key])]));
}

function isImageDigest(value) {
  return typeof value === "string" && /^sha256:[0-9a-f]{64}$/i.test(value.trim());
}

function configuredPath(environmentName) {
  const configured = process.env?.[environmentName];
  if (typeof configured !== "string" || !configured.trim()) return null;
  const value = configured.trim();
  try {
    const url = value.startsWith("file:") ? new URL(value) : pathToFileURL(resolve(value));
    if (url.protocol !== "file:" || url.search || url.hash || !existsSync(url)) return null;
    return url;
  } catch {
    return null;
  }
}

function isRepositoryArtifact(url) {
  try {
    const artifactPath = resolve(realpathSync(fileURLToPath(url)));
    const repositoryPath = resolve(realpathSync(REPOSITORY_ROOT));
    const repositoryRelative = relative(repositoryPath, artifactPath);
    return !isAbsolute(repositoryRelative) && !repositoryRelative.startsWith("..");
  } catch {
    return true;
  }
}

export async function verifyConfiguredRuntimeDigest(
  manifest,
  { requireOperatorDigest = false, requireDependencyClosure = false } = {},
) {
  const configured = process.env?.[APPROVED_PLAYWRIGHT_RUNTIME_ENV];
  if (typeof configured !== "string" || !configured.trim()) {
    return { status: "BLOCKED", code: "TB_RUNTIME_UNAVAILABLE" };
  }
  const operatorDigest = process.env?.[APPROVED_RUNTIME_DIGEST_ENV];
  if (requireOperatorDigest && (typeof operatorDigest !== "string" || !operatorDigest.trim())) {
    return { status: "BLOCKED", code: "TB_PROVIDER_MANIFEST_INVALID" };
  }
  if (
    requireDependencyClosure &&
    (typeof manifest?.approved_runtime_dependency_lockfile_digest !== "string" ||
      !manifest.approved_runtime_dependency_lockfile_digest.trim())
  ) {
    return { status: "BLOCKED", code: "TB_PROVIDER_MANIFEST_INVALID" };
  }
  try {
    const result = await validateRuntimeModuleCustody({
      modulePath: configured,
      expectedDigest: manifest?.approved_runtime_module_digest,
      operatorDigest,
      expectedLockfileDigest: manifest?.approved_runtime_dependency_lockfile_digest,
      requireDependencyClosure: requireDependencyClosure,
    });
    return {
      status: "PASS",
      digest: result.digest,
      ...(result.dependencyClosure ? { dependencyClosure: result.dependencyClosure } : {}),
    };
  } catch (error) {
    const code = error?.code === "TB_PROVIDER_MANIFEST_INVALID"
      ? error.code
      : "TB_RUNTIME_UNAVAILABLE";
    return { status: "BLOCKED", code };
  }
}

function blockedCheck(name, code) {
  return { name, status: "BLOCKED", code };
}

function passCheck(name) {
  return { name, status: "PASS" };
}

function providerConfigurationCode() {
  return [TRUSTED_BROWSER_CLIENT_ENV, TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV]
    .some((name) => typeof process.env?.[name] !== "string" || !process.env[name].trim())
    ? "TB_PROVIDER_NOT_CONFIGURED"
    : undefined;
}

function activationStatus(checks, providerVerification) {
  const allArtifactsValid = checks.runtime_module_exists.status === "PASS" &&
    checks.runtime_digest_matches_manifest.status === "PASS" &&
    checks.runtime_dependency_bundle.status === "PASS" &&
    checks.manifest_integrity.status === "PASS" &&
    checks.image_digest_binding.status === "PASS" &&
    checks.certified_origin_binding?.status === "PASS";
  return allArtifactsValid && providerVerification?.status === "PASS"
    ? READY_STATUS
    : BLOCKED_STATUS;
}

function remediationFor(code) {
  switch (code) {
    case "TB_RUNTIME_UNAVAILABLE":
      return "Obtain the reviewed Playwright/RPC runtime from approved custody, verify its SHA-256 digest, and rerun onboarding.";
    case "TB_PROVIDER_MANIFEST_MISSING":
      return "Obtain the approved activation custody manifest and configure its non-secret path; do not use the checked-in fixture.";
    case "TB_PROVIDER_MANIFEST_INVALID":
      return "Return the activation manifest to custody for integrity, origin, approval, and digest reconciliation.";
    case "TB_IMAGE_IDENTITY_INVALID":
      return "Set the immutable deployed staging image SHA-256 digest and reconcile it in the custody manifest.";
    case "TB_PROVIDER_NOT_CONFIGURED":
      return "Configure the reviewed facade, provider boundary, and externally supplied runtime through the operator helper.";
    case "TB_PROVIDER_MODULE_MISSING":
      return "Confirm the reviewed provider module is present and supplied from the approved deployment package.";
    case "TB_ORIGIN_UNREACHABLE":
      return "Validate private-TLS reachability of the exact certified staging origin from the approved operator host; do not use an alternate origin.";
    default:
      return "Keep Gate 4 blocked and consult the approved runtime or release-custody owner before retrying.";
  }
}

export async function verifyGate4ExternalArtifacts() {
  const runtimeUrl = configuredPath(APPROVED_PLAYWRIGHT_RUNTIME_ENV);
  const runtimeUsable = runtimeUrl !== null && !isRepositoryArtifact(runtimeUrl);
  const checks = {
    runtime_module_exists: runtimeUsable ? passCheck("runtime_module_exists") : blockedCheck("runtime_module_exists", "TB_RUNTIME_UNAVAILABLE"),
    runtime_digest_matches_manifest: { name: "runtime_digest_matches_manifest", status: "NOT_RUN" },
    runtime_dependency_bundle: { name: "runtime_dependency_bundle", status: "NOT_RUN" },
    manifest_integrity: { name: "manifest_integrity", status: "NOT_RUN" },
    image_digest_binding: { name: "image_digest_binding", status: "NOT_RUN" },
  };
  let runtimeDigest;
  let runtimeCustody;

  let manifest;
  let manifestIntegrityCode;
  const manifestUrl = configuredPath(ACTIVATION_MANIFEST_ENV);
  if (!manifestUrl || isRepositoryArtifact(manifestUrl)) {
    manifestIntegrityCode = "TB_PROVIDER_MANIFEST_MISSING";
    checks.manifest_integrity = blockedCheck("manifest_integrity", manifestIntegrityCode);
  } else {
    try {
      manifest = await loadActivationManifest();
      checks.manifest_integrity = passCheck("manifest_integrity");
    } catch (error) {
      const code = safeCode(error?.code, "TB_PROVIDER_MANIFEST_MISSING");
      manifestIntegrityCode = code;
      checks.manifest_integrity = blockedCheck("manifest_integrity", code);
    }
  }

  if (manifest && runtimeUsable) {
    runtimeCustody = await verifyConfiguredRuntimeDigest(manifest, {
      requireOperatorDigest: true,
      requireDependencyClosure: true,
    });
    if (runtimeCustody.status === "PASS") {
      runtimeDigest = runtimeCustody.digest;
      checks.runtime_digest_matches_manifest = passCheck("runtime_digest_matches_manifest");
      checks.runtime_dependency_bundle = passCheck("runtime_dependency_bundle");
    } else {
      checks.runtime_digest_matches_manifest = blockedCheck(
        "runtime_digest_matches_manifest",
        runtimeCustody.code,
      );
      checks.runtime_dependency_bundle = blockedCheck(
        "runtime_dependency_bundle",
        runtimeCustody.code,
      );
    }
  } else if (!runtimeUsable || !runtimeDigest) {
    checks.runtime_digest_matches_manifest = blockedCheck("runtime_digest_matches_manifest", "TB_RUNTIME_UNAVAILABLE");
    checks.runtime_dependency_bundle = blockedCheck("runtime_dependency_bundle", "TB_RUNTIME_UNAVAILABLE");
  }

  const configuredImage = process.env?.[IMAGE_DIGEST_ENV]?.trim();
  if (!isImageDigest(configuredImage)) {
    checks.image_digest_binding = blockedCheck("image_digest_binding", "TB_IMAGE_IDENTITY_INVALID");
  } else if (manifest && manifest.approved_image_runtime_digest.toLowerCase() === configuredImage.toLowerCase()) {
    checks.image_digest_binding = passCheck("image_digest_binding");
  } else if (manifest) {
    checks.image_digest_binding = blockedCheck("image_digest_binding", "TB_PROVIDER_MANIFEST_INVALID");
  }
  checks.certified_origin_binding = manifest?.staging_origin === CERTIFIED_ORIGIN
    ? passCheck("certified_origin_binding")
    : blockedCheck(
      "certified_origin_binding",
      manifestIntegrityCode || (manifest ? "TB_ORIGIN_REJECTED" : "TB_PROVIDER_MANIFEST_MISSING"),
    );

  const custodyBlocker = [
    checks.runtime_module_exists,
    checks.runtime_digest_matches_manifest,
    checks.runtime_dependency_bundle,
    checks.manifest_integrity,
    checks.image_digest_binding,
    checks.certified_origin_binding,
  ].find((check) => check.status !== "PASS");
  const providerConfigurationFailure = providerConfigurationCode();
  let providerVerification;
  if (providerConfigurationFailure || custodyBlocker) {
    // Do not import or execute any operator runtime until its exact bytes,
    // custody manifest, deployed image, and certified origin are reconciled.
    providerVerification = {
      status: BLOCKED_STATUS,
      failure_category: providerConfigurationFailure ||
        safeCode(custodyBlocker.code, "TB_RUNTIME_UNAVAILABLE"),
      checks: {},
    };
  } else {
    try {
      providerVerification = await verifyTrustedBrowserProvider();
    } catch {
      providerVerification = { status: BLOCKED_STATUS, failure_category: "TB_RUNTIME_UNAVAILABLE", checks: {} };
    }
  }
  const providerCode = providerVerification.status === "PASS"
    ? undefined
    : safeCode(providerVerification.failure_category, "TB_RUNTIME_UNAVAILABLE");
  const blockers = [
    ...Object.values(checks).filter((check) => check.status !== "PASS").map((check) => check.code),
    ...(providerCode ? [providerCode] : []),
  ].filter((code, index, values) => code && values.indexOf(code) === index).sort();
  const status = activationStatus(checks, providerVerification);
  const evidence = {
    schema_version: EXTERNAL_ARTIFACT_EVIDENCE_SCHEMA_VERSION,
    gate: "GATE4",
    evidence_type: "external_artifact_onboarding_verification",
    status,
    provider_verification: {
      status: providerVerification.status === "PASS" ? "PASS" : BLOCKED_STATUS,
      ...(providerCode ? { failure_category: providerCode } : {}),
    },
    activation: { status, codes: blockers },
    checks: {
      ...checks,
      provider_verification: providerVerification.status === "PASS"
        ? passCheck("provider_verification")
        : blockedCheck("provider_verification", providerCode),
      certified_origin_binding: checks.certified_origin_binding,
    },
    artifact_identity: {
      runtime_module_digest: runtimeDigest || null,
      runtime_dependency_lockfile_digest: runtimeCustody?.dependencyClosure?.lockfileDigest || null,
      image_digest: isImageDigest(configuredImage) ? configuredImage.toLowerCase() : null,
      certified_origin: CERTIFIED_ORIGIN,
    },
    controls: {
      credentials_included: false,
      cookies_included: false,
      tokens_included: false,
      sessions_included: false,
      browserAuth_invoked: false,
      security_controls_bypassed: false,
    },
    blockers,
    remediation: blockers.map(remediationFor),
  };
  return {
    ...evidence,
    evidence_sha256: createHash("sha256").update(JSON.stringify(canonicalJson(evidence)), "utf8").digest("hex"),
  };
}

function outputPathFromArgs(args) {
  const index = args.indexOf("--output");
  if (index < 0) return DEFAULT_EXTERNAL_ARTIFACT_EVIDENCE_PATH;
  if (args.filter((value) => value === "--output").length !== 1 || !args[index + 1]) throw new Error("invalid output");
  return resolve(args[index + 1]);
}

async function writeEvidence(evidence, outputPath) {
  const evidenceDirectory = GATE4_EVIDENCE_DIRECTORY;
  const target = resolve(outputPath);
  const relativeTarget = relative(evidenceDirectory, target);
  if (isAbsolute(relativeTarget) || relativeTarget.startsWith("..") ||
      !/^gate4-external-artifact-verification(?:-[A-Za-z0-9._-]+)?\.json$/i.test(relativeTarget)) {
    throw new Error("invalid output");
  }
  await mkdir(evidenceDirectory, { recursive: true });
  await writeFile(target, `${JSON.stringify(evidence, null, 2)}\n`, { encoding: "utf8", flag: "wx" });
}

const invokedAsMain = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (invokedAsMain) {
  const evidence = await verifyGate4ExternalArtifacts();
  try {
    await writeEvidence(evidence, outputPathFromArgs(process.argv.slice(2)));
  } catch {
    evidence.status = BLOCKED_STATUS;
    evidence.activation = { status: BLOCKED_STATUS, codes: ["TB_EVIDENCE_DIRECTORY_UNAVAILABLE"] };
    evidence.blockers = ["TB_EVIDENCE_DIRECTORY_UNAVAILABLE"];
    evidence.remediation = ["Use the approved non-secret evidence custody directory and rerun onboarding verification."];
  }
  console.log(JSON.stringify(evidence, null, 2));
  process.exitCode = evidence.status === READY_STATUS ? 0 : 1;
}

/**
 * Generate deterministic, non-secret evidence for the Gate 4 provider check.
 *
 * This command delegates all provider validation to the authoritative
 * verifier. It does not provide a test runtime, invoke browserAuth, navigate,
 * evaluate page code, launch a browser, or connect to CDP.
 */

import { createHash } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { TRUSTED_BROWSER_RUNTIME_ENVIRONMENT } from "./trusted_browser_execution_adapter.mjs";
import { CERTIFIED_ORIGIN } from "./trusted_browser_service/providers/playwright-runtime-provider.mjs";
import { verifyTrustedBrowserProvider } from "./verify_trusted_browser_provider.mjs";

export const GATE4_EVIDENCE_SCHEMA_VERSION = "1.0";
export const DEFAULT_GATE4_EVIDENCE_PATH = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "../../../pilot-evidence/gate4/gate4-provider-verification.json",
);

const CHECK_NAMES = Object.freeze([
  "provider",
  "runtime",
  "origin",
  "browser_contract",
  "browser_auth",
]);

const SAFE_FAILURE_CATEGORIES = new Set([
  "TB_PROVIDER_NOT_CONFIGURED",
  "TB_PROVIDER_MODULE_MISSING",
  "TB_PROVIDER_EXPORT_INVALID",
  "TB_RUNTIME_UNAVAILABLE",
  "TB_BROWSER_SELECTION_FAILED",
  "TB_BROWSER_CONTRACT_FAILED",
  "TB_AUTH_CAPABILITY_MISSING",
  "TB_ORIGIN_REJECTED",
]);

function canonicalJson(value) {
  if (Array.isArray(value)) return value.map(canonicalJson);
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.keys(value).sort().map((key) => [key, canonicalJson(value[key])]),
  );
}

function digest(value) {
  return createHash("sha256")
    .update(JSON.stringify(canonicalJson(value)), "utf8")
    .digest("hex");
}

function normalizedChecks(verification) {
  return Object.fromEntries(CHECK_NAMES.map((name) => [
    name,
    verification?.checks?.[name] === "PASS" ? "PASS" :
      verification?.checks?.[name] === "FAIL" ? "FAIL" : "NOT_RUN",
  ]));
}

/**
 * Build evidence from verifier output without copying paths or exceptions.
 * The same verifier result always produces the same evidence bytes.
 */
export function buildGate4Evidence(verification) {
  const checks = normalizedChecks(verification);
  const evidence = {
    schema_version: GATE4_EVIDENCE_SCHEMA_VERSION,
    gate: "GATE4",
    evidence_type: "trusted_browser_provider_verification",
    status: verification?.status === "PASS" && Object.values(checks).every((value) => value === "PASS")
      ? "PASS"
      : "BLOCKED_WITH_REASON",
    provider_configuration: {
      trusted_browser_client: "repository:trusted_browser_service/browser-client.mjs",
      approved_provider: "repository:trusted_browser_service/providers/playwright-runtime-provider.mjs",
      runtime_environment: TRUSTED_BROWSER_RUNTIME_ENVIRONMENT,
      certified_origin: CERTIFIED_ORIGIN,
    },
    checks,
    controls: {
      provider_module_existence_enforced: true,
      provider_export_validation_enforced: true,
      runtime_contract_enforced: true,
      certified_origin_restriction_enforced: true,
      browser_contract_enforced: true,
      browser_auth_capability_required: true,
      credentials_or_tokens_in_evidence: false,
      browserAuth_invoked: false,
      browser_launched_by_generator: false,
    },
  };
  if (SAFE_FAILURE_CATEGORIES.has(verification?.failure_category) && evidence.status !== "PASS") {
    evidence.failure_category = verification.failure_category;
  }
  return {
    ...evidence,
    evidence_sha256: digest(evidence),
  };
}

function outputPathFromArgs(args) {
  const outputIndex = args.indexOf("--output");
  if (outputIndex < 0) return DEFAULT_GATE4_EVIDENCE_PATH;
  if (args.filter((value) => value === "--output").length !== 1 || !args[outputIndex + 1]) {
    throw new Error("invalid evidence output");
  }
  return resolve(args[outputIndex + 1]);
}

function assertSafeOutputPath(outputPath) {
  const gate4Directory = resolve(dirname(DEFAULT_GATE4_EVIDENCE_PATH));
  const relativePath = relative(gate4Directory, outputPath);
  if (
    isAbsolute(relativePath) ||
    relativePath.startsWith("..") ||
    !/^gate4-provider-verification(?:-[A-Za-z0-9._-]+)?\.json$/i.test(relativePath)
  ) throw new Error("invalid evidence output");
}

export async function generateGate4Evidence({ outputPath = DEFAULT_GATE4_EVIDENCE_PATH } = {}) {
  const verification = await verifyTrustedBrowserProvider();
  const evidence = buildGate4Evidence(verification);
  const target = resolve(outputPath);
  assertSafeOutputPath(target);
  await mkdir(dirname(target), { recursive: true });
  await writeFile(target, `${JSON.stringify(evidence, null, 2)}\n`, { encoding: "utf8", flag: "wx" });
  return { evidence, outputPath: target };
}

const invokedAsMain = process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url;
if (invokedAsMain) {
  try {
    const { evidence } = await generateGate4Evidence({ outputPath: outputPathFromArgs(process.argv.slice(2)) });
    console.log(JSON.stringify(evidence, null, 2));
    process.exitCode = evidence.status === "PASS" ? 0 : 1;
  } catch {
    console.log(JSON.stringify({ status: "BLOCKED_WITH_REASON", failure_category: "TB_EVIDENCE_DIRECTORY_UNAVAILABLE" }, null, 2));
    process.exitCode = 1;
  }
}

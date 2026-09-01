/**
 * Generate a safe, machine-readable trusted-browser activation report.
 *
 * This command performs provider contract verification and the read-only
 * staging readiness checks. It never authenticates, invokes browserAuth,
 * navigates, writes evidence, or exposes provider paths or exceptions.
 */

import { writeFile } from "node:fs/promises";
import { isAbsolute, relative, resolve } from "node:path";
import { dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import {
  checkControlledPilotReadiness,
  READINESS_READY_STATUS,
} from "./check_controlled_pilot_readiness.mjs";
import { verifyTrustedBrowserProvider } from "./verify_trusted_browser_provider.mjs";

const SAFE_FAILURE_CODES = new Set([
  "TB_PROVIDER_NOT_CONFIGURED",
  "TB_PROVIDER_MODULE_MISSING",
  "TB_PROVIDER_EXPORT_INVALID",
  "TB_RUNTIME_UNAVAILABLE",
  "TB_BROWSER_SELECTION_FAILED",
  "TB_BROWSER_CONTRACT_FAILED",
  "TB_AUTH_CAPABILITY_MISSING",
  "TB_ORIGIN_REJECTED",
  "TB_PROVIDER_MANIFEST_MISSING",
  "TB_PROVIDER_MANIFEST_INVALID",
  "TB_IMAGE_IDENTITY_INVALID",
  "TB_ORIGIN_UNREACHABLE",
  "TB_EVIDENCE_DIRECTORY_UNAVAILABLE",
  "TB_SECURITY_CONTROL_MISSING",
]);
const PILOT_EVIDENCE_DIRECTORY = resolve(dirname(fileURLToPath(import.meta.url)), "../../../pilot-evidence");

function safeCategory(value, fallback) {
  return SAFE_FAILURE_CODES.has(value) ? value : fallback;
}

function reportCheck(name, passed, passReason, failureReason) {
  return {
    name,
    status: passed ? "PASS" : "BLOCKED",
    reason: passed ? passReason : failureReason,
  };
}

function byName(checks, name) {
  return checks.find((check) => check.name === name);
}

async function safeProviderVerification() {
  try {
    return await verifyTrustedBrowserProvider();
  } catch {
    return {
      status: "FAIL",
      checks: {},
      failure_category: "TB_RUNTIME_UNAVAILABLE",
    };
  }
}

export async function generateTrustedBrowserReadinessReport(options = {}) {
  const providerVerification = await safeProviderVerification();
  const readiness = await checkControlledPilotReadiness({
    ...options,
    providerVerification,
  });
  const providerConfigured = byName(readiness.checks, "provider_configured")?.status === "PASS";
  const runtimeReachable = providerVerification.checks?.runtime === "PASS";
  const browserContractValid = providerVerification.checks?.browser_contract === "PASS";
  const browserAuthAvailable = providerVerification.checks?.browser_auth === "PASS";
  const originReachable = byName(readiness.checks, "certified_origin")?.status === "PASS";
  const evidenceWritable = byName(readiness.checks, "evidence_directory")?.status === "PASS";
  const auditNames = [
    "secure_cookies",
    "debug_disabled",
    "pilot_access_gate",
    "tenant_isolation",
    "audit_logging",
  ];
  const auditReady = auditNames.every((name) => byName(readiness.checks, name)?.status === "PASS");
  const providerFailure = safeCategory(
    providerVerification.failure_category,
    "TB_RUNTIME_UNAVAILABLE",
  );
  const providerCheckFailure = (checkName, fallback) =>
    providerVerification.checks?.[checkName] === "FAIL"
      ? providerFailure
      : providerVerification.checks?.[checkName] === "NOT_RUN"
        ? providerFailure
        : fallback;

  const checks = [
    reportCheck(
      "provider_configured",
      providerConfigured,
      "trusted browser provider configuration is present",
      "TB_PROVIDER_NOT_CONFIGURED",
    ),
    reportCheck(
      "runtime_reachable",
      runtimeReachable,
      "reviewed runtime setup completed",
      providerCheckFailure("runtime", "TB_RUNTIME_UNAVAILABLE"),
    ),
    reportCheck(
      "browser_contract_valid",
      browserContractValid,
      "browser and tab contract is valid",
      providerCheckFailure("browser_contract", "TB_BROWSER_CONTRACT_FAILED"),
    ),
    reportCheck(
      "origin_reachable",
      originReachable,
      "certified staging origin is reachable",
      byName(readiness.checks, "certified_origin")?.reason || "certified staging origin is not reachable",
    ),
    reportCheck(
      "browser_auth_available",
      browserAuthAvailable,
      "external browserAuth capability is available",
      providerCheckFailure("browser_auth", "TB_AUTH_CAPABILITY_MISSING"),
    ),
    reportCheck(
      "evidence_directory_writable",
      evidenceWritable,
      "evidence directory is writable",
      byName(readiness.checks, "evidence_directory")?.reason || "evidence directory is not writable",
    ),
    reportCheck(
      "audit_prerequisites_available",
      auditReady,
      "staging security and audit prerequisites are enabled",
      byName(readiness.checks, "audit_logging")?.reason || "audit prerequisites are unavailable",
    ),
    reportCheck(
      "activation_manifest_valid",
      byName(readiness.checks, "activation_manifest")?.status === "PASS",
      "activation manifest integrity and certified origin are valid",
      byName(readiness.checks, "activation_manifest")?.reason || "TB_PROVIDER_MANIFEST_INVALID",
    ),
  ];
  const blocked = checks.find((check) => check.status !== "PASS");
  const finalStatus = blocked ? "BLOCKED_WITH_REASON" : READINESS_READY_STATUS;
  return {
    schema_version: "1.0",
    generated_at_utc: new Date().toISOString(),
    status: finalStatus,
    manifest_status: byName(readiness.checks, "activation_manifest")?.status || "BLOCKED",
    provider_status: byName(readiness.checks, "provider_verification")?.status || "BLOCKED",
    image_digest_status: byName(readiness.checks, "image_digest")?.status || "BLOCKED",
    origin_status: byName(readiness.checks, "certified_origin")?.status || "BLOCKED",
    tenant_isolation_status: byName(readiness.checks, "tenant_isolation")?.status || "BLOCKED",
    audit_status: byName(readiness.checks, "audit_logging")?.status || "BLOCKED",
    final_readiness_decision: finalStatus,
    checks,
  };
}

const invokedAsMain = process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url;
if (invokedAsMain) {
  const argumentsList = process.argv.slice(2);
  const outputIndex = argumentsList.indexOf("--output");
  const outputArgument = outputIndex >= 0 ? argumentsList[outputIndex + 1] : undefined;
  let report = await generateTrustedBrowserReadinessReport();
  if (outputIndex >= 0 && (!outputArgument || argumentsList.filter((value) => value === "--output").length !== 1)) {
    report = {
      ...report,
      status: "BLOCKED_WITH_REASON",
      final_readiness_decision: "BLOCKED_WITH_REASON",
      checks: [
        ...report.checks,
        { name: "activation_report_artifact", status: "BLOCKED", reason: "TB_EVIDENCE_DIRECTORY_UNAVAILABLE" },
      ],
    };
  } else if (outputArgument) {
    try {
      const target = resolve(outputArgument);
      const relativeTarget = relative(PILOT_EVIDENCE_DIRECTORY, target);
      if (
        isAbsolute(relativeTarget) ||
        relativeTarget.startsWith("..") ||
        !/^controlled-pilot-readiness-report-[0-9]{8}T[0-9]{6,9}Z\.json$/i.test(relativeTarget)
      ) throw new Error("invalid report destination");
      await writeFile(target, `${JSON.stringify(report, null, 2)}\n`, { encoding: "utf8", flag: "wx" });
    } catch {
      report = {
        ...report,
        status: "BLOCKED_WITH_REASON",
        final_readiness_decision: "BLOCKED_WITH_REASON",
        checks: [
          ...report.checks,
          { name: "activation_report_artifact", status: "BLOCKED", reason: "TB_EVIDENCE_DIRECTORY_UNAVAILABLE" },
        ],
      };
    }
  }
  console.log(JSON.stringify(report, null, 2));
  process.exitCode = report.status === READINESS_READY_STATUS ? 0 : 1;
}

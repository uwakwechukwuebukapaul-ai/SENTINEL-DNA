/**
 * Produce a safe operator troubleshooting report for activation blockers.
 *
 * This is diagnostic-only. It reuses the trusted readiness report and emits
 * component names, allowlisted codes, and remediation guidance. It never
 * prints paths, provider exceptions, secrets, or browser state.
 */

import { pathToFileURL } from "node:url";
import { generateTrustedBrowserReadinessReport } from "./generate_trusted_browser_readiness_report.mjs";

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
  "TB_EVIDENCE_DIRECTORY_UNAVAILABLE",
  "TB_SECURITY_CONTROL_MISSING",
]);

const REMEDIATION = Object.freeze({
  provider_configured: ["external_reviewed_runtime", "TB_PROVIDER_NOT_CONFIGURED", "Configure the reviewed facade, provider boundary, and external runtime module."],
  runtime_reachable: ["external_reviewed_runtime", "TB_RUNTIME_UNAVAILABLE", "Confirm the separately reviewed Playwright/RPC runtime is installed and available."],
  browser_contract_valid: ["browser_contract", "TB_BROWSER_CONTRACT_FAILED", "Return the runtime to review; required browser and tab surfaces are incomplete."],
  origin_reachable: ["certified_staging_origin", "TB_ORIGIN_UNREACHABLE", "Verify private staging DNS, TLS trust, and the certified staging origin."],
  browser_auth_available: ["browser_auth_capability", "TB_AUTH_CAPABILITY_MISSING", "Restore the reviewed browserAuth bridge; do not pass credentials another way."],
  evidence_directory_writable: ["evidence_custody", "TB_EVIDENCE_DIRECTORY_UNAVAILABLE", "Verify the approved non-production evidence directory and append-only custody access."],
  audit_prerequisites_available: ["security_controls", "TB_SECURITY_CONTROL_MISSING", "Enable and verify secure cookies, disabled debug, pilot access, tenant isolation, and audit logging."],
  activation_manifest_valid: ["activation_manifest", "TB_PROVIDER_MANIFEST_INVALID", "Create or repair the externally approved manifest and reconcile its digest and origin."],
});

function safeCode(value, fallback) {
  return SAFE_CODES.has(value) ? value : fallback;
}

export async function generateTrustedBrowserActivationTroubleshootingReport(options = {}) {
  let readiness;
  try {
    readiness = await generateTrustedBrowserReadinessReport(options);
  } catch {
    return {
      schema_version: "1.0",
      generated_at_utc: new Date().toISOString(),
      status: "BLOCKED_WITH_REASON",
      blockers: [{ component: "activation_checks", check: "activation_report", code: "TB_RUNTIME_UNAVAILABLE", action: "Retry from the approved operator runtime." }],
      next_action: "Resolve every listed blocker before controlled analyst pilot execution.",
    };
  }

  const blockers = readiness.checks
    .filter((check) => check.status !== "PASS")
    .map((check) => {
      const [component, fallbackCode, action] = REMEDIATION[check.name] || ["activation_checks", "TB_RUNTIME_UNAVAILABLE", "Retry from the approved operator runtime."];
      const code = safeCode(check.reason, fallbackCode);
      return { component, check: check.name, code, action };
    });
  return {
    schema_version: "1.0",
    generated_at_utc: new Date().toISOString(),
    status: readiness.status,
    blockers,
    next_action: blockers.length === 0
      ? "Proceed to the human approval gate; do not execute without that approval."
      : "Resolve every listed blocker before controlled analyst pilot execution.",
  };
}

const invokedAsMain = process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url;
if (invokedAsMain) {
  const report = await generateTrustedBrowserActivationTroubleshootingReport();
  console.log(JSON.stringify(report, null, 2));
  process.exitCode = report.status === "READY_FOR_ANALYST_PILOT" ? 0 : 1;
}

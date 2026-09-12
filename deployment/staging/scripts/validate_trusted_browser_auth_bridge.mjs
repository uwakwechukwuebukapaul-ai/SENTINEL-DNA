/**
 * Read-only acceptance harness for the operator-supplied browserAuth bridge.
 *
 * This tool validates only module custody/path shape and the
 * requestBrowserAuth export. It never invokes the bridge, launches a browser,
 * navigates, handles credentials, or changes Gate 4/pilot state.
 */

import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const BROWSER_AUTH_BRIDGE_ENV =
  "SENTINEL_DNA_BROWSER_AUTH_BRIDGE";
export const BROWSER_AUTH_BRIDGE_EXPORT = "requestBrowserAuth";

const REJECTED_PATH_MARKERS = [
  "/tests/",
  "/test/",
  "/fixtures/",
  "/fixture/",
  "stub",
  "mock",
  "fake",
];

function blocked(failureCategory) {
  return {
    status: "BLOCKED_WITH_REASON",
    checks: { bridge: "FAIL" },
    failure_category: failureCategory,
  };
}

export function validateBrowserAuthBridgeModule(moduleNamespace) {
  return typeof moduleNamespace?.[BROWSER_AUTH_BRIDGE_EXPORT] === "function"
    ? { status: "PASS", checks: { bridge: "PASS" } }
    : blocked("TB_AUTH_BRIDGE_EXPORT_INVALID");
}

function configuredBridgeUrl(modulePath) {
  if (typeof modulePath !== "string" || !modulePath.trim()) {
    return blocked("TB_AUTH_BRIDGE_MISSING");
  }

  const normalized = modulePath.replaceAll("\\", "/").toLowerCase();
  if (REJECTED_PATH_MARKERS.some((marker) => normalized.includes(marker))) {
    return blocked("TB_AUTH_BRIDGE_MISSING");
  }

  let moduleUrl;
  try {
    moduleUrl = modulePath.trim().startsWith("file:")
      ? new URL(modulePath.trim())
      : pathToFileURL(resolve(modulePath.trim()));
  } catch {
    return blocked("TB_AUTH_BRIDGE_MISSING");
  }

  if (
    moduleUrl.protocol !== "file:" ||
    moduleUrl.search ||
    moduleUrl.hash ||
    !existsSync(moduleUrl)
  ) {
    return blocked("TB_AUTH_BRIDGE_MISSING");
  }

  return moduleUrl;
}

export async function validateConfiguredBrowserAuthBridge({
  modulePath = process.env?.[BROWSER_AUTH_BRIDGE_ENV],
} = {}) {
  const moduleUrl = configuredBridgeUrl(modulePath);
  if (!(moduleUrl instanceof URL)) return moduleUrl;

  let moduleNamespace;
  try {
    moduleNamespace = await import(moduleUrl.href);
  } catch {
    return blocked("TB_AUTH_BRIDGE_RUNTIME_FAILED");
  }

  return validateBrowserAuthBridgeModule(moduleNamespace);
}

const invokedAsMain = typeof process !== "undefined" && process.argv?.[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (invokedAsMain) {
  const result = await validateConfiguredBrowserAuthBridge();
  console.log(JSON.stringify(result, null, 2));
  process.exitCode = result.status === "PASS" ? 0 : 1;
}

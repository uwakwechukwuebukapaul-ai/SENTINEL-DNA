/**
 * Read-only operator verification for the trusted browser provider chain.
 *
 * This command validates the configured modules and browser contract. It does
 * not perform authentication, call browserAuth.request(), navigate, evaluate
 * page code, make HTTP requests, launch a local browser, or connect to CDP.
 */

import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import {
  TRUSTED_BROWSER_CLIENT_ENV,
  TRUSTED_BROWSER_RUNTIME_ENVIRONMENT,
} from "./trusted_browser_execution_adapter.mjs";
import {
  CERTIFIED_ORIGIN,
  TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV,
} from "./trusted_browser_service/browser-client.mjs";

const CHECK_NAMES = ["provider", "runtime", "origin", "browser_contract", "browser_auth"];
const SAFE_CATEGORIES = new Set([
  "TB_PROVIDER_NOT_CONFIGURED",
  "TB_PROVIDER_MODULE_MISSING",
  "TB_PROVIDER_EXPORT_INVALID",
  "TB_RUNTIME_UNAVAILABLE",
  "TB_BROWSER_SELECTION_FAILED",
  "TB_BROWSER_CONTRACT_FAILED",
  "TB_AUTH_CAPABILITY_MISSING",
  "TB_ORIGIN_REJECTED",
  "TB_ORIGIN_UNREACHABLE",
]);

function diagnosticError(code) {
  const error = new Error(`[${code}] trusted browser provider verification failed`);
  error.code = code;
  return error;
}

function categoryFor(error, fallback) {
  return SAFE_CATEGORIES.has(error?.code) ? error.code : fallback;
}

function resultTemplate() {
  return {
    status: "BLOCKED_WITH_REASON",
    checks: Object.fromEntries(CHECK_NAMES.map((name) => [name, "NOT_RUN"])),
  };
}

function markPass(result, check) {
  result.checks[check] = "PASS";
}

function markFailure(result, check, category) {
  result.checks[check] = "FAIL";
  if (!result.failure_category) result.failure_category = category;
}

function configuredModuleUrl(environmentName) {
  const configured = process.env?.[environmentName];
  if (typeof configured !== "string" || !configured.trim()) {
    throw diagnosticError("TB_PROVIDER_NOT_CONFIGURED");
  }
  const modulePath = configured.trim();
  const normalized = modulePath.replaceAll("\\", "/").toLowerCase();
  // Never allow the repository's test fixture to become an operator provider.
  if (
    normalized.includes("/tests/staging/") ||
    normalized.includes("trusted-playwright-adapter-stub")
  ) {
    throw diagnosticError("TB_PROVIDER_MODULE_MISSING");
  }
  let url;
  try {
    url = modulePath.startsWith("file:")
      ? new URL(modulePath)
      : pathToFileURL(resolve(modulePath));
  } catch {
    throw diagnosticError("TB_PROVIDER_MODULE_MISSING");
  }
  if (url.protocol !== "file:" || url.search || url.hash || !existsSync(url)) {
    throw diagnosticError("TB_PROVIDER_MODULE_MISSING");
  }
  return url;
}

async function loadConfiguredModule(environmentName) {
  const url = configuredModuleUrl(environmentName);
  try {
    const module = await import(url.href);
    if (typeof module.setupBrowserRuntime !== "function") {
      throw diagnosticError("TB_PROVIDER_EXPORT_INVALID");
    }
    return module;
  } catch (error) {
    if (error?.code === "TB_PROVIDER_EXPORT_INVALID") throw error;
    throw diagnosticError("TB_PROVIDER_MODULE_MISSING");
  }
}

function assertRuntimeContract(runtime) {
  if (!runtime?.browsers || typeof runtime.browsers.getForUrl !== "function") {
    throw diagnosticError("TB_RUNTIME_UNAVAILABLE");
  }
}

function assertBrowserContract(browser) {
  if (!browser || typeof browser.tabs?.new !== "function") {
    throw diagnosticError("TB_BROWSER_CONTRACT_FAILED");
  }
}

function assertTabContract(tab) {
  if (!tab || typeof tab.goto !== "function") {
    throw diagnosticError("TB_BROWSER_CONTRACT_FAILED");
  }
  if (
    typeof tab.playwright?.locator !== "function" ||
    typeof tab.playwright?.evaluate !== "function" ||
    typeof tab.dom_cua?.get_visible_dom !== "function" ||
    typeof tab.capabilities?.get !== "function"
  ) {
    throw diagnosticError("TB_BROWSER_CONTRACT_FAILED");
  }
}

/**
 * Verify the configured trusted browser provider without performing auth.
 * The returned object contains only statuses and an allowlisted category.
 */
export async function verifyTrustedBrowserProvider() {
  const result = resultTemplate();
  let trustedClient;
  let runtime;
  let tab;

  try {
    await loadConfiguredModule(TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV);
    trustedClient = await loadConfiguredModule(TRUSTED_BROWSER_CLIENT_ENV);
    markPass(result, "provider");
  } catch (error) {
    markFailure(result, "provider", categoryFor(error, "TB_PROVIDER_MODULE_MISSING"));
    return result;
  }

  try {
    runtime = await trustedClient.setupBrowserRuntime({
      environment: TRUSTED_BROWSER_RUNTIME_ENVIRONMENT,
    });
    assertRuntimeContract(runtime);
    markPass(result, "runtime");
  } catch (error) {
    markFailure(result, "runtime", categoryFor(error, "TB_RUNTIME_UNAVAILABLE"));
    return result;
  }

  let browser;
  try {
    browser = await runtime.browsers.getForUrl(CERTIFIED_ORIGIN);
    markPass(result, "origin");
  } catch (error) {
    markFailure(result, "origin", categoryFor(error, "TB_BROWSER_SELECTION_FAILED"));
    return result;
  }

  try {
    assertBrowserContract(browser);
    tab = await browser.tabs.new();
    assertTabContract(tab);
    markPass(result, "browser_contract");
  } catch (error) {
    markFailure(result, "browser_contract", categoryFor(error, "TB_BROWSER_CONTRACT_FAILED"));
    if (tab && typeof tab.close === "function") await tab.close().catch(() => {});
    return result;
  }

  try {
    const browserAuth = await tab.capabilities.get("browserAuth");
    if (!browserAuth || typeof browserAuth.request !== "function") {
      throw diagnosticError("TB_AUTH_CAPABILITY_MISSING");
    }
    markPass(result, "browser_auth");
  } catch (error) {
    markFailure(result, "browser_auth", categoryFor(error, "TB_AUTH_CAPABILITY_MISSING"));
  } finally {
    if (tab && typeof tab.close === "function") await tab.close().catch(() => {});
  }

  if (Object.values(result.checks).every((status) => status === "PASS")) {
    result.status = "PASS";
    delete result.failure_category;
  }
  return result;
}

const invokedAsMain = typeof process !== "undefined" && process.argv?.[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (invokedAsMain) {
  const result = await verifyTrustedBrowserProvider();
  console.log(JSON.stringify(result, null, 2));
  process.exitCode = result.status === "PASS" ? 0 : 1;
}

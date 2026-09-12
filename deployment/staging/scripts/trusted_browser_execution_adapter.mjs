/**
 * Operator-approved bridge from the trusted browser service to the pilot
 * runner.
 *
 * This adapter deliberately does not start a browser, connect to a browser
 * debugging port, or accept any credential material. The configured module
 * must be the reviewed browser client for the operator's trusted service. That
 * client obtains its browser RPC transport from the trusted runtime bridge.
 */

import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

import { DEFAULT_ORIGIN } from "./controlled_analyst_pilot_runner.mjs";
import {
  createTrustedBrowserDiagnostics,
  TRUSTED_BROWSER_TIMEOUTS,
} from "./trusted_browser_diagnostics.mjs";

export const TRUSTED_BROWSER_CLIENT_ENV = "SENTINEL_DNA_TRUSTED_BROWSER_CLIENT";
export const TRUSTED_BROWSER_RUNTIME_ENVIRONMENT = "codex-app";

function trustedBrowserError(code, message) {
  const error = new Error(`[${code}] ${message}`);
  // Only stable, allowlisted diagnostic identifiers cross this boundary.
  error.code = code;
  return error;
}

const SAFE_DIAGNOSTIC_CODES = new Set([
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
  "TB_RUNTIME_SETUP",
  "TB_RUNTIME_SETUP_TIMEOUT",
  "TB_PROVIDER_LOAD_TIMEOUT",
  "TB_BROWSER_SELECTION",
  "TB_BROWSER_SELECTION_TIMEOUT",
  "TB_BROWSER_CREATE",
  "TB_BROWSER_CREATE_TIMEOUT",
  "TB_STAGING_NAVIGATION",
  "TB_STAGING_NAVIGATION_TIMEOUT",
  "TB_AUTH_CAPABILITY",
  "TB_AUTH_CAPABILITY_TIMEOUT",
  "TB_AUTH_BRIDGE",
  "TB_AUTH_BRIDGE_TIMEOUT",
  "TB_AUTH_COMPLETE",
  "TB_AUTH_COMPLETE_TIMEOUT",
  "TB_TAB_CLOSE",
  "TB_TAB_CLOSE_TIMEOUT",
]);

function safeDiagnosticCode(error, fallback) {
  return typeof error?.code === "string" && SAFE_DIAGNOSTIC_CODES.has(error.code)
    ? error.code
    : fallback;
}

function configuredClientModule(explicitPath) {
  if (typeof explicitPath === "string" && explicitPath.trim()) return explicitPath.trim();
  if (typeof process !== "undefined" && process.env?.[TRUSTED_BROWSER_CLIENT_ENV]) {
    return process.env[TRUSTED_BROWSER_CLIENT_ENV].trim();
  }
  throw trustedBrowserError(
    "TB_PROVIDER_NOT_CONFIGURED",
    `${TRUSTED_BROWSER_CLIENT_ENV} must point to the reviewed trusted browser client module`,
  );
}

function clientModuleUrl(modulePath) {
  let url;
  try {
    url = modulePath.startsWith("file:")
      ? new URL(modulePath)
      : pathToFileURL(resolve(modulePath));
  } catch {
    throw trustedBrowserError(
      "TB_PROVIDER_MODULE_MISSING",
      "trusted browser client module path is invalid",
    );
  }
  if (url.protocol !== "file:") {
    throw trustedBrowserError(
      "TB_PROVIDER_MODULE_MISSING",
      "trusted browser client must be a local file module",
    );
  }
  return url.href;
}

function assertCertifiedOrigin(origin) {
  if (origin !== DEFAULT_ORIGIN) {
    throw trustedBrowserError(
      "TB_ORIGIN_REJECTED",
      `trusted browser adapter only permits the certified origin ${DEFAULT_ORIGIN}`,
    );
  }
}

async function assertBrowserContract(browser, diagnostics) {
  if (!browser || typeof browser.tabs?.new !== "function") {
    throw trustedBrowserError("TB_BROWSER_CONTRACT_FAILED", "trusted browser service returned an invalid browser");
  }

  let probeTab;
  try {
    probeTab = await diagnostics.run(
      "BROWSER_CREATE",
      "contract_probe_tab",
      () => browser.tabs.new(),
      { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.BROWSER_CREATE },
    );
    if (!probeTab || typeof probeTab.goto !== "function") {
      throw trustedBrowserError("TB_BROWSER_CONTRACT_FAILED", "trusted browser service returned an invalid tab object");
    }
    if (typeof probeTab.dom_cua?.get_visible_dom !== "function") {
      throw trustedBrowserError("TB_BROWSER_CONTRACT_FAILED", "approved browser is missing visible DOM inspection");
    }
    if (typeof probeTab.playwright?.locator !== "function" || typeof probeTab.playwright?.evaluate !== "function") {
      throw trustedBrowserError("TB_BROWSER_CONTRACT_FAILED", "approved browser is missing the runner Playwright surface");
    }
    if (typeof probeTab.capabilities?.get !== "function") {
      throw trustedBrowserError("TB_BROWSER_CONTRACT_FAILED", "approved browser is missing tab capability discovery");
    }

    let browserAuth;
    try {
      browserAuth = await probeTab.capabilities.get("browserAuth");
    } catch (error) {
      throw trustedBrowserError(
        safeDiagnosticCode(error, "TB_AUTH_CAPABILITY_MISSING"),
        "approved browser does not expose the browserAuth capability",
      );
    }
    if (!browserAuth || typeof browserAuth.request !== "function") {
      throw trustedBrowserError("TB_AUTH_CAPABILITY_MISSING", "approved browser does not expose the browserAuth capability");
    }
  } finally {
    if (probeTab && typeof probeTab.close === "function") {
      await diagnostics.run(
        "TAB_CLOSE",
        "contract_probe_close",
        () => probeTab.close(),
        { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.TAB_CLOSE },
      ).catch(() => {});
    }
  }
}

/**
 * Create and validate the browser object consumed by
 * runControlledAnalystPilot().
 *
 * `browserClientModule` is an operator-environment path used for testing and
 * for pinning the reviewed client installation. It is not a credential or a
 * browser endpoint. In normal execution it is supplied through
 * SENTINEL_DNA_TRUSTED_BROWSER_CLIENT.
 */
export async function createApprovedBrowser({
  origin = DEFAULT_ORIGIN,
  browserClientModule = undefined,
} = {}) {
  assertCertifiedOrigin(origin);
  const diagnostics = createTrustedBrowserDiagnostics();
  let client;
  try {
    client = await diagnostics.run(
      "PROVIDER_LOAD",
      "trusted_client.load",
      () => import(clientModuleUrl(configuredClientModule(browserClientModule))),
      { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.PROVIDER_LOAD },
    );
  } catch (error) {
    const code = error?.code === "ERR_MODULE_NOT_FOUND"
      ? "TB_PROVIDER_MODULE_MISSING"
      : safeDiagnosticCode(error, "TB_PROVIDER_MODULE_MISSING");
    throw trustedBrowserError(
      code,
      code === "TB_PROVIDER_NOT_CONFIGURED"
        ? "trusted browser client module is not configured"
        : code === "TB_PROVIDER_MODULE_MISSING"
          ? "trusted browser client module is missing"
          : "trusted browser client module could not be loaded",
    );
  }
  if (typeof client.setupBrowserRuntime !== "function") {
    throw trustedBrowserError(
      "TB_PROVIDER_EXPORT_INVALID",
      "trusted browser client does not export setupBrowserRuntime",
    );
  }

  let runtime;
  try {
    runtime = await diagnostics.run(
      "RUNTIME_SETUP",
      "trusted_runtime.setup",
      () => client.setupBrowserRuntime({ environment: TRUSTED_BROWSER_RUNTIME_ENVIRONMENT }),
      { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.RUNTIME_SETUP },
    );
  } catch (error) {
    const code = safeDiagnosticCode(error, "TB_RUNTIME_UNAVAILABLE");
    throw trustedBrowserError(
      code,
      `trusted browser runtime setup failed at ${code}`,
    );
  }
  if (!runtime?.browsers || typeof runtime.browsers.getForUrl !== "function") {
    if (runtime && typeof runtime.close === "function") {
      await diagnostics.run(
        "TAB_CLOSE",
        "runtime.close_after_contract_failure",
        () => runtime.close(),
        { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.TAB_CLOSE },
      ).catch(() => {});
    }
    throw trustedBrowserError(
      "TB_RUNTIME_UNAVAILABLE",
      "trusted browser runtime does not provide browser selection",
    );
  }

  let browser;
  try {
    browser = await diagnostics.run(
      "BROWSER_SELECTION",
      "certified_origin.select",
      () => runtime.browsers.getForUrl(origin),
      { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.BROWSER_SELECTION },
    );
  } catch (error) {
    const code = safeDiagnosticCode(error, "TB_BROWSER_SELECTION_FAILED");
    if (runtime && typeof runtime.close === "function") {
      await diagnostics.run(
        "TAB_CLOSE",
        "runtime.close_after_selection_failure",
        () => runtime.close(),
        { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.TAB_CLOSE },
      ).catch(() => {});
    }
    throw trustedBrowserError(
      code,
      `trusted browser selection failed at ${code}`,
    );
  }
  try {
    await assertBrowserContract(browser, diagnostics);
  } catch (error) {
    if (browser && typeof browser.close === "function") {
      await diagnostics.run(
        "TAB_CLOSE",
        "browser.close_after_contract_failure",
        () => browser.close(),
        { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.TAB_CLOSE },
      ).catch(() => {});
    } else if (runtime && typeof runtime.close === "function") {
      await diagnostics.run(
        "TAB_CLOSE",
        "runtime.close_after_contract_failure",
        () => runtime.close(),
        { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.TAB_CLOSE },
      ).catch(() => {});
    }
    throw error;
  }
  return browser;
}

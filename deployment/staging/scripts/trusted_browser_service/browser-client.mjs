/**
 * Sentinel DNA trusted browser service client.
 *
 * This module is the reviewed, origin-scoped client selected by
 * trusted_browser_execution_adapter.mjs.  The actual browser transport is
 * supplied by the operator-approved Playwright-backed browser client.  This
 * facade deliberately does not launch a browser, connect to CDP, make HTTP
 * requests, or collect credentials.
 *
 * The upstream client is configured as a local module because the trusted
 * browser runtime is owned by the operator environment, not by this
 * repository.  It must export setupBrowserRuntime(), as does this module.
 */

import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

import {
  createTrustedRuntimeProvider,
  TRUSTED_BROWSER_ENVIRONMENT,
} from "./runtime-provider.mjs";

export { TRUSTED_BROWSER_ENVIRONMENT } from "./runtime-provider.mjs";

export const CERTIFIED_ORIGIN = "https://sentinel-dna-staging:18443";
export const TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV =
  "SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT";

function trustedBrowserError(code, message) {
  const error = new Error(`[${code}] ${message}`);
  // Keep diagnostics allowlisted and free of upstream exception text, paths,
  // environment values, and any other potentially sensitive configuration.
  error.code = code;
  return error;
}

const SECRET_KEY_PARTS = new Set([
  "password",
  "passwordhash",
  "passphrase",
  "secret",
  "secrets",
  "token",
  "accesstoken",
  "refreshtoken",
  "idtoken",
  "csrftoken",
  "cookie",
  "cookies",
  "setcookie",
  "authorization",
  "privatekey",
  "credential",
  "credentials",
  "clientsecret",
  "apikey",
  "signingkey",
  "encryptionkey",
  "sessionid",
  "jwt",
  "bearer",
]);

function normalizeKey(key) {
  return String(key).toLowerCase().replace(/[^a-z0-9]/g, "");
}

function isSecretKey(key) {
  const normalized = normalizeKey(key);
  return SECRET_KEY_PARTS.has(normalized) ||
    [...SECRET_KEY_PARTS].some((part) => normalized.endsWith(part));
}

function assertNoCredentialFields(value, seen = new WeakSet()) {
  if (value === null || typeof value !== "object") return;
  if (seen.has(value)) return;
  seen.add(value);
  for (const [key, child] of Object.entries(value)) {
    if (isSecretKey(key)) {
      throw new Error("trusted browser client does not accept credential material");
    }
    assertNoCredentialFields(child, seen);
  }
}

function redact(value, seen = new WeakSet()) {
  if (value === null || typeof value !== "object") return value;
  if (seen.has(value)) return "[cycle omitted]";
  seen.add(value);
  if (Array.isArray(value)) return value.map((item) => redact(item, seen));

  const result = {};
  for (const [key, child] of Object.entries(value)) {
    if (isSecretKey(key)) continue;
    result[key] = redact(child, seen);
  }
  return result;
}

function assertCertifiedOrigin(origin) {
  if (typeof origin !== "string") {
    throw new Error(`trusted browser only permits ${CERTIFIED_ORIGIN}`);
  }
  let parsed;
  try {
    parsed = new URL(origin);
  } catch {
    throw new Error(`trusted browser only permits ${CERTIFIED_ORIGIN}`);
  }
  if (
    parsed.origin !== CERTIFIED_ORIGIN ||
    parsed.username ||
    parsed.password ||
    parsed.pathname !== "/" ||
    parsed.search ||
    parsed.hash
  ) {
    throw new Error(`trusted browser only permits the certified origin ${CERTIFIED_ORIGIN}`);
  }
  return parsed.origin;
}

function assertCertifiedUrl(url) {
  if (typeof url !== "string") {
    throw new Error(`trusted browser navigation is restricted to ${CERTIFIED_ORIGIN}`);
  }
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    throw new Error(`trusted browser navigation is restricted to ${CERTIFIED_ORIGIN}`);
  }
  if (
    parsed.origin !== CERTIFIED_ORIGIN ||
    parsed.username ||
    parsed.password
  ) {
    throw new Error(`trusted browser navigation is restricted to ${CERTIFIED_ORIGIN}`);
  }
  return parsed.href;
}

function localModuleUrl(modulePath, label) {
  if (typeof modulePath !== "string" || !modulePath.trim()) {
    throw trustedBrowserError(
      "TB_PROVIDER_NOT_CONFIGURED",
      `${label} must be configured as a local reviewed module`,
    );
  }
  try {
    const url = modulePath.startsWith("file:")
      ? new URL(modulePath)
      : pathToFileURL(resolve(modulePath));
    if (url.protocol !== "file:") throw new Error("not a file module");
    return url.href;
  } catch {
    throw trustedBrowserError(
      "TB_PROVIDER_MODULE_MISSING",
      `${label} must be a local reviewed module`,
    );
  }
}

function configuredUpstreamClient(explicitPath) {
  if (typeof explicitPath === "string" && explicitPath.trim()) {
    return explicitPath.trim();
  }
  const configured = process.env?.[TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV];
  if (typeof configured === "string" && configured.trim()) return configured.trim();
  throw trustedBrowserError(
    "TB_PROVIDER_NOT_CONFIGURED",
    `${TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV} must point to the reviewed Playwright browser client`,
  );
}

function assertUpstreamBrowser(browser) {
  if (!browser || typeof browser.tabs?.new !== "function") {
    throw trustedBrowserError(
      "TB_BROWSER_CONTRACT_FAILED",
      "trusted browser client returned an invalid browser",
    );
  }
}

function assertUpstreamTab(tab) {
  if (!tab || typeof tab.goto !== "function") {
    throw trustedBrowserError(
      "TB_BROWSER_CONTRACT_FAILED",
      "trusted browser client returned an invalid tab",
    );
  }
  if (
    typeof tab.playwright?.locator !== "function" ||
    typeof tab.playwright?.evaluate !== "function"
  ) {
    throw trustedBrowserError(
      "TB_BROWSER_CONTRACT_FAILED",
      "trusted browser tab is missing its Playwright surface",
    );
  }
  if (typeof tab.dom_cua?.get_visible_dom !== "function") {
    throw trustedBrowserError(
      "TB_BROWSER_CONTRACT_FAILED",
      "trusted browser tab is missing visible DOM inspection",
    );
  }
  if (typeof tab.capabilities?.get !== "function") {
    throw trustedBrowserError(
      "TB_BROWSER_CONTRACT_FAILED",
      "trusted browser tab is missing capability discovery",
    );
  }
}

const SAFE_TAB_DIAGNOSTIC_CODES = new Set([
  "TB_BROWSER_CONTRACT_FAILED",
  "TB_AUTH_CAPABILITY_MISSING",
  "TB_AUTH_BRIDGE_MISSING",
  "TB_AUTH_BRIDGE_EXPORT_INVALID",
  "TB_AUTH_BRIDGE_RUNTIME_FAILED",
]);

const SAFE_AUTH_DIAGNOSTIC_CODES = new Set([
  "TB_AUTH_CAPABILITY_MISSING",
  "TB_AUTH_BRIDGE_MISSING",
  "TB_AUTH_BRIDGE_EXPORT_INVALID",
  "TB_AUTH_BRIDGE_RUNTIME_FAILED",
  "TB_AUTH_CAPABILITY_TIMEOUT",
  "TB_AUTH_BRIDGE",
  "TB_AUTH_BRIDGE_TIMEOUT",
  "TB_AUTH_COMPLETE",
  "TB_AUTH_COMPLETE_TIMEOUT",
  "TB_AUTH_REQUEST_INVALID",
  "TB_CREDENTIAL_FIELD_REJECTED",
  "TB_ORIGIN_REJECTED",
]);

function authCapabilityCode(error) {
  return SAFE_AUTH_DIAGNOSTIC_CODES.has(error?.code)
    ? error.code
    : "TB_AUTH_CAPABILITY_MISSING";
}

function createPlaywrightSurface(tab) {
  const playwright = tab.playwright;
  return Object.freeze({
    // Locator objects remain native to the approved Playwright runtime.  This
    // is required so browserAuth can validate selectors against this tab.
    locator: (...args) => playwright.locator(...args),
    // The runner performs page-local, same-origin fetches.  Only the result
    // crosses this service boundary, and secret-shaped fields are removed.
    evaluate: async (...args) => {
      try {
        return redact(await playwright.evaluate(...args));
      } catch {
        throw new Error("trusted Playwright evaluation failed");
      }
    },
  });
}

function createDomCuaSurface(tab) {
  const domCua = tab.dom_cua;
  return Object.freeze({
    get_visible_dom: async (...args) => {
      try {
        return redact(await domCua.get_visible_dom(...args));
      } catch {
        throw new Error("trusted visible DOM inspection failed");
      }
    },
  });
}

function createBrowserAuthCapability(tab) {
  let capabilityPromise;
  return Object.freeze({
    request: async (request) => {
      if (request === null || typeof request !== "object") {
        throw new Error("browserAuth request must be an object");
      }
      try {
        assertNoCredentialFields(request);
      } catch {
        throw trustedBrowserError(
          "TB_CREDENTIAL_FIELD_REJECTED",
          "credential-bearing browser data is not accepted",
        );
      }
      // The credential bridge receives field descriptors and Playwright
      // selectors, never credential values.  Keep this allowlist narrow so a
      // caller cannot smuggle a password, cookie, or token into the bridge.
      if (request.origin !== CERTIFIED_ORIGIN) {
        throw new Error(`browserAuth is restricted to ${CERTIFIED_ORIGIN}`);
      }
      if (!Array.isArray(request.fields) || request.fields.length === 0) {
        throw new Error("browserAuth requires visible field descriptors");
      }
      const fields = request.fields.map((field) => {
        if (field === null || typeof field !== "object") {
          throw new Error("browserAuth field descriptor is invalid");
        }
        if (
          typeof field.id !== "string" ||
          typeof field.label !== "string" ||
          typeof field.type !== "string" ||
          typeof field.selector !== "string" ||
          !field.selector.trim()
        ) {
          throw new Error("browserAuth field descriptor is invalid");
        }
        return {
          id: field.id,
          label: field.label,
          type: field.type,
          ...(field.autocomplete === undefined ? {} : { autocomplete: field.autocomplete }),
          ...(field.required === undefined ? {} : { required: field.required }),
          selector: field.selector,
        };
      });
      const safeRequest = {
        origin: CERTIFIED_ORIGIN,
        fields,
      };
      if (request.submit !== undefined) {
        if (
          request.submit === null ||
          typeof request.submit !== "object" ||
          typeof request.submit.selector !== "string" ||
          !request.submit.selector.trim()
        ) {
          throw new Error("browserAuth submit descriptor is invalid");
        }
        safeRequest.submit = {
          action: request.submit.action,
          selector: request.submit.selector,
        };
      }

      if (!capabilityPromise) capabilityPromise = tab.capabilities.get("browserAuth");
      let capability;
      try {
        capability = await capabilityPromise;
      } catch (error) {
        throw trustedBrowserError(
          authCapabilityCode(error),
          "approved browserAuth capability is unavailable",
        );
      }
      if (!capability || typeof capability.request !== "function") {
        throw trustedBrowserError(
          "TB_AUTH_CAPABILITY_MISSING",
          "approved browserAuth capability is unavailable",
        );
      }
      let result;
      try {
        result = await capability.request(safeRequest);
      } catch (error) {
        const code = SAFE_AUTH_DIAGNOSTIC_CODES.has(error?.code)
          ? error.code
          : "TB_AUTH_BRIDGE";
        throw trustedBrowserError(code, "external browserAuth handoff failed");
      }
      // Deliberately return only the protocol status.  The external bridge
      // owns credential entry and any richer result is not runner-visible.
      return Object.freeze({ status: typeof result?.status === "string" ? result.status : "unknown" });
    },
  });
}

function createRestrictedTab(tab) {
  assertUpstreamTab(tab);
  const browserAuth = createBrowserAuthCapability(tab);
  const restricted = {
    ...(tab.id === undefined ? {} : { id: tab.id }),
    goto: async (url) => tab.goto(assertCertifiedUrl(url)),
    close: typeof tab.close === "function" ? (...args) => tab.close(...args) : undefined,
    playwright: createPlaywrightSurface(tab),
    dom_cua: createDomCuaSurface(tab),
    capabilities: Object.freeze({
      get: async (name) => {
        if (name !== "browserAuth") return undefined;
        let capability;
        try {
          capability = await tab.capabilities.get("browserAuth");
        } catch (error) {
          throw trustedBrowserError(
            authCapabilityCode(error),
            "approved browserAuth capability is unavailable",
          );
        }
        if (!capability || typeof capability.request !== "function") {
          throw trustedBrowserError(
            "TB_AUTH_CAPABILITY_MISSING",
            "approved browserAuth capability is unavailable",
          );
        }
        return browserAuth;
      },
    }),
  };
  if (restricted.close === undefined) delete restricted.close;
  return Object.freeze(restricted);
}

function createRestrictedBrowser(browser) {
  assertUpstreamBrowser(browser);
  const restricted = {
    tabs: Object.freeze({
      new: async (...args) => {
        if (args.length !== 0) throw new Error("trusted browser tabs.new does not accept options");
        try {
          return createRestrictedTab(await browser.tabs.new());
        } catch (error) {
          if (SAFE_TAB_DIAGNOSTIC_CODES.has(error?.code)) throw error;
          throw trustedBrowserError(
            "TB_BROWSER_CONTRACT_FAILED",
            "trusted browser could not create a staging tab",
          );
        }
      },
    }),
  };
  if (typeof browser.close === "function") {
    restricted.close = async () => browser.close();
  }
  return Object.freeze(restricted);
}

/**
 * Set up the trusted browser service runtime consumed by the pilot adapter.
 *
 * Only the certified staging origin is selectable.  The returned runtime has
 * no default-browser selector and no management, cookie, storage, download,
 * or credential APIs.  `browserAuth` remains an external operator-approved
 * capability and is exposed only as its status-returning request method.
 */
export async function setupBrowserRuntime(options = {}) {
  if (options === null || typeof options !== "object" || Array.isArray(options)) {
    throw new Error("trusted browser runtime options must be an object");
  }
  assertNoCredentialFields(options);
  const {
    environment = TRUSTED_BROWSER_ENVIRONMENT,
    upstreamClientModule = undefined,
  } = options;
  if (environment !== TRUSTED_BROWSER_ENVIRONMENT) {
    throw trustedBrowserError(
      "TB_RUNTIME_UNAVAILABLE",
      `trusted browser runtime requires environment ${TRUSTED_BROWSER_ENVIRONMENT}`,
    );
  }

  const upstreamUrl = localModuleUrl(
    configuredUpstreamClient(upstreamClientModule),
    TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV,
  );
  let client;
  try {
    client = await import(upstreamUrl);
  } catch {
    if (!existsSync(new URL(upstreamUrl))) {
      throw trustedBrowserError(
        "TB_PROVIDER_MODULE_MISSING",
        "reviewed Playwright browser client module is missing",
      );
    }
    throw trustedBrowserError(
      "TB_PROVIDER_MODULE_MISSING",
      "reviewed Playwright browser client module could not be loaded",
    );
  }
  let provider;
  try {
    provider = createTrustedRuntimeProvider(client);
  } catch (error) {
    throw trustedBrowserError(
      error.code === "TB_PROVIDER_EXPORT_INVALID"
        ? error.code
        : "TB_PROVIDER_EXPORT_INVALID",
      "reviewed Playwright browser client lacks setupBrowserRuntime",
    );
  }

  let runtime;
  try {
    // Do not forward arbitrary options or environment values to the browser
    // runtime.  In particular, this client never forwards credential data.
    runtime = await provider.setupBrowserRuntime({ environment });
  } catch {
    throw trustedBrowserError(
      "TB_RUNTIME_UNAVAILABLE",
      "trusted Playwright runtime setup failed at the launch/RPC bridge layer",
    );
  }
  if (!runtime?.browsers || typeof runtime.browsers.getForUrl !== "function") {
    throw trustedBrowserError(
      "TB_RUNTIME_UNAVAILABLE",
      "trusted Playwright browser runtime lacks URL selection",
    );
  }

  const exposedRuntime = {
    browsers: Object.freeze({
      getForUrl: async (origin) => {
        assertCertifiedOrigin(origin);
        let browser;
        try {
          browser = await runtime.browsers.getForUrl(CERTIFIED_ORIGIN);
        } catch {
          throw trustedBrowserError(
            "TB_BROWSER_SELECTION_FAILED",
            "trusted Playwright browser could not select the certified staging origin",
          );
        }
        return createRestrictedBrowser(browser);
      },
    }),
  };
  if (typeof runtime.close === "function") {
    exposedRuntime.close = async () => runtime.close();
  }
  return Object.freeze(exposedRuntime);
}

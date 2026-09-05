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

import { existsSync, lstatSync, realpathSync } from "node:fs";
import { isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import {
  createTrustedRuntimeProvider,
  TRUSTED_BROWSER_ENVIRONMENT,
} from "./runtime-provider.mjs";
import { configuredCertifiedOrigin, parseTrustedOrigin, parseTrustedNavigation } from "./policy/origin-policy.mjs";
import { assertNoSecretFields, isSecretFieldName } from "./policy/secret-fields.mjs";
import { createRuntimePolicy } from "./policy/runtime-policy.mjs";

export { TRUSTED_BROWSER_ENVIRONMENT } from "./runtime-provider.mjs";

export const CERTIFIED_ORIGIN = process.env?.SENTINEL_DNA_CERTIFIED_ORIGIN ||
  process.env?.SENTINEL_DNA_BASE_URL || "";
export const TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV =
  "SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT";
export const BROWSER_AUTH_BRIDGE_ENV = "SENTINEL_DNA_BROWSER_AUTH_BRIDGE";

const REJECTED_BRIDGE_PATH_MARKERS = [
  "/tests/",
  "/test/",
  "/fixtures/",
  "/fixture/",
  "stub",
  "mock",
  "fake",
];

function trustedBrowserError(code, message) {
  const error = new Error(`[${code}] ${message}`);
  // Keep diagnostics allowlisted and free of upstream exception text, paths,
  // environment values, and any other potentially sensitive configuration.
  error.code = code;
  return error;
}

function assertNoCredentialFields(value, seen = new WeakSet()) {
  try {
    assertNoSecretFields(value, seen);
  } catch {
    throw new Error("trusted browser client does not accept credential material");
  }
}

function redact(value, seen = new WeakSet()) {
  if (value === null || typeof value !== "object") return value;
  if (seen.has(value)) return "[cycle omitted]";
  seen.add(value);
  if (Array.isArray(value)) return value.map((item) => redact(item, seen));

  const result = {};
  for (const [key, child] of Object.entries(value)) {
    if (isSecretFieldName(key)) continue;
    result[key] = redact(child, seen);
  }
  return result;
}

function assertCertifiedOrigin(origin) {
  try {
    return parseTrustedOrigin(origin, { certifiedOrigin: configuredCertifiedOrigin() }).origin;
  } catch {
    throw new Error(`trusted browser only permits the certified origin ${CERTIFIED_ORIGIN}`);
  }
}

function assertCertifiedUrl(url) {
  try {
    return parseTrustedNavigation(url, { certifiedOrigin: configuredCertifiedOrigin() });
  } catch {
    throw new Error(`trusted browser navigation is restricted to ${CERTIFIED_ORIGIN}`);
  }
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

function repositoryRoot() {
  return resolve(fileURLToPath(new URL("../../../../", import.meta.url)));
}

function configuredBrowserAuthBridgeUrl() {
  const configured = process.env?.[BROWSER_AUTH_BRIDGE_ENV];
  if (typeof configured !== "string" || !configured.trim()) {
    return { failureCode: "TB_AUTH_BRIDGE_MISSING" };
  }

  const normalized = configured.replaceAll("\\", "/").toLowerCase();
  if (REJECTED_BRIDGE_PATH_MARKERS.some((marker) => normalized.includes(marker))) {
    return { failureCode: "TB_AUTH_BRIDGE_MISSING" };
  }

  try {
    const source = configured.trim().startsWith("file:")
      ? new URL(configured.trim())
      : pathToFileURL(resolve(configured.trim()));
    if (source.protocol !== "file:" || source.search || source.hash || !existsSync(source)) {
      return { failureCode: "TB_AUTH_BRIDGE_MISSING" };
    }
    if (lstatSync(source).isSymbolicLink()) {
      return { failureCode: "TB_AUTH_BRIDGE_MISSING" };
    }
    const target = realpathSync(fileURLToPath(source));
    const repository = realpathSync(repositoryRoot());
    const repositoryRelative = relative(repository, target);
    if (!isAbsolute(repositoryRelative) && !repositoryRelative.startsWith("..")) {
      return { failureCode: "TB_AUTH_BRIDGE_MISSING" };
    }
    return { url: pathToFileURL(target).href };
  } catch {
    return { failureCode: "TB_AUTH_BRIDGE_MISSING" };
  }
}

async function loadBrowserAuthBridge() {
  const configured = configuredBrowserAuthBridgeUrl();
  if (configured.failureCode) return configured;

  try {
    const bridge = await import(configured.url);
    if (typeof bridge.requestBrowserAuth !== "function") {
      return { failureCode: "TB_AUTH_BRIDGE_EXPORT_INVALID" };
    }
    return { bridge };
  } catch {
    return { failureCode: "TB_AUTH_BRIDGE_RUNTIME_FAILED" };
  }
}

function assertUpstreamBrowser(browser) {
  if (!browser || typeof browser.tabs?.new !== "function") {
    throw trustedBrowserError(
      "TB_BROWSER_CONTRACT_FAILED",
      "trusted browser client returned an invalid browser",
    );
  }
}

function createNativePlaywrightBrowserAdapter(browser, authBridgeState, policy) {
  if (
    !browser ||
    typeof browser.newContext !== "function" ||
    typeof browser.close !== "function"
  ) {
    return null;
  }

  return {
    tabs: {
      new: async () => {
        const context = await browser.newContext();
        let page;
        let closed = false;
        const close = async () => {
          if (closed) return;
          closed = true;
          let closeError;
          try {
            if (page && typeof page.close === "function") await page.close();
          } catch (error) {
            closeError = error;
          }
          try {
            if (typeof context.close === "function") await context.close();
          } catch (error) {
            closeError ||= error;
          }
          if (closeError) throw closeError;
        };

        try {
          page = await context.newPage();
          return {
            goto: async (url) => page.goto(await policy.validateNavigation(url)),
            close,
            playwright: {
              locator: (selector) => page.locator(selector),
              evaluate: async (expression, ...args) => {
                assertNoCredentialFields(args);
                return page.evaluate(expression, ...args);
              },
            },
            dom_cua: {
              get_visible_dom: async () => page.evaluate(() => {
                const root = document.body || document.documentElement;
                if (!root) return "";
                const clone = root.cloneNode(true);
                for (const element of clone.querySelectorAll(
                  "script, style, noscript, template",
                )) {
                  element.remove();
                }
                return clone.innerHTML;
              }),
            },
            capabilities: {
              get: async (name) => {
                if (name === "browserAuth") {
                  if (authBridgeState.failureCode) {
                    throw trustedBrowserError(
                      authBridgeState.failureCode,
                      "approved browserAuth capability is unavailable",
                    );
                  }
                  return {
                    request: (request) => authBridgeState.bridge.requestBrowserAuth({
                      page,
                      request,
                      environment: TRUSTED_BROWSER_ENVIRONMENT,
                    }),
                  };
                }
                return undefined;
              },
            },
          };
        } catch (error) {
          await close().catch(() => {});
          throw error;
        }
      },
    },
    close: () => browser.close(),
  };
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
    (typeof tab.playwright?.evaluate !== "function" && typeof tab.playwright?.getTitle !== "function")
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

function createPlaywrightSurface(tab, policy) {
  const playwright = tab.playwright;
  const surface = {
    locator: (selector) => {
      if (typeof selector !== "string" || !selector.trim()) throw new Error("trusted locator selector is invalid");
      const native = playwright.locator(selector);
      if (!native || typeof native !== "object") throw new Error("trusted locator is unavailable");
      const facade = Object.create(null);
      facade.count = () => native.count();
      facade.isVisible = () => native.isVisible();
      facade.innerText = () => native.innerText();
      facade.getAttribute = (attribute) => {
        if (!["aria-label", "name", "role", "type"].includes(attribute)) throw new Error("trusted locator attribute is restricted");
        return native.getAttribute(attribute);
      };
      return Object.freeze(facade);
    },
    // The runner performs page-local, same-origin fetches.  Only the result
    // crosses this service boundary, and secret-shaped fields are removed.
    getTitle: async () => redact(await (playwright.getTitle ? playwright.getTitle() : playwright.evaluate(() => document.title))),
    getVisibleText: async () => redact(await (playwright.getVisibleText ? playwright.getVisibleText() : playwright.evaluate(() => (document.body || document.documentElement)?.innerText || ""))),
    getApprovedAttribute: async (selector, attribute) => {
      if (typeof selector !== "string" || !selector.trim() ||
          !["aria-label", "name", "role", "type"].includes(attribute)) {
        throw new Error("trusted attribute inspection is restricted");
      }
      return redact(await (playwright.getApprovedAttribute
        ? playwright.getApprovedAttribute(selector, attribute)
        : playwright.evaluate((input) => document.querySelector(input.selector)?.getAttribute(input.attribute) ?? null, { selector, attribute })));
    },
    readApprovedDOMState: async () => redact(playwright.readApprovedDOMState
      ? await playwright.readApprovedDOMState()
      : await playwright.evaluate(() => ({
        title: document.title,
        visibleText: (document.body || document.documentElement)?.innerText || "",
      }))),
    requestJson: async ({ path, method = "GET", body = undefined, csrfRequired = false } = {}) => {
      if (typeof path !== "string" || !path.startsWith("/") || path.startsWith("//") ||
          !["GET", "POST"].includes(method) || typeof csrfRequired !== "boolean") {
        throw new Error("trusted same-origin request is invalid");
      }
      policy.parseNavigation(path);
      if (playwright.requestJson) return redact(await playwright.requestJson({ path, method, body, csrfRequired }));
      return redact(await playwright.evaluate(async (input) => {
        const headers = { Accept: "application/json" };
        if (input.body !== undefined) headers["Content-Type"] = "application/json";
        if (input.csrfRequired) {
          const csrfResponse = await fetch("/api/auth/csrf", { credentials: "same-origin" });
          const csrfPayload = await csrfResponse.json().catch(() => ({}));
          if (typeof csrfPayload.csrf_token !== "string") throw new Error("csrf unavailable");
          headers["X-CSRF-Token"] = csrfPayload.csrf_token;
        }
        const response = await fetch(input.path, {
          method: input.method,
          credentials: "same-origin",
          headers,
          body: input.body === undefined ? undefined : JSON.stringify(input.body),
        });
        return { status: response.status, body: await response.json().catch(() => null) };
      }, { path, method, body, csrfRequired }));
    },
  };
  return Object.freeze(surface);
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

function createBrowserAuthCapability(tab, policy) {
  let capabilityPromise;
  return Object.freeze({
    request: async (request) => {
      if (request === null || typeof request !== "object") {
        throw new Error("browserAuth request must be an object");
      }
      try {
        const { securityContext: _securityContext, ...requestWithoutContext } = request;
        assertNoCredentialFields(requestWithoutContext);
      } catch {
        throw trustedBrowserError(
          "TB_CREDENTIAL_FIELD_REJECTED",
          "credential-bearing browser data is not accepted",
        );
      }
      if (policy.production && request.securityContext) {
        try { policy.bindTenant(request.securityContext); } catch {
          throw trustedBrowserError("TB_TENANT_CONTEXT_MISMATCH", "browser authentication context is not authorized");
        }
      }
      if (policy.production && !policy.securityContext) {
        throw trustedBrowserError("TB_AUTH_CAPABILITY_MISSING", "browser authentication security context is unavailable");
      }
      // The credential bridge receives field descriptors and Playwright
      // selectors, never credential values.  Keep this allowlist narrow so a
      // caller cannot smuggle a password, cookie, or token into the bridge.
      if (request.origin !== policy.origin) {
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
        origin: policy.origin,
        fields,
        ...(policy.securityContext ? { securityContext: policy.securityContext } : {}),
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

function createRestrictedTab(tab, policy) {
  assertUpstreamTab(tab);
  const browserAuth = createBrowserAuthCapability(tab, policy);
  const restricted = {
    ...(tab.id === undefined ? {} : { id: tab.id }),
    goto: async (url) => {
      let validated;
      try {
        validated = await policy.validateNavigation(url);
      } catch {
        throw new Error(`trusted browser navigation is restricted to ${policy.origin}`);
      }
      return tab.goto(validated);
    },
    close: typeof tab.close === "function" ? (...args) => tab.close(...args) : undefined,
    playwright: createPlaywrightSurface(tab, policy),
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

function createRestrictedBrowser(browser, authBridgeState, policy) {
  const adaptedBrowser = browser?.tabs?.new
    ? browser
    : createNativePlaywrightBrowserAdapter(browser, authBridgeState, policy);
  assertUpstreamBrowser(adaptedBrowser);
  const restricted = {
    ...(policy.securityContext ? { securityContext: policy.securityContext } : {}),
    tabs: Object.freeze({
      new: async (...args) => {
        if (args.length !== 0) throw new Error("trusted browser tabs.new does not accept options");
        try {
          return createRestrictedTab(await adaptedBrowser.tabs.new(), policy);
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
  if (typeof adaptedBrowser.close === "function") {
    restricted.close = async () => adaptedBrowser.close();
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
  const { tenantContext: _tenantContext, ...credentialCheckedOptions } = options;
  assertNoCredentialFields(credentialCheckedOptions);
  const {
    environment = TRUSTED_BROWSER_ENVIRONMENT,
    upstreamClientModule = undefined,
    certifiedOrigin = undefined,
    tenantContext = undefined,
  } = options;
  if (environment !== TRUSTED_BROWSER_ENVIRONMENT) {
    throw trustedBrowserError(
      "TB_RUNTIME_UNAVAILABLE",
      `trusted browser runtime requires environment ${TRUSTED_BROWSER_ENVIRONMENT}`,
    );
  }

  const policy = createRuntimePolicy({
    certifiedOrigin: configuredCertifiedOrigin(certifiedOrigin),
    tenantContext,
    production: process.env?.SENTINEL_DNA_TRUSTED_BROWSER_PRODUCTION === "true",
  });

  const upstreamUrl = localModuleUrl(
    configuredUpstreamClient(upstreamClientModule),
    TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV,
  );
  const authBridgeState = await loadBrowserAuthBridge();
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
    runtime = await provider.setupBrowserRuntime({
      environment,
      certifiedOrigin: policy.origin,
      tenantContext,
    });
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
        try {
          policy.parseOrigin(origin);
        } catch {
          throw new Error(`trusted browser only permits the certified origin ${policy.origin}`);
        }
        let browser;
        try {
          browser = await runtime.browsers.getForUrl(policy.origin);
        } catch {
          throw trustedBrowserError(
            "TB_BROWSER_SELECTION_FAILED",
            "trusted Playwright browser could not select the certified staging origin",
          );
        }
        try {
          return createRestrictedBrowser(browser, authBridgeState, policy);
        } catch (error) {
          // A custody runtime that returns a non-conforming browser may have
          // launched a real process. Close it before propagating the bounded
          // contract failure; never leave an unowned browser alive.
          if (browser && typeof browser.close === "function") {
            await browser.close().catch(() => {});
          }
          throw error;
        }
      },
    }),
  };
  if (typeof runtime.close === "function") {
    exposedRuntime.close = async () => runtime.close();
  }
  return Object.freeze(exposedRuntime);
}

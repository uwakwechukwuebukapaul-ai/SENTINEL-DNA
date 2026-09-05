/**
 * Operator-approved Playwright runtime adapter for the Sentinel DNA
 * trusted-browser contract.
 *
 * SECURITY MODEL
 * -------------
 * This module is the operator-controlled runtime boundary.
 *
 * It may launch Playwright because it is explicitly configured through
 * SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME.
 *
 * It accepts only:
 *   - environment: "codex-app"
 *   - origin: an activation/deployment-configured HTTPS origin
 *
 * It does not:
 *   - accept arbitrary browser launch options
 *   - accept arbitrary origins
 *   - collect or log credentials
 *   - fabricate browserAuth success
 *   - treat test fixtures as an approved authentication provider
 *
 * browserAuth remains fail-closed unless a separately reviewed operator
 * authentication bridge is configured. The bridge contract is:
 *
 *   export async function requestBrowserAuth({ page, request, environment })
 *
 * `request` contains only certified-origin field descriptors and selectors;
 * credentials are entered by the bridge, outside the Sentinel DNA process.
 * The bridge returns only a non-secret `{ status }` result.
 */

import { existsSync } from "node:fs";
import { chromium } from "playwright";
import {
  createTrustedBrowserDiagnostics,
  TRUSTED_BROWSER_TIMEOUTS,
} from "../../trusted_browser_diagnostics.mjs";
import { parseTrustedOrigin } from "../policy/origin-policy.mjs";
import { resolveAndValidateNetworkTarget } from "../policy/network-policy.mjs";
import { assertNoSecretFields } from "../policy/secret-fields.mjs";
import { createRuntimePolicy } from "../policy/runtime-policy.mjs";

export const APPROVED_PLAYWRIGHT_RUNTIME_ENV =
  "SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME";

export const TRUSTED_BROWSER_ENVIRONMENT = "codex-app";

export const CERTIFIED_ORIGIN = process.env?.SENTINEL_DNA_CERTIFIED_ORIGIN ||
  process.env?.SENTINEL_DNA_BASE_URL || "";

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

function trustedBrowserError(code, message) {
  const error = new Error(`[${code}] ${message}`);
  error.code = code;
  return error;
}

function assertEnvironment(environment) {
  if (environment !== TRUSTED_BROWSER_ENVIRONMENT) {
    throw trustedBrowserError(
      "TB_RUNTIME_UNAVAILABLE",
      `trusted browser runtime requires environment ${TRUSTED_BROWSER_ENVIRONMENT}`,
    );
  }
}

function assertCertifiedOrigin(origin) {
  try {
    return parseTrustedOrigin(origin, { certifiedOrigin: CERTIFIED_ORIGIN }).origin;
  } catch {
    throw trustedBrowserError(
      "TB_ORIGIN_REJECTED",
      "browser runtime requested an uncertified origin",
    );
  }
}

function assertNoCredentialFields(value) {
  try { assertNoSecretFields(value); } catch {
    throw trustedBrowserError("TB_CREDENTIAL_FIELD_REJECTED", "credential-bearing browser data is not accepted");
  }
}

function validateModulePath(value, errorCode) {
  if (typeof value !== "string" || !value.trim()) {
    throw trustedBrowserError(
      errorCode,
      "configured runtime module is missing",
    );
  }

  const normalized = value
    .replaceAll("\\", "/")
    .toLowerCase();

  if (REJECTED_PATH_MARKERS.some((marker) => normalized.includes(marker))) {
    throw trustedBrowserError(
      "TB_PROVIDER_MODULE_MISSING",
      "configured runtime module is not an approved operator module",
    );
  }

  return value.trim();
}

function assertApprovedLocalModule(moduleUrl, errorCode, message) {
  if (
    moduleUrl.protocol !== "file:" ||
    moduleUrl.search ||
    moduleUrl.hash ||
    !existsSync(moduleUrl)
  ) {
    throw trustedBrowserError(errorCode, message);
  }
  return moduleUrl;
}

async function loadAuthBridge(diagnostics) {
  const configured = process.env?.[BROWSER_AUTH_BRIDGE_ENV];

  if (typeof configured !== "string" || !configured.trim()) {
    return Object.freeze({ failureCode: "TB_AUTH_BRIDGE_MISSING" });
  }

  let modulePath;
  try {
    modulePath = validateModulePath(configured, "TB_AUTH_BRIDGE_MISSING");
  } catch {
    return Object.freeze({ failureCode: "TB_AUTH_BRIDGE_MISSING" });
  }

  let moduleUrl;

  try {
    if (modulePath.startsWith("file:")) {
      moduleUrl = new URL(modulePath);
    } else {
      const { resolve } = await import("node:path");
      const { pathToFileURL } = await import("node:url");

      moduleUrl = pathToFileURL(resolve(modulePath));
    }
  } catch {
    return Object.freeze({ failureCode: "TB_AUTH_BRIDGE_MISSING" });
  }

  if (
    moduleUrl.protocol !== "file:" ||
    moduleUrl.search ||
    moduleUrl.hash
  ) {
    return Object.freeze({ failureCode: "TB_AUTH_BRIDGE_MISSING" });
  }

  try {
    assertApprovedLocalModule(
      moduleUrl,
      "TB_AUTH_BRIDGE_MISSING",
      "configured browser authentication bridge is unavailable",
    );
  } catch {
    return Object.freeze({ failureCode: "TB_AUTH_BRIDGE_MISSING" });
  }

  try {
    const bridge = await diagnostics.run(
      "AUTH_BRIDGE",
      "bridge.load",
      () => import(moduleUrl.href),
    );

    if (typeof bridge[BROWSER_AUTH_BRIDGE_EXPORT] !== "function") {
      return Object.freeze({ failureCode: "TB_AUTH_BRIDGE_EXPORT_INVALID" });
    }

    return Object.freeze({ bridge });
  } catch (error) {
    return Object.freeze({
      failureCode: error?.code === "TB_AUTH_BRIDGE_TIMEOUT"
        ? error.code
        : "TB_AUTH_BRIDGE_RUNTIME_FAILED",
    });
  }
}

function sanitizeAuthRequest(request, policy) {
  if (!request || typeof request !== "object" || Array.isArray(request)) {
    throw trustedBrowserError(
      "TB_AUTH_REQUEST_INVALID",
      "browser authentication request must be an object",
    );
  }

  const { securityContext: _securityContext, ...requestWithoutContext } = request;
  assertNoCredentialFields(requestWithoutContext);

  if (request.origin !== policy.origin) {
    throw trustedBrowserError(
      "TB_ORIGIN_REJECTED",
      "browser authentication request targets an uncertified origin",
    );
  }
  if (policy.production) {
    if (!request.securityContext) throw trustedBrowserError("TB_TENANT_CONTEXT_MISMATCH", "browser authentication context is missing");
    try { policy.bindTenant(request.securityContext); } catch {
      throw trustedBrowserError("TB_TENANT_CONTEXT_MISMATCH", "browser authentication context is unauthorized");
    }
  }

  if (!Array.isArray(request.fields) || request.fields.length === 0) {
    throw trustedBrowserError(
      "TB_AUTH_REQUEST_INVALID",
      "browser authentication request must contain fields",
    );
  }

  const fields = request.fields.map((field) => {
    if (!field || typeof field !== "object") {
      throw trustedBrowserError(
        "TB_AUTH_REQUEST_INVALID",
        "browser authentication field descriptor is invalid",
      );
    }

    const safeField = {
      id: field.id,
      label: field.label,
      type: field.type,
      selector: field.selector,
    };

    if (
      typeof safeField.id !== "string" ||
      !safeField.id.trim() ||
      typeof safeField.label !== "string" ||
      !safeField.label.trim() ||
      typeof safeField.type !== "string" ||
      !safeField.type.trim() ||
      typeof safeField.selector !== "string" ||
      !safeField.selector.trim()
    ) {
      throw trustedBrowserError(
        "TB_AUTH_REQUEST_INVALID",
        "browser authentication field descriptor is incomplete",
      );
    }

    if (field.autocomplete !== undefined) {
      safeField.autocomplete = field.autocomplete;
    }

    if (field.required !== undefined) {
      safeField.required = Boolean(field.required);
    }

    return safeField;
  });

  const safeRequest = {
    origin: policy.origin,
    fields,
    ...(policy.securityContext ? { securityContext: policy.securityContext } : {}),
  };

  if (request.submit !== undefined) {
    if (
      !request.submit ||
      typeof request.submit !== "object" ||
      typeof request.submit.selector !== "string" ||
      !request.submit.selector.trim()
    ) {
      throw trustedBrowserError(
        "TB_AUTH_REQUEST_INVALID",
        "browser authentication submit descriptor is invalid",
      );
    }

    safeRequest.submit = {
      selector: request.submit.selector,
    };
  }

  return safeRequest;
}

function createPlaywrightSurface(page) {
  return Object.freeze({
    locator(selector) {
      if (typeof selector !== "string" || !selector.trim()) {
        throw trustedBrowserError(
          "TB_SELECTOR_INVALID",
          "locator selector must be a non-empty string",
        );
      }

      const native = page.locator(selector);
      const facade = Object.create(null);
      facade.count = () => native.count();
      facade.isVisible = () => native.isVisible();
      facade.innerText = () => native.innerText();
      facade.getAttribute = (attribute) => {
        if (!["aria-label", "name", "role", "type"].includes(attribute)) {
          throw trustedBrowserError("TB_ATTRIBUTE_INVALID", "locator attribute is restricted");
        }
        return native.getAttribute(attribute);
      };
      return Object.freeze(facade);
    },

    async getTitle() { return page.title(); },
    async getVisibleText() { return page.locator("body").innerText(); },
    async getApprovedAttribute(selector, attribute) {
      if (typeof selector !== "string" || !selector.trim() ||
          !["aria-label", "name", "role", "type"].includes(attribute)) {
        throw trustedBrowserError("TB_ATTRIBUTE_INVALID", "attribute inspection is restricted");
      }
      return page.locator(selector).getAttribute(attribute);
    },
    async readApprovedDOMState() {
      return { title: await page.title(), visibleText: await page.locator("body").innerText() };
    },
    async requestJson({ path, method = "GET", body = undefined, csrfRequired = false } = {}) {
      if (typeof path !== "string" || !path.startsWith("/") || path.startsWith("//") ||
          !["GET", "POST"].includes(method) || typeof csrfRequired !== "boolean") {
        throw trustedBrowserError("TB_REQUEST_INVALID", "same-origin request is restricted");
      }
      if (method === "POST" && csrfRequired !== true) {
        throw trustedBrowserError("TB_CSRF_REQUIRED", "same-origin writes require CSRF protection");
      }
      return page.evaluate(async (input) => {
        const headers = { Accept: "application/json" };
        if (input.body !== undefined) headers["Content-Type"] = "application/json";
        if (input.csrfRequired) {
          const csrfResponse = await fetch("/api/auth/csrf", { credentials: "same-origin" });
          const csrfPayload = await csrfResponse.json().catch(() => ({}));
          if (typeof csrfPayload.csrf_token !== "string") throw new Error("TB_CSRF_UNAVAILABLE");
          headers["X-CSRF-Token"] = csrfPayload.csrf_token;
        }
        const response = await fetch(input.path, {
          method: input.method,
          credentials: "same-origin",
          headers,
          body: input.body === undefined ? undefined : JSON.stringify(input.body),
        });
        return { status: response.status, body: await response.json().catch(() => null) };
      }, { path, method, body, csrfRequired });
    },
  });
}

async function getVisibleDom(page) {
  return page.evaluate(() => {
    const root = document.body || document.documentElement;

    if (!root) {
      return "";
    }

    const clone = root.cloneNode(true);

    for (const element of clone.querySelectorAll(
      "script, style, noscript, template",
    )) {
      element.remove();
    }

    return clone.innerHTML;
  });
}

function createDomCuaSurface(page) {
  return Object.freeze({
    async get_visible_dom() {
      return getVisibleDom(page);
    },
  });
}

function bridgeFailure(authBridgeState) {
  if (!authBridgeState?.failureCode) return;
  throw trustedBrowserError(
    authBridgeState.failureCode,
    "approved browser authentication bridge is unavailable",
  );
}

function createBrowserAuthCapability(page, authBridgeState, diagnostics, policy) {
  return Object.freeze({
    async request(request) {
      const safeRequest = sanitizeAuthRequest(request, policy);

      bridgeFailure(authBridgeState);
      const authBridge = authBridgeState.bridge;

      try {
        const result = await diagnostics.run(
          "AUTH_BRIDGE",
          "bridge.request",
          () => authBridge[BROWSER_AUTH_BRIDGE_EXPORT]({
            page,
            request: safeRequest,
            environment: TRUSTED_BROWSER_ENVIRONMENT,
          }),
          { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.AUTH_BRIDGE },
        );

        if (!result || typeof result.status !== "string") {
          throw trustedBrowserError(
            "TB_AUTH_BRIDGE_RUNTIME_FAILED",
            "browser authentication bridge returned an invalid result",
          );
        }

        return {
          status: result.status,
        };
      } catch (error) {
        if (
          error?.code === "TB_AUTH_BRIDGE_TIMEOUT" ||
          error?.code === "TB_AUTH_BRIDGE_RUNTIME_FAILED"
        ) {
          throw error;
        }

        throw trustedBrowserError(
          "TB_AUTH_BRIDGE_RUNTIME_FAILED",
          "browser authentication bridge request failed",
        );
      }
    },
  });
}

async function createTrustedTab(context, authBridgeState, diagnostics, policy) {
  let page;

  try {
    page = await diagnostics.run(
      "BROWSER_CREATE",
      "tab.new_page",
      () => context.newPage(),
    );

    const playwrightSurface = createPlaywrightSurface(page);
    const domCuaSurface = createDomCuaSurface(page);
    const browserAuthCapability = createBrowserAuthCapability(
      page,
      authBridgeState,
      diagnostics,
      policy,
    );

    return Object.freeze({
      async goto(url) {
        if (typeof url !== "string" || !url.trim()) {
          throw trustedBrowserError(
            "TB_URL_INVALID",
            "browser navigation URL must be a non-empty string",
          );
        }

        const validatedUrl = await policy.validateNavigation(url);

        await diagnostics.run(
          "STAGING_NAVIGATION",
          "tab.goto",
          () => page.goto(validatedUrl, { timeout: TRUSTED_BROWSER_TIMEOUTS.STAGING_NAVIGATION }),
          { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.STAGING_NAVIGATION },
        );
        if (typeof page.url === "function") policy.parseNavigation(page.url());
      },

      playwright: playwrightSurface,

      dom_cua: domCuaSurface,

      capabilities: Object.freeze({
        async get(name) {
          if (name !== "browserAuth") {
            throw trustedBrowserError(
              "TB_CAPABILITY_UNAVAILABLE",
              "requested browser capability is not approved",
            );
          }

          bridgeFailure(authBridgeState);

          return browserAuthCapability;
        },
      }),

      async close() {
        let closeError;
        try {
          await diagnostics.run("TAB_CLOSE", "tab.page_close", () => page.close());
        } catch (error) {
          closeError = error;
        }
        try {
          await diagnostics.run("TAB_CLOSE", "tab.context_close", () => context.close());
        } catch (error) {
          closeError ||= error;
        }
        if (closeError) throw closeError;
      },
    });
  } catch (error) {
    if (page) {
      await diagnostics.run("TAB_CLOSE", "tab.page_close_after_error", () => page.close()).catch(() => {});
    }

    throw error;
  }
}

function createTrustedBrowser(browser, authBridgeState, diagnostics, policy) {
  return Object.freeze({
    tabs: Object.freeze({
      async new() {
        const context = await diagnostics.run(
          "BROWSER_CREATE",
          "browser.new_context",
          () => browser.newContext(),
        );

        try {
          if (typeof context.route !== "function" && policy.production) {
            throw trustedBrowserError("TB_NETWORK_POLICY_UNAVAILABLE", "browser context cannot enforce request policy");
          }
          if (typeof context.route === "function") {
            await context.route("**/*", async (route) => {
              try {
                const requestUrl = route.request().url();
                await resolveAndValidateNetworkTarget(requestUrl);
                await route.continue();
              } catch {
                await route.abort("blockedbyclient");
              }
            });
          }
          return await createTrustedTab(context, authBridgeState, diagnostics, policy);
        } catch (error) {
          await diagnostics.run("TAB_CLOSE", "context.close_after_error", () => context.close()).catch(() => {});
          throw error;
        }
      },
    }),
    async close() {
      await diagnostics.run("TAB_CLOSE", "browser.close", () => browser.close());
    },
  });
}

export async function setupBrowserRuntime({ environment, certifiedOrigin = CERTIFIED_ORIGIN, tenantContext, securityMode } = {}) {
  assertEnvironment(environment);

  assertNoCredentialFields({ environment, certifiedOrigin });
  const expectedOrigin = assertCertifiedOrigin(certifiedOrigin);
  const policy = createRuntimePolicy({
    certifiedOrigin: expectedOrigin,
    tenantContext,
    production: securityMode === "trusted-rpc",
  });

  const diagnostics = createTrustedBrowserDiagnostics();
  const authBridge = await loadAuthBridge(diagnostics);

  const browser = await diagnostics.run(
    "RUNTIME_SETUP",
    "browser.launch",
    () => chromium.launch({
      headless: true,
      timeout: TRUSTED_BROWSER_TIMEOUTS.RUNTIME_SETUP,
    }),
    { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.RUNTIME_SETUP },
  );

  let closed = false;

  return Object.freeze({
    browsers: Object.freeze({
      async getForUrl(origin) {
        if (closed) {
          throw trustedBrowserError(
            "TB_RUNTIME_UNAVAILABLE",
            "trusted browser runtime has been closed",
          );
        }

        assertCertifiedOrigin(origin);

        return createTrustedBrowser(browser, authBridge, diagnostics, policy);
      },
    }),

    async close() {
      if (closed) {
        return;
      }

      closed = true;
      await diagnostics.run("TAB_CLOSE", "browser.close", () => browser.close()).catch(() => {});
    },
  });
}

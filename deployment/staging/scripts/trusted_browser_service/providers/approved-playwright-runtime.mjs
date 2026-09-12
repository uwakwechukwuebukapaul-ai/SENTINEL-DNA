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
 *   - origin: https://uwakwe-desktop.taile388cc.ts.net
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

export const APPROVED_PLAYWRIGHT_RUNTIME_ENV =
  "SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME";

export const TRUSTED_BROWSER_ENVIRONMENT = "codex-app";

export const CERTIFIED_ORIGIN =
  "https://uwakwe-desktop.taile388cc.ts.net";

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
  if (origin !== CERTIFIED_ORIGIN) {
    throw trustedBrowserError(
      "TB_ORIGIN_REJECTED",
      "browser runtime requested an uncertified origin",
    );
  }
}

function assertNoCredentialFields(value) {
  if (value === null || value === undefined) {
    return;
  }

  if (typeof value === "string") {
    return;
  }

  if (Array.isArray(value)) {
    for (const item of value) {
      assertNoCredentialFields(item);
    }
    return;
  }

  if (typeof value !== "object") {
    return;
  }

  for (const [key, child] of Object.entries(value)) {
    const normalized = key.toLowerCase();

    if (
      normalized.includes("password") ||
      normalized.includes("passwd") ||
      normalized.includes("secret") ||
      normalized.includes("token") ||
      normalized.includes("api_key") ||
      normalized.includes("apikey") ||
      normalized.includes("authorization") ||
      normalized.includes("cookie") ||
      normalized.includes("credential")
    ) {
      throw trustedBrowserError(
        "TB_CREDENTIAL_FIELD_REJECTED",
        "credential-bearing browser data is not accepted",
      );
    }

    assertNoCredentialFields(child);
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

function sanitizeAuthRequest(request) {
  if (!request || typeof request !== "object" || Array.isArray(request)) {
    throw trustedBrowserError(
      "TB_AUTH_REQUEST_INVALID",
      "browser authentication request must be an object",
    );
  }

  assertNoCredentialFields(request);

  if (request.origin !== CERTIFIED_ORIGIN) {
    throw trustedBrowserError(
      "TB_ORIGIN_REJECTED",
      "browser authentication request targets an uncertified origin",
    );
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
    origin: CERTIFIED_ORIGIN,
    fields,
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

      return page.locator(selector);
    },

    async evaluate(expression, ...args) {
      assertNoCredentialFields(args);

      if (typeof expression !== "string" && typeof expression !== "function") {
        throw trustedBrowserError(
          "TB_EVALUATE_INVALID",
          "evaluate expression must be a string or function",
        );
      }

      return page.evaluate(expression, ...args);
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

function createBrowserAuthCapability(page, authBridgeState, diagnostics) {
  return Object.freeze({
    async request(request) {
      const safeRequest = sanitizeAuthRequest(request);

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

async function createTrustedTab(context, authBridgeState, diagnostics) {
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
    );

    return Object.freeze({
      async goto(url) {
        if (typeof url !== "string" || !url.trim()) {
          throw trustedBrowserError(
            "TB_URL_INVALID",
            "browser navigation URL must be a non-empty string",
          );
        }

        const parsed = new URL(url);

        assertCertifiedOrigin(parsed.origin);

        await diagnostics.run(
          "STAGING_NAVIGATION",
          "tab.goto",
          () => page.goto(url, { timeout: TRUSTED_BROWSER_TIMEOUTS.STAGING_NAVIGATION }),
          { timeoutMs: TRUSTED_BROWSER_TIMEOUTS.STAGING_NAVIGATION },
        );
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

function createTrustedBrowser(browser, authBridgeState, diagnostics) {
  return Object.freeze({
    tabs: Object.freeze({
      async new() {
        const context = await diagnostics.run(
          "BROWSER_CREATE",
          "browser.new_context",
          () => browser.newContext(),
        );

        try {
          return await createTrustedTab(context, authBridgeState, diagnostics);
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

export async function setupBrowserRuntime({ environment } = {}) {
  assertEnvironment(environment);

  assertNoCredentialFields({ environment });

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

        return createTrustedBrowser(browser, authBridge, diagnostics);
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

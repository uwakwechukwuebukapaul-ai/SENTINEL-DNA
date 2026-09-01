/**
 * Sentinel DNA staging provider boundary for the reviewed Playwright runtime.
 *
 * This entrypoint is the value for
 * SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT. It does not install or
 * launch Playwright, connect to CDP, make HTTP requests, handle credentials,
 * or log provider errors. The actual browser transport must be supplied by a
 * separately reviewed local runtime module configured through
 * SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME.
 */

import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

export const CERTIFIED_ORIGIN = "https://sentinel-dna-staging:18443";
export const TRUSTED_BROWSER_ENVIRONMENT = "codex-app";
export const APPROVED_PLAYWRIGHT_RUNTIME_ENV =
  "SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME";

const SECRET_KEY_PARTS = new Set([
  "password",
  "secret",
  "token",
  "cookie",
  "authorization",
  "credential",
  "privatekey",
  "sessionid",
  "jwt",
  "bearer",
]);

function trustedProviderError(code, message) {
  const error = new Error(`[${code}] ${message}`);
  error.code = code;
  return error;
}

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
      throw trustedProviderError(
        "TB_PROVIDER_INPUT_REJECTED",
        "trusted browser provider does not accept credential material",
      );
    }
    assertNoCredentialFields(child, seen);
  }
}

function assertEnvironmentOptions(options) {
  if (options === null || typeof options !== "object" || Array.isArray(options)) {
    throw trustedProviderError(
      "TB_RUNTIME_UNAVAILABLE",
      `trusted browser runtime requires environment ${TRUSTED_BROWSER_ENVIRONMENT}`,
    );
  }
  assertNoCredentialFields(options);
  if (options.environment !== TRUSTED_BROWSER_ENVIRONMENT) {
    throw trustedProviderError(
      "TB_RUNTIME_UNAVAILABLE",
      `trusted browser runtime requires environment ${TRUSTED_BROWSER_ENVIRONMENT}`,
    );
  }
}

function configuredRuntimeModule() {
  const configured = process.env?.[APPROVED_PLAYWRIGHT_RUNTIME_ENV];
  if (typeof configured !== "string" || !configured.trim()) {
    throw trustedProviderError(
      "TB_PROVIDER_NOT_CONFIGURED",
      `${APPROVED_PLAYWRIGHT_RUNTIME_ENV} must point to the reviewed Playwright runtime`,
    );
  }
  return configured.trim();
}

function localModuleUrl(modulePath) {
  try {
    const url = modulePath.startsWith("file:")
      ? new URL(modulePath)
      : pathToFileURL(resolve(modulePath));
    if (url.protocol !== "file:" || url.search || url.hash) {
      throw new Error("runtime is not a plain local module");
    }
    return url;
  } catch {
    throw trustedProviderError(
      "TB_PROVIDER_MODULE_MISSING",
      "approved Playwright runtime must be a local reviewed module",
    );
  }
}

function assertCertifiedOrigin(origin) {
  if (typeof origin !== "string") {
    throw trustedProviderError(
      "TB_ORIGIN_REJECTED",
      `trusted browser provider only permits ${CERTIFIED_ORIGIN}`,
    );
  }
  let parsed;
  try {
    parsed = new URL(origin);
  } catch {
    throw trustedProviderError(
      "TB_ORIGIN_REJECTED",
      `trusted browser provider only permits ${CERTIFIED_ORIGIN}`,
    );
  }
  if (
    parsed.origin !== CERTIFIED_ORIGIN ||
    parsed.username ||
    parsed.password ||
    parsed.pathname !== "/" ||
    parsed.search ||
    parsed.hash
  ) {
    throw trustedProviderError(
      "TB_ORIGIN_REJECTED",
      `trusted browser provider only permits ${CERTIFIED_ORIGIN}`,
    );
  }
  return parsed.origin;
}

async function loadApprovedRuntime() {
  const runtimeUrl = localModuleUrl(configuredRuntimeModule());
  if (runtimeUrl.href === import.meta.url) {
    throw trustedProviderError(
      "TB_PROVIDER_MODULE_MISSING",
      "approved Playwright runtime cannot be the provider boundary itself",
    );
  }
  if (!existsSync(runtimeUrl)) {
    throw trustedProviderError(
      "TB_PROVIDER_MODULE_MISSING",
      "approved Playwright runtime module is missing",
    );
  }

  let runtimeModule;
  try {
    runtimeModule = await import(runtimeUrl.href);
  } catch {
    throw trustedProviderError(
      "TB_PROVIDER_MODULE_MISSING",
      "approved Playwright runtime module could not be loaded",
    );
  }
  if (typeof runtimeModule.setupBrowserRuntime !== "function") {
    throw trustedProviderError(
      "TB_PROVIDER_EXPORT_INVALID",
      "approved Playwright runtime must export setupBrowserRuntime",
    );
  }
  return runtimeModule;
}

/**
 * Load the separately reviewed Playwright runtime and expose only certified
 * URL selection to the trusted browser facade.
 */
export async function setupBrowserRuntime(options = {}) {
  assertEnvironmentOptions(options);
  const runtimeModule = await loadApprovedRuntime();

  let runtime;
  try {
    runtime = await runtimeModule.setupBrowserRuntime({
      environment: TRUSTED_BROWSER_ENVIRONMENT,
    });
  } catch {
    throw trustedProviderError(
      "TB_RUNTIME_UNAVAILABLE",
      "approved Playwright runtime setup failed",
    );
  }
  if (!runtime?.browsers || typeof runtime.browsers.getForUrl !== "function") {
    throw trustedProviderError(
      "TB_RUNTIME_UNAVAILABLE",
      "approved Playwright runtime lacks URL selection",
    );
  }

  return Object.freeze({
    browsers: Object.freeze({
      getForUrl: async (origin) => {
        assertCertifiedOrigin(origin);
        try {
          return await runtime.browsers.getForUrl(CERTIFIED_ORIGIN);
        } catch {
          throw trustedProviderError(
            "TB_BROWSER_SELECTION_FAILED",
            "approved Playwright runtime could not select the certified browser",
          );
        }
      },
    }),
  });
}

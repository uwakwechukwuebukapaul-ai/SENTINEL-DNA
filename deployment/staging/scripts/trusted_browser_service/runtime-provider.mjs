/**
 * Production-safe interface for the operator-supplied trusted browser
 * runtime provider.
 *
 * This module is intentionally transport-agnostic. It does not import
 * Playwright, launch a browser, connect to CDP, make HTTP requests, or expose
 * credentials. The provider is the separately reviewed operator module that
 * owns the trusted Playwright/RPC transport.
 */

export const TRUSTED_BROWSER_ENVIRONMENT = "codex-app";

function trustedBrowserError(code, message) {
  const error = new Error(`[${code}] ${message}`);
  error.code = code;
  return error;
}

/**
 * Adapt the reviewed provider export to the one method consumed by the
 * checked-in trusted browser facade.
 *
 * Provider contract:
 *   setupBrowserRuntime({ environment: "codex-app" })
 *     -> { browsers: { getForUrl(origin) } }
 *
 * Only the certified environment is accepted and only that environment is
 * forwarded. No caller-supplied options are passed to the provider.
 */
export function createTrustedRuntimeProvider(provider) {
  if (!provider || typeof provider.setupBrowserRuntime !== "function") {
    throw trustedBrowserError(
      "TB_PROVIDER_EXPORT_INVALID",
      "reviewed browser runtime provider must export setupBrowserRuntime",
    );
  }

  return Object.freeze({
    setupBrowserRuntime: async ({ environment } = {}) => {
      if (environment !== TRUSTED_BROWSER_ENVIRONMENT) {
        throw trustedBrowserError(
          "TB_RUNTIME_UNAVAILABLE",
          `trusted browser runtime requires environment ${TRUSTED_BROWSER_ENVIRONMENT}`,
        );
      }
      try {
        return await provider.setupBrowserRuntime({ environment: TRUSTED_BROWSER_ENVIRONMENT });
      } catch {
        throw trustedBrowserError(
          "TB_RUNTIME_UNAVAILABLE",
          "trusted browser runtime provider setup failed",
        );
      }
    },
  });
}

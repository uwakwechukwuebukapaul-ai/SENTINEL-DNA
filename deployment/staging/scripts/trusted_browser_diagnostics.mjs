import { spawn } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Secret-free diagnostics and bounded operation support for the trusted
 * browser path.  This module never records exception text, URLs, headers,
 * response bodies, or caller data.
 */

export const TRUSTED_BROWSER_TIMEOUTS = Object.freeze({
  PROVIDER_LOAD: 10_000,
  RUNTIME_SETUP: 30_000,
  BROWSER_SELECTION: 10_000,
  BROWSER_CREATE: 15_000,
  STAGING_NAVIGATION: 20_000,
  AUTH_CAPABILITY: 5_000,
  AUTH_BRIDGE: 30_000,
  AUTH_COMPLETE: 15_000,
  TAB_CLOSE: 5_000,
  APPLICATION_REQUEST: 15_000,
  DOM_INSPECTION: 10_000,
  PLAYWRIGHT: 10_000,
});

const PHASE_CODES = Object.freeze({
  PROVIDER_LOAD: "TB_PROVIDER_LOAD",
  RUNTIME_SETUP: "TB_RUNTIME_SETUP",
  BROWSER_SELECTION: "TB_BROWSER_SELECTION",
  BROWSER_CREATE: "TB_BROWSER_CREATE",
  STAGING_NAVIGATION: "TB_STAGING_NAVIGATION",
  AUTH_CAPABILITY: "TB_AUTH_CAPABILITY",
  AUTH_BRIDGE: "TB_AUTH_BRIDGE",
  AUTH_COMPLETE: "TB_AUTH_COMPLETE",
  TAB_CLOSE: "TB_TAB_CLOSE",
  APPLICATION_REQUEST: "TB_APPLICATION_REQUEST",
  DOM_INSPECTION: "TB_DOM_INSPECTION",
  PLAYWRIGHT: "TB_PLAYWRIGHT",
});

const SAFE_CODES = new Set([
  ...Object.values(PHASE_CODES),
  ...Object.values(PHASE_CODES).map((code) => `${code}_TIMEOUT`),
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
  "TB_AUTH_REQUEST_INVALID",
  "TB_CREDENTIAL_FIELD_REJECTED",
  "TB_URL_INVALID",
  "TB_SELECTOR_INVALID",
  "TB_EVALUATE_INVALID",
  "TB_CAPABILITY_UNAVAILABLE",
]);

function phaseCode(phase) {
  return PHASE_CODES[phase] || "TB_RUNTIME_UNAVAILABLE";
}

const PHASE_FAILURE_FALLBACKS = Object.freeze({
  PROVIDER_LOAD: "TB_PROVIDER_MODULE_MISSING",
  RUNTIME_SETUP: "TB_RUNTIME_UNAVAILABLE",
  BROWSER_SELECTION: "TB_BROWSER_SELECTION_FAILED",
  BROWSER_CREATE: "TB_BROWSER_CONTRACT_FAILED",
  AUTH_CAPABILITY: "TB_AUTH_CAPABILITY_MISSING",
});

function safeOperation(operation) {
  return typeof operation === "string" && /^[A-Z0-9_.:-]{1,80}$/i.test(operation)
    ? operation
    : "operation";
}

function safeErrorCode(error, fallback) {
  return SAFE_CODES.has(error?.code) ? error.code : fallback;
}

function timeoutError(phase, operation) {
  const code = `${phaseCode(phase)}_TIMEOUT`;
  const error = new Error(`[${code}] trusted browser operation timed out`);
  error.code = code;
  error.phase = phase;
  error.operation = safeOperation(operation);
  return error;
}

function phaseError(phase, operation, error) {
  const fallback = PHASE_FAILURE_FALLBACKS[phase] || phaseCode(phase);
  const code = safeErrorCode(error, fallback);
  const safe = new Error(`[${code}] trusted browser operation failed`);
  safe.code = code;
  safe.phase = phase;
  safe.operation = safeOperation(operation);
  return safe;
}

function runWithTimeout(work, timeoutMs, phase, operation) {
  const limit = Number.isFinite(timeoutMs) && timeoutMs > 0
    ? Math.floor(timeoutMs)
    : TRUSTED_BROWSER_TIMEOUTS[phase] || 10_000;
  return new Promise((resolve, reject) => {
    let settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      reject(timeoutError(phase, operation));
    }, limit);

    Promise.resolve()
      .then(work)
      .then((value) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve(value);
      }, (error) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        reject(phaseError(phase, operation, error));
      });
  });
}

/**
 * Create a per-run collector.  The collector rethrows safe errors so callers
 * retain fail-closed semantics while still receiving an auditable phase.
 */
export function createTrustedBrowserDiagnostics() {
  const events = [];

  return Object.freeze({
    async run(phase, operation, work, { timeoutMs = undefined } = {}) {
      const started = Date.now();
      const safePhase = Object.prototype.hasOwnProperty.call(PHASE_CODES, phase)
        ? phase
        : "RUNTIME_SETUP";
      const safeOp = safeOperation(operation);
      try {
        const value = await runWithTimeout(
          work,
          timeoutMs ?? TRUSTED_BROWSER_TIMEOUTS[safePhase],
          safePhase,
          safeOp,
        );
        events.push({
          phase: safePhase,
          operation: safeOp,
          duration_ms: Math.max(0, Date.now() - started),
          status: "PASS",
        });
        return value;
      } catch (error) {
        const code = safeErrorCode(error, phaseCode(safePhase));
        events.push({
          phase: safePhase,
          operation: safeOp,
          duration_ms: Math.max(0, Date.now() - started),
          status: "BLOCKED",
          error_category: code,
        });
        throw phaseError(safePhase, safeOp, error);
      }
    },

    snapshot() {
      return events.map((event) => Object.freeze({ ...event }));
    },
  });
}

export function safeTrustedBrowserCode(error, fallback = "TB_RUNTIME_UNAVAILABLE") {
  return safeErrorCode(error, fallback);
}

/**
 * Run the read-only provider verification when this module is used as the
 * operator diagnostic command.  The verifier imports this module, so it runs
 * in a child process to avoid a top-level-await module cycle.  Only the
 * verifier's JSON status object is allowed back across this boundary.
 */
export async function runTrustedBrowserDiagnostics() {
  const verifierPath = fileURLToPath(new URL(
    "./verify_trusted_browser_provider.mjs",
    import.meta.url,
  ));

  return new Promise((resolveResult, rejectResult) => {
    const child = spawn(process.execPath, [verifierPath], {
      env: process.env,
      stdio: ["ignore", "pipe", "ignore"],
    });
    let stdout = "";

    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.on("error", () => {
      rejectResult(new Error("trusted browser verifier could not be started"));
    });
    child.on("close", () => {
      try {
        resolveResult(JSON.parse(stdout));
      } catch {
        rejectResult(new Error("trusted browser verifier returned no safe result"));
      }
    });
  });
}

const invokedAsMain = typeof process !== "undefined" && process.argv?.[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (invokedAsMain) {
  const result = await runTrustedBrowserDiagnostics();
  console.log(JSON.stringify(result, null, 2));
  process.exitCode = result.status === "PASS" ? 0 : 1;
}

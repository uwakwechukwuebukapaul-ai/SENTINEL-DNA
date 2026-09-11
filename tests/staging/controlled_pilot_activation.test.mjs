import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { readFile } from "node:fs/promises";
import { promisify } from "node:util";
import { test } from "node:test";

const execFileAsync = promisify(execFile);
const SCRIPT = "deployment/staging/scripts/check_controlled_pilot_activation.ps1";

async function runActivation(environment, argumentsList = ["-DryRun"]) {
  try {
    const result = await execFileAsync(
      "powershell.exe",
      ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", SCRIPT, ...argumentsList],
      { env: environment, maxBuffer: 100000 },
    );
    return { code: 0, stdout: result.stdout };
  } catch (error) {
    return { code: error.code, stdout: error.stdout || "", stderr: error.stderr || "" };
  }
}

test("activation command fails closed with safe categories when provider is missing", async () => {
  const secret = "secret-token-do-not-print";
  const environment = {
    Path: process.env.Path,
    SystemRoot: process.env.SystemRoot,
    SENTINEL_DNA_IMAGE_DIGEST: secret,
  };
  const result = await runActivation(environment);
  assert.equal(result.code, 1);
  assert.match(result.stdout, /MODE=DRY_RUN/);
  assert.match(result.stdout, /BLOCKED_WITH_REASON/);
  assert.match(result.stdout, /CODE=TB_PROVIDER_MANIFEST_MISSING/);
  assert.match(result.stdout, /CODE=TB_PROVIDER_NOT_CONFIGURED/);
  assert.match(result.stdout, /CODE=TB_RUNTIME_UNAVAILABLE/);
  assert.match(result.stdout, /CODE=TB_IMAGE_IDENTITY_INVALID/);
  assert.doesNotMatch(`${result.stdout}${result.stderr}`, /secret-token-do-not-print/);
  assert.doesNotMatch(`${result.stdout}${result.stderr}`, /password|cookie|authorization/i);
});

test("activation command delegates runtime, manifest, origin, and audit validation", async () => {
  const source = await readFile(SCRIPT, "utf8");
  assert.match(source, /generate_trusted_browser_readiness_report\.mjs/);
  assert.match(source, /check_controlled_pilot_readiness\.mjs/);
  assert.match(source, /SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST/);
  assert.match(source, /SENTINEL_DNA_IMAGE_DIGEST/);
  assert.match(source, /SENTINEL_DNA_TENANT_ISOLATION_ENABLED/);
  assert.match(source, /SENTINEL_DNA_AUDIT_LOGGING_ENABLED/);
  assert.doesNotMatch(source, /browserAuth\.request/);
  assert.doesNotMatch(source, /connectOverCDP|--no-sandbox|ignoreHTTPSErrors/i);
});

test("activation command supports secret-safe JSON status output", async () => {
  const secret = "secret-token-do-not-print";
  const result = await runActivation({
    Path: process.env.Path,
    SystemRoot: process.env.SystemRoot,
    SENTINEL_DNA_IMAGE_DIGEST: secret,
  }, ["-Json", "-DryRun"]);
  assert.equal(result.code, 1);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.status, "BLOCKED_WITH_REASON");
  assert.ok(Array.isArray(payload.codes));
  assert.ok(payload.codes.every((code) => /^TB_[A-Z0-9_]+$/.test(code)));
  assert.doesNotMatch(`${result.stdout}${result.stderr}`, /secret-token-do-not-print|[A-Za-z]:\\/);
});

test("operator readiness artifact is machine-readable and secret-safe", async () => {
  const artifact = JSON.parse(await readFile(
    new URL("../../pilot-evidence/controlled-pilot-readiness-report-20260901T000000Z.json", import.meta.url),
    "utf8",
  ));
  assert.equal(artifact.schema_version, "1.0");
  assert.equal(artifact.final_readiness_decision, "BLOCKED_WITH_REASON");
  for (const field of [
    "manifest_status",
    "provider_status",
    "image_digest_status",
    "origin_status",
    "tenant_isolation_status",
    "audit_status",
  ]) assert.ok(["PASS", "BLOCKED"].includes(artifact[field]));
  assert.doesNotMatch(JSON.stringify(artifact), /[A-Za-z]:\\|\/Users\/|password|cookie|token|authorization|BEGIN PRIVATE KEY/i);
});

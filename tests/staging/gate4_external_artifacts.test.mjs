import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { test } from "node:test";

import {
  verifyConfiguredRuntimeDigest,
  verifyGate4ExternalArtifacts,
} from "../../deployment/staging/scripts/verify_gate4_external_artifacts.mjs";
import {
  APPROVED_RUNTIME_DIGEST_ENV,
} from "../../deployment/staging/scripts/trusted_browser_runtime_custody.mjs";

const ENVIRONMENT_VARIABLES = [
  "SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME",
  "SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST",
  "SENTINEL_DNA_IMAGE_DIGEST",
  "SENTINEL_DNA_BROWSER_AUTH_BRIDGE",
  "SENTINEL_DNA_TRUSTED_BROWSER_CLIENT",
  "SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT",
  APPROVED_RUNTIME_DIGEST_ENV,
];

test("external artifact onboarding remains blocked without custody inputs", { concurrency: false }, async () => {
  const previous = Object.fromEntries(ENVIRONMENT_VARIABLES.map((name) => [name, process.env[name]]));
  for (const name of ENVIRONMENT_VARIABLES) delete process.env[name];
  process.env.SENTINEL_DNA_IMAGE_DIGEST = `sha256:${"a".repeat(64)}`;
  process.env.SENTINEL_DNA_TRUSTED_BROWSER_CLIENT = "deployment/staging/scripts/trusted_browser_service/browser-client.mjs";
  process.env.SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT = "deployment/staging/scripts/trusted_browser_service/providers/playwright-runtime-provider.mjs";
  try {
    const report = await verifyGate4ExternalArtifacts();
    assert.equal(report.status, "BLOCKED_WITH_REASON");
    assert.equal(report.provider_verification.failure_category, "TB_RUNTIME_UNAVAILABLE");
    assert.deepEqual(report.activation.codes, ["TB_PROVIDER_MANIFEST_MISSING", "TB_RUNTIME_UNAVAILABLE"]);
    assert.equal(report.controls.credentials_included, false);
    assert.equal(report.controls.cookies_included, false);
    assert.equal(report.controls.tokens_included, false);
    assert.equal(report.controls.sessions_included, false);
    assert.doesNotMatch(JSON.stringify(report), /password=|secret-token|must-not-escape|C:\\Users\\|\/Users\//i);
  } finally {
    for (const name of ENVIRONMENT_VARIABLES) {
      if (previous[name] === undefined) delete process.env[name];
      else process.env[name] = previous[name];
    }
  }
});

test("external artifact report cannot claim activation from incomplete checks", { concurrency: false }, async () => {
  const previous = Object.fromEntries(ENVIRONMENT_VARIABLES.map((name) => [name, process.env[name]]));
  process.env.SENTINEL_DNA_IMAGE_DIGEST = `sha256:${"a".repeat(64)}`;
  delete process.env.SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME;
  delete process.env.SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST;
  delete process.env.SENTINEL_DNA_TRUSTED_BROWSER_CLIENT;
  delete process.env.SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT;
  try {
    const report = await verifyGate4ExternalArtifacts();
    assert.notEqual(report.activation.status, "READY_FOR_ANALYST_PILOT");
    assert.notDeepEqual(report.activation.codes, []);
  } finally {
    for (const name of ENVIRONMENT_VARIABLES) {
      if (previous[name] === undefined) delete process.env[name];
      else process.env[name] = previous[name];
    }
  }
});

test("runtime digest verification fails closed on a manifest mismatch", { concurrency: false }, async () => {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-onboarding-"));
  const runtimePath = join(directory, "reviewed-runtime.mjs");
  const runtimeSource = "export async function setupBrowserRuntime() { return {}; }\n";
  await writeFile(runtimePath, runtimeSource, "utf8");
  const previous = process.env.SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME;
  const previousOperatorDigest = process.env[APPROVED_RUNTIME_DIGEST_ENV];
  process.env.SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME = runtimePath;
  delete process.env[APPROVED_RUNTIME_DIGEST_ENV];
  const digest = `sha256:${createHash("sha256").update(runtimeSource, "utf8").digest("hex")}`;
  try {
    assert.deepEqual(await verifyConfiguredRuntimeDigest({ approved_runtime_module_digest: digest }), {
      status: "PASS",
      digest,
    });
    assert.deepEqual(await verifyConfiguredRuntimeDigest({ approved_runtime_module_digest: `sha256:${"b".repeat(64)}` }), {
      status: "BLOCKED",
      code: "TB_PROVIDER_MANIFEST_INVALID",
    });
  } finally {
    if (previous === undefined) delete process.env.SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME;
    else process.env.SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME = previous;
    if (previousOperatorDigest === undefined) delete process.env[APPROVED_RUNTIME_DIGEST_ENV];
    else process.env[APPROVED_RUNTIME_DIGEST_ENV] = previousOperatorDigest;
    await rm(directory, { recursive: true, force: true });
  }
});

test("runtime custody reconciles an independent operator digest", { concurrency: false }, async () => {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-runtime-custody-"));
  const runtimePath = join(directory, "reviewed-runtime.mjs");
  const runtimeSource = "export async function setupBrowserRuntime() { return {}; }\n";
  await writeFile(runtimePath, runtimeSource, "utf8");
  const previous = process.env[APPROVED_RUNTIME_DIGEST_ENV];
  const previousRuntime = process.env.SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME;
  process.env.SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME = runtimePath;
  const digest = `sha256:${createHash("sha256").update(runtimeSource, "utf8").digest("hex")}`;
  process.env[APPROVED_RUNTIME_DIGEST_ENV] = digest;
  try {
    assert.deepEqual(await verifyConfiguredRuntimeDigest({ approved_runtime_module_digest: digest }), {
      status: "PASS",
      digest,
    });
    process.env[APPROVED_RUNTIME_DIGEST_ENV] = `sha256:${"c".repeat(64)}`;
    assert.deepEqual(await verifyConfiguredRuntimeDigest({ approved_runtime_module_digest: digest }), {
      status: "BLOCKED",
      code: "TB_PROVIDER_MANIFEST_INVALID",
    });
  } finally {
    if (previous === undefined) delete process.env[APPROVED_RUNTIME_DIGEST_ENV];
    else process.env[APPROVED_RUNTIME_DIGEST_ENV] = previous;
    if (previousRuntime === undefined) delete process.env.SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME;
    else process.env.SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME = previousRuntime;
    await rm(directory, { recursive: true, force: true });
  }
});

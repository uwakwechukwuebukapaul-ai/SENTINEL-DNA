import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { test } from "node:test";

import {
  validateBrowserAuthBridgeModule,
  validateConfiguredBrowserAuthBridge,
} from "../../deployment/staging/scripts/validate_trusted_browser_auth_bridge.mjs";

test("missing operator bridge is blocked", async () => {
  const result = await validateConfiguredBrowserAuthBridge({ modulePath: undefined });
  assert.deepEqual(result, {
    status: "BLOCKED_WITH_REASON",
    checks: { bridge: "FAIL" },
    failure_category: "TB_AUTH_BRIDGE_MISSING",
  });
});

test("bridge without requestBrowserAuth is blocked", async () => {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-auth-harness-invalid-"));
  const modulePath = join(directory, "invalid-bridge.mjs");
  await writeFile(modulePath, "export const notTheBridge = true;\n", "utf8");
  try {
    const result = await validateConfiguredBrowserAuthBridge({ modulePath });
    assert.equal(result.status, "BLOCKED_WITH_REASON");
    assert.equal(result.failure_category, "TB_AUTH_BRIDGE_EXPORT_INVALID");
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test("valid reviewed bridge export shape is accepted without invoking it", () => {
  let invoked = false;
  const result = validateBrowserAuthBridgeModule({
    requestBrowserAuth: () => {
      invoked = true;
    },
  });

  assert.deepEqual(result, { status: "PASS", checks: { bridge: "PASS" } });
  assert.equal(invoked, false);
});

test("bridge module load failures are blocked without exposing module errors", async () => {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-auth-harness-runtime-"));
  const modulePath = join(directory, "runtime-failure.mjs");
  await writeFile(modulePath, "throw new Error('password=must-not-escape');\n", "utf8");
  try {
    const result = await validateConfiguredBrowserAuthBridge({ modulePath });
    assert.equal(result.status, "BLOCKED_WITH_REASON");
    assert.equal(result.failure_category, "TB_AUTH_BRIDGE_RUNTIME_FAILED");
    assert.doesNotMatch(JSON.stringify(result), /password|must-not-escape/i);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

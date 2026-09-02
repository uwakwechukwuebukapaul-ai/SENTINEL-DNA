import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { test } from "node:test";

import {
  createTrustedBrowserDiagnostics,
} from "../../deployment/staging/scripts/trusted_browser_diagnostics.mjs";
import {
  runControlledAnalystPilot,
} from "../../deployment/staging/scripts/controlled_analyst_pilot_runner.mjs";

test("trusted browser diagnostics bound a pending operation and emit no exception text", async () => {
  const diagnostics = createTrustedBrowserDiagnostics();
  const started = Date.now();
  await assert.rejects(
    diagnostics.run("AUTH_BRIDGE", "bridge.request", () => new Promise(() => {}), { timeoutMs: 20 }),
    (error) => {
      assert.equal(error.code, "TB_AUTH_BRIDGE_TIMEOUT");
      assert.equal(error.phase, "AUTH_BRIDGE");
      assert.equal(error.operation, "bridge.request");
      assert.doesNotMatch(error.message, /password|token|cookie|authorization/i);
      return true;
    },
  );
  assert.ok(Date.now() - started < 1000);
  assert.deepEqual(diagnostics.snapshot()[0], {
    phase: "AUTH_BRIDGE",
    operation: "bridge.request",
    duration_ms: diagnostics.snapshot()[0].duration_ms,
    status: "BLOCKED",
    error_category: "TB_AUTH_BRIDGE_TIMEOUT",
  });
});

test("pilot records missing browserAuth, closes its tab, and returns bounded evidence", async () => {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-gate4-runtime-"));
  let closed = 0;
  const locator = {
    count: async () => 1,
    isVisible: async () => true,
    isEnabled: async () => true,
  };
  const browser = {
    tabs: {
      new: async () => ({
        goto: async () => {},
        close: async () => { closed += 1; },
        dom_cua: { get_visible_dom: async () => ({ login: true }) },
        playwright: { locator: () => locator, evaluate: async () => ({}) },
        capabilities: { get: async () => undefined },
      }),
    },
    close: async () => { closed += 1; },
  };
  try {
    const result = await runControlledAnalystPilot({
      browser,
      runId: "gate4-missing-auth",
      evidenceDir: directory,
    });
    assert.equal(result.status, "BLOCKED_WITH_REASON");
    assert.equal(result.results.find((item) => item.check === "trusted_browser_execution").failure_category, "TB_AUTH_CAPABILITY_MISSING");
    assert.equal(closed, 2);
    assert.equal(result.evidence.path.endsWith("controlled-analyst-pilot-gate4-missing-auth.json"), true);
    const evidence = await readFile(result.evidence.path, "utf8");
    assert.match(evidence, /"phase": "AUTH_CAPABILITY"/);
    assert.doesNotMatch(evidence, /"password"\s*:|"token"\s*:|"cookie"\s*:|"authorization"\s*:/i);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test("pilot completes navigation and manager handoff only with a supplied auth capability", async () => {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-gate4-success-"));
  let closed = 0;
  let authRequest;
  const locator = {
    count: async () => 1,
    isVisible: async () => true,
    isEnabled: async () => true,
  };
  const browser = {
    tabs: {
      new: async () => ({
        goto: async (url) => assert.equal(url, "https://uwakwe-desktop.taile388cc.ts.net/login"),
        close: async () => { closed += 1; },
        dom_cua: { get_visible_dom: async () => ({ login: true }) },
        playwright: {
          locator: () => locator,
          evaluate: async (_expression, args) => args.path === "/api/auth/me"
            ? { status: 200, body: { role: "admin" } }
            : { status: 403, body: { error: "forbidden" } },
        },
        capabilities: {
          get: async () => ({
            request: async (request) => {
              authRequest = request;
              return { status: "submitted", token: "not-returned" };
            },
          }),
        },
      }),
    },
    close: async () => { closed += 1; },
  };
  try {
    const result = await runControlledAnalystPilot({
      browser,
      runId: "gate4-success-contract",
      evidenceDir: directory,
    });
    assert.equal(result.status, "BLOCKED_WITH_REASON");
    assert.equal(result.results.find((item) => item.check === "manager_login_session").status, "SUBMITTED");
    assert.equal(typeof authRequest.fields[0].selector, "string");
    assert.equal(typeof authRequest.fields[1].selector, "string");
    assert.equal(typeof authRequest.submit.selector, "string");
    assert.equal(closed, 2);
    const evidence = await readFile(result.evidence.path, "utf8");
    assert.doesNotMatch(evidence, /"token"\s*:/i);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

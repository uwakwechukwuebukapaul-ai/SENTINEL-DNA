import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

import {
  createApprovedBrowser,
  createVerificationBrowser,
  TRUSTED_BROWSER_RUNTIME_ENVIRONMENT,
} from "../../deployment/staging/scripts/trusted_browser_execution_adapter.mjs";

const SYNTHETIC_CERTIFIED_ORIGIN = process.env.SENTINEL_DNA_CERTIFIED_ORIGIN || "https://synthetic-gate4.example.test";

async function withFakeClient(source, callback) {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-browser-adapter-"));
  const modulePath = join(directory, "fake-browser-client.mjs");
  await writeFile(modulePath, source, "utf8");
  try {
    return await callback(modulePath);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

test("creates an approved browser only through the trusted runtime and checks browserAuth", async () => {
  await withFakeClient(`
    export const browser = {
      selectedOrigins: [],
      setupEnvironments: [],
      closedProbeTabs: 0,
      tabs: { new: async () => ({
        goto: async () => {},
        close: async () => { browser.closedProbeTabs += 1; },
        dom_cua: { get_visible_dom: async () => {} },
        playwright: { locator: () => {}, evaluate: async () => {} },
        capabilities: { get: async (name) => name === "browserAuth" ? { request: async () => {} } : undefined },
      }) },
    };
    export async function setupBrowserRuntime(options) {
      browser.setupEnvironments.push(options.environment);
      return { browsers: { getForUrl: async (origin) => { browser.selectedOrigins.push(origin); return browser; } } };
    }
  `, async (modulePath) => {
    const expected = await import(pathToFileURL(modulePath).href);
    const browser = await createVerificationBrowser({ browserClientModule: modulePath });

    assert.strictEqual(browser, expected.browser);
    assert.deepEqual(browser.setupEnvironments, [TRUSTED_BROWSER_RUNTIME_ENVIRONMENT]);
    assert.deepEqual(browser.selectedOrigins, [SYNTHETIC_CERTIFIED_ORIGIN]);
    assert.equal(browser.closedProbeTabs, 1);
  });
});

test("exposes the missing upstream layer through the adapter without secrets", async () => {
  const serviceModule = fileURLToPath(new URL(
    "../../deployment/staging/scripts/trusted_browser_service/browser-client.mjs",
    import.meta.url,
  ));
  const envName = "SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT";
  const previous = process.env[envName];
  delete process.env[envName];
  try {
    await assert.rejects(
      createVerificationBrowser({ browserClientModule: serviceModule }),
      (error) => {
        assert.equal(error.code, "TB_PROVIDER_NOT_CONFIGURED");
        assert.match(error.message, /runtime setup failed at TB_PROVIDER_NOT_CONFIGURED/);
        assert.doesNotMatch(error.message, /password|token|cookie|authorization/i);
        return true;
      },
    );
  } finally {
    if (previous === undefined) delete process.env[envName];
    else process.env[envName] = previous;
  }
});

test("reports an upstream export failure without forwarding upstream error text", async () => {
  await withFakeClient(`export const notSetupBrowserRuntime = true;`, async (modulePath) => {
    await assert.rejects(
      createVerificationBrowser({ browserClientModule: modulePath }),
      (error) => {
        assert.equal(error.code, "TB_PROVIDER_EXPORT_INVALID");
        assert.match(error.message, /does not export setupBrowserRuntime/);
        return true;
      },
    );
  });
});

test("reports Playwright setup and browser selection failures by layer", async () => {
  await withFakeClient(`
    export async function setupBrowserRuntime() {
      throw new Error("password=must-not-escape");
    }
  `, async (modulePath) => {
    await assert.rejects(
      createVerificationBrowser({ browserClientModule: modulePath }),
      (error) => {
        assert.equal(error.code, "TB_RUNTIME_UNAVAILABLE");
        assert.doesNotMatch(error.message, /password|must-not-escape/i);
        return true;
      },
    );
  });

  await withFakeClient(`
    export async function setupBrowserRuntime() {
      return { browsers: { getForUrl: async () => { throw new Error("token=must-not-escape"); } } };
    }
  `, async (modulePath) => {
    await assert.rejects(
      createVerificationBrowser({ browserClientModule: modulePath }),
      (error) => {
        assert.equal(error.code, "TB_BROWSER_SELECTION_FAILED");
        assert.doesNotMatch(error.message, /token|must-not-escape/i);
        return true;
      },
    );
  });
});

test("fails closed when the selected browser has no browserAuth capability", async () => {
  await withFakeClient(`
    export async function setupBrowserRuntime() {
      return { browsers: { getForUrl: async () => ({
        tabs: { new: async () => ({
          goto: async () => {},
          close: async () => {},
          dom_cua: { get_visible_dom: async () => {} },
          playwright: { locator: () => {}, evaluate: async () => {} },
          capabilities: { get: async () => undefined },
        }) },
      }) } };
    }
  `, async (modulePath) => {
    await assert.rejects(
      createVerificationBrowser({ browserClientModule: modulePath }),
      /browserAuth capability/,
    );
  });
});

test("rejects an origin outside the certified staging contract", async () => {
  await assert.rejects(
    createVerificationBrowser({ origin: "https://example.invalid:18443", browserClientModule: "unused" }),
    /certified origin/,
  );
});

test("wrapper delegates browser creation and has no credential CLI inputs", async () => {
  const wrapper = await readFile(new URL("../../deployment/staging/scripts/run_controlled_analyst_pilot.mjs", import.meta.url), "utf8");
  assert.match(wrapper, /createApprovedBrowser/);
  assert.match(wrapper, /checkControlledPilotReadiness/);
  assert.match(wrapper, /TB_PILOT_READINESS_BLOCKED/);
  assert.match(wrapper, /runControlledAnalystPilot\(\{ browser, runId, securityContext \}/);
  assert.doesNotMatch(wrapper, /password|activation[_-]?token|csrf[_-]?token|cookie|authorization/i);
});

test("production caller is RPC-only when the legacy routing flag is absent", async () => {
  const names = ["SENTINEL_DNA_ENV", "SENTINEL_DNA_TRUSTED_BROWSER_PRODUCTION", "SENTINEL_DNA_CERTIFIED_ORIGIN", "SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_KEY", "SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_HOST", "SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_PORT"];
  const previous = Object.fromEntries(names.map((name) => [name, process.env[name]]));
  process.env.SENTINEL_DNA_ENV = "production";
  delete process.env.SENTINEL_DNA_TRUSTED_BROWSER_PRODUCTION;
  process.env.SENTINEL_DNA_CERTIFIED_ORIGIN = SYNTHETIC_CERTIFIED_ORIGIN;
  delete process.env.SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_KEY;
  delete process.env.SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_HOST;
  delete process.env.SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_PORT;
  try {
    await assert.rejects(
      createApprovedBrowser({
        tenantContext: { tenantId: "tenant-a", subjectId: "subject-a", sessionId: "session-a", authorizationContext: "analyst" },
        browserClientModule: fileURLToPath(new URL("./fixtures/trusted-playwright-adapter-stub.mjs", import.meta.url)),
      }),
      (error) => error.code === "TB_RPC_CONFIGURATION_INVALID",
    );
  } finally {
    for (const name of names) {
      if (previous[name] === undefined) delete process.env[name]; else process.env[name] = previous[name];
    }
  }
});

test("configured production caller selects RPC and never imports the local client", async () => {
  const names = ["SENTINEL_DNA_TRUSTED_BROWSER_PRODUCTION", "SENTINEL_DNA_CERTIFIED_ORIGIN", "SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_KEY", "SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_HOST", "SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_PORT"];
  const previous = Object.fromEntries(names.map((name) => [name, process.env[name]]));
  process.env.SENTINEL_DNA_CERTIFIED_ORIGIN = SYNTHETIC_CERTIFIED_ORIGIN;
  delete process.env.SENTINEL_DNA_TRUSTED_BROWSER_PRODUCTION;
  process.env.SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_KEY = "c".repeat(32);
  process.env.SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_HOST = "trusted-browser";
  process.env.SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_PORT = "3000";
  const calls = [];
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async (_url, options) => {
    calls.push(JSON.parse(Buffer.from(options.body).toString("utf8")));
    const operation = calls.at(-1).operation;
    return { ok: true, status: 200, json: async () => ({ ok: true, result: operation === "health" ? { serviceEpoch: "rpc-epoch", status: "ok" } : operation === "create_session" ? { sessionId: "rpc-session", identityBinding: "rpc-identity", serviceEpoch: "rpc-epoch" } : { closed: true } }) };
  };
  try {
    const browser = await createApprovedBrowser({
      tenantContext: { tenantId: "tenant-a", subjectId: "subject-a", sessionId: "session-a", authorizationContext: "analyst" },
      browserClientModule: "this-must-not-be-loaded.mjs",
    });
    assert.equal(calls.find((operation) => operation.operation === "create_session").operation, "create_session");
    await browser.close();
  } finally {
    globalThis.fetch = previousFetch;
    for (const name of names) {
      if (previous[name] === undefined) delete process.env[name]; else process.env[name] = previous[name];
    }
  }
});

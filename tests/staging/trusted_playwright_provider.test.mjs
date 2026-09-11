import assert from "node:assert/strict";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { test } from "node:test";
import { pathToFileURL } from "node:url";

import {
  APPROVED_PLAYWRIGHT_RUNTIME_ENV,
  CERTIFIED_ORIGIN,
  setupBrowserRuntime,
  TRUSTED_BROWSER_ENVIRONMENT,
} from "../../deployment/staging/scripts/trusted_browser_service/providers/playwright-runtime-provider.mjs";
import {
  BROWSER_AUTH_BRIDGE_ENV,
  setupBrowserRuntime as setupApprovedPlaywrightRuntime,
} from "../../deployment/staging/scripts/trusted_browser_service/providers/approved-playwright-runtime.mjs";

async function withRuntime(source, callback) {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-approved-runtime-"));
  const modulePath = join(directory, "approved-runtime.mjs");
  await writeFile(modulePath, source, "utf8");
  const previous = process.env[APPROVED_PLAYWRIGHT_RUNTIME_ENV];
  process.env[APPROVED_PLAYWRIGHT_RUNTIME_ENV] = modulePath;
  try {
    return await callback(modulePath);
  } finally {
    if (previous === undefined) delete process.env[APPROVED_PLAYWRIGHT_RUNTIME_ENV];
    else process.env[APPROVED_PLAYWRIGHT_RUNTIME_ENV] = previous;
    await rm(directory, { recursive: true, force: true });
  }
}

test("loads a valid reviewed runtime provider and selects only the certified origin", async () => {
  await withRuntime(`
    export const state = { setup: [], selected: [] };
    export async function setupBrowserRuntime(options) {
      state.setup.push(options);
      return { browsers: { getForUrl: async (origin) => {
        state.selected.push(origin);
        return { approved: true };
      } } };
    }
  `, async (modulePath) => {
    const approved = await import(`file:///${modulePath.replaceAll("\\", "/")}`);
    const runtime = await setupBrowserRuntime({ environment: TRUSTED_BROWSER_ENVIRONMENT });
    const browser = await runtime.browsers.getForUrl(CERTIFIED_ORIGIN);

    assert.deepEqual(browser, { approved: true });
    assert.deepEqual(approved.state.setup, [{ environment: TRUSTED_BROWSER_ENVIRONMENT }]);
    assert.deepEqual(approved.state.selected, [CERTIFIED_ORIGIN]);
  });
});

test("rejects a non-certified origin before calling the approved runtime", async () => {
  await withRuntime(`
    export async function setupBrowserRuntime() {
      return { browsers: { getForUrl: async () => ({ approved: true }) } };
    }
  `, async () => {
    const runtime = await setupBrowserRuntime({ environment: TRUSTED_BROWSER_ENVIRONMENT });
    await assert.rejects(
      runtime.browsers.getForUrl("https://example.invalid:18443"),
      (error) => {
      assert.equal(error.code, "TB_ORIGIN_REJECTED");
        assert.match(error.message, /only permits/);
        return true;
      },
    );
  });
});

test("rejects an invalid environment before loading a runtime", async () => {
  await assert.rejects(
    setupBrowserRuntime({ environment: "node" }),
    (error) => {
      assert.equal(error.code, "TB_RUNTIME_UNAVAILABLE");
      return true;
    },
  );
});

test("fails closed when the approved runtime is missing", async () => {
  const previous = process.env[APPROVED_PLAYWRIGHT_RUNTIME_ENV];
  process.env[APPROVED_PLAYWRIGHT_RUNTIME_ENV] = join(tmpdir(), "does-not-exist-approved-runtime.mjs");
  try {
    await assert.rejects(
      setupBrowserRuntime({ environment: TRUSTED_BROWSER_ENVIRONMENT }),
      (error) => {
        assert.equal(error.code, "TB_PROVIDER_MODULE_MISSING");
        assert.doesNotMatch(error.message, /does-not-exist-approved-runtime/);
        return true;
      },
    );
  } finally {
    if (previous === undefined) delete process.env[APPROVED_PLAYWRIGHT_RUNTIME_ENV];
    else process.env[APPROVED_PLAYWRIGHT_RUNTIME_ENV] = previous;
  }
});

test("rejects a fixture runtime even when it exports the required contract", async () => {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-runtime-fixture-test-"));
  const fixtureDirectory = join(directory, "fixtures");
  const fixturePath = join(fixtureDirectory, "runtime.mjs");
  const previous = process.env[APPROVED_PLAYWRIGHT_RUNTIME_ENV];
  await mkdir(fixtureDirectory);
  await writeFile(
    fixturePath,
    "export async function setupBrowserRuntime() { return { browsers: { getForUrl: async () => ({}) } }; }\n",
    "utf8",
  );
  process.env[APPROVED_PLAYWRIGHT_RUNTIME_ENV] = fixturePath;
  try {
    await assert.rejects(
      setupBrowserRuntime({ environment: TRUSTED_BROWSER_ENVIRONMENT }),
      (error) => {
        assert.equal(error.code, "TB_PROVIDER_MODULE_MISSING");
        assert.doesNotMatch(error.message, /fixtures|runtime\.mjs/);
        return true;
      },
    );
  } finally {
    if (previous === undefined) delete process.env[APPROVED_PLAYWRIGHT_RUNTIME_ENV];
    else process.env[APPROVED_PLAYWRIGHT_RUNTIME_ENV] = previous;
    await rm(directory, { recursive: true, force: true });
  }
});

test("exposes browserAuth through the approved runtime when its reviewed bridge supports it", { concurrency: false }, async () => {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-auth-bridge-"));
  const bridgePath = join(directory, "browser-auth-bridge.mjs");
  const previous = process.env[BROWSER_AUTH_BRIDGE_ENV];
  await writeFile(
    bridgePath,
    `
      export const state = { requests: [] };
      export async function requestBrowserAuth({ page, request, environment }) {
        state.requests.push({ hasPage: Boolean(page), request, environment });
        return { status: "submitted", token: "never-returned" };
      }
    `,
    "utf8",
  );
  process.env[BROWSER_AUTH_BRIDGE_ENV] = bridgePath;

  let runtime;
  try {
    runtime = await setupApprovedPlaywrightRuntime({ environment: TRUSTED_BROWSER_ENVIRONMENT });
    const browser = await runtime.browsers.getForUrl(CERTIFIED_ORIGIN);
    const tab = await browser.tabs.new();
    const browserAuth = await tab.capabilities.get("browserAuth");

    assert.equal(typeof browserAuth.request, "function");
    assert.deepEqual(
      await browserAuth.request({
        origin: CERTIFIED_ORIGIN,
        fields: [{
          id: "password",
          label: "Password",
          type: "password",
          selector: "#password",
        }],
        submit: { selector: "#submit" },
      }),
      { status: "submitted" },
    );

    const bridge = await import(pathToFileURL(bridgePath).href);
    assert.deepEqual(bridge.state.requests, [{
      hasPage: true,
      request: {
        origin: CERTIFIED_ORIGIN,
        fields: [{
          id: "password",
          label: "Password",
          type: "password",
          selector: "#password",
        }],
        submit: { selector: "#submit" },
      },
      environment: TRUSTED_BROWSER_ENVIRONMENT,
    }]);
    assert.doesNotMatch(JSON.stringify(bridge.state), /never-returned|credential-value|bearer/i);
  } finally {
    if (runtime) await runtime.close().catch(() => {});
    if (previous === undefined) delete process.env[BROWSER_AUTH_BRIDGE_ENV];
    else process.env[BROWSER_AUTH_BRIDGE_ENV] = previous;
    await rm(directory, { recursive: true, force: true });
  }
});

test("keeps the approved runtime blocked when its authentication bridge is missing", { concurrency: false }, async () => {
  const previous = process.env[BROWSER_AUTH_BRIDGE_ENV];
  delete process.env[BROWSER_AUTH_BRIDGE_ENV];
  let runtime;
  try {
    runtime = await setupApprovedPlaywrightRuntime({ environment: TRUSTED_BROWSER_ENVIRONMENT });
    const browser = await runtime.browsers.getForUrl(CERTIFIED_ORIGIN);
    const tab = await browser.tabs.new();
    await assert.rejects(
      tab.capabilities.get("browserAuth"),
      (error) => {
        assert.equal(error.code, "TB_AUTH_BRIDGE_MISSING");
        assert.doesNotMatch(error.message, /password|token|cookie|authorization/i);
        return true;
      },
    );
  } finally {
    if (runtime) await runtime.close().catch(() => {});
    if (previous === undefined) delete process.env[BROWSER_AUTH_BRIDGE_ENV];
    else process.env[BROWSER_AUTH_BRIDGE_ENV] = previous;
  }
});

test("rejects a bridge without requestBrowserAuth", { concurrency: false }, async () => {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-auth-bridge-invalid-"));
  const bridgePath = join(directory, "browser-auth-bridge.mjs");
  const previous = process.env[BROWSER_AUTH_BRIDGE_ENV];
  await writeFile(bridgePath, "export const notTheAuthBridge = true;\n", "utf8");
  process.env[BROWSER_AUTH_BRIDGE_ENV] = bridgePath;
  let runtime;
  try {
    runtime = await setupApprovedPlaywrightRuntime({ environment: TRUSTED_BROWSER_ENVIRONMENT });
    const tab = await (await runtime.browsers.getForUrl(CERTIFIED_ORIGIN)).tabs.new();
    await assert.rejects(
      tab.capabilities.get("browserAuth"),
      (error) => {
        assert.equal(error.code, "TB_AUTH_BRIDGE_EXPORT_INVALID");
        assert.doesNotMatch(error.message, /browser-auth-bridge|notTheAuthBridge/i);
        return true;
      },
    );
  } finally {
    if (runtime) await runtime.close().catch(() => {});
    if (previous === undefined) delete process.env[BROWSER_AUTH_BRIDGE_ENV];
    else process.env[BROWSER_AUTH_BRIDGE_ENV] = previous;
    await rm(directory, { recursive: true, force: true });
  }
});

test("rejects a fixture path configured as the browser authentication bridge", { concurrency: false }, async () => {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-auth-bridge-fixture-"));
  const fixtureDirectory = join(directory, "fixtures");
  const bridgePath = join(fixtureDirectory, "browser-auth-bridge.mjs");
  const previous = process.env[BROWSER_AUTH_BRIDGE_ENV];
  await mkdir(fixtureDirectory);
  await writeFile(
    bridgePath,
    "export async function requestBrowserAuth() { return { status: 'submitted' }; }\n",
    "utf8",
  );
  process.env[BROWSER_AUTH_BRIDGE_ENV] = bridgePath;
  let runtime;
  try {
    runtime = await setupApprovedPlaywrightRuntime({ environment: TRUSTED_BROWSER_ENVIRONMENT });
    const tab = await (await runtime.browsers.getForUrl(CERTIFIED_ORIGIN)).tabs.new();
    await assert.rejects(
      tab.capabilities.get("browserAuth"),
      (error) => {
        assert.equal(error.code, "TB_AUTH_BRIDGE_MISSING");
        assert.doesNotMatch(error.message, /fixtures|browser-auth-bridge/i);
        return true;
      },
    );
  } finally {
    if (runtime) await runtime.close().catch(() => {});
    if (previous === undefined) delete process.env[BROWSER_AUTH_BRIDGE_ENV];
    else process.env[BROWSER_AUTH_BRIDGE_ENV] = previous;
    await rm(directory, { recursive: true, force: true });
  }
});

test("maps bridge execution errors to a safe runtime failure", { concurrency: false }, async () => {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-auth-bridge-failure-"));
  const bridgePath = join(directory, "browser-auth-bridge.mjs");
  const previous = process.env[BROWSER_AUTH_BRIDGE_ENV];
  await writeFile(
    bridgePath,
    "export async function requestBrowserAuth() { throw new Error('password=must-not-escape'); }\n",
    "utf8",
  );
  process.env[BROWSER_AUTH_BRIDGE_ENV] = bridgePath;
  let runtime;
  try {
    runtime = await setupApprovedPlaywrightRuntime({ environment: TRUSTED_BROWSER_ENVIRONMENT });
    const tab = await (await runtime.browsers.getForUrl(CERTIFIED_ORIGIN)).tabs.new();
    const browserAuth = await tab.capabilities.get("browserAuth");
    await assert.rejects(
      browserAuth.request({
        origin: CERTIFIED_ORIGIN,
        fields: [{ id: "username", label: "Username", type: "text", selector: "#username" }],
      }),
      (error) => {
        assert.equal(error.code, "TB_AUTH_BRIDGE_RUNTIME_FAILED");
        assert.doesNotMatch(error.message, /password|must-not-escape/i);
        return true;
      },
    );
  } finally {
    if (runtime) await runtime.close().catch(() => {});
    if (previous === undefined) delete process.env[BROWSER_AUTH_BRIDGE_ENV];
    else process.env[BROWSER_AUTH_BRIDGE_ENV] = previous;
    await rm(directory, { recursive: true, force: true });
  }
});

test("fails closed when the approved runtime lacks browser selection", async () => {
  await withRuntime(`
    export async function setupBrowserRuntime() {
      return { browsers: {} };
    }
  `, async () => {
    await assert.rejects(
      setupBrowserRuntime({ environment: TRUSTED_BROWSER_ENVIRONMENT }),
      (error) => {
        assert.equal(error.code, "TB_RUNTIME_UNAVAILABLE");
        return true;
      },
    );
  });
});

test("does not expose provider exceptions or accept credential-shaped options", async () => {
  await withRuntime(`
    export async function setupBrowserRuntime() {
      throw new Error("password=must-not-escape");
    }
  `, async () => {
    await assert.rejects(
      setupBrowserRuntime({ environment: TRUSTED_BROWSER_ENVIRONMENT }),
      (error) => {
        assert.equal(error.code, "TB_RUNTIME_UNAVAILABLE");
        assert.doesNotMatch(error.message, /password|must-not-escape/i);
        return true;
      },
    );
  });

  await assert.rejects(
    setupBrowserRuntime({ environment: TRUSTED_BROWSER_ENVIRONMENT, token: "must-not-accept" }),
    (error) => {
      assert.equal(error.code, "TB_PROVIDER_INPUT_REJECTED");
      assert.doesNotMatch(error.message, /must-not-accept/);
      return true;
    },
  );
});

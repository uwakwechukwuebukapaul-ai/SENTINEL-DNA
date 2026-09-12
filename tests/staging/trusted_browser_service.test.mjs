import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

import {
  CERTIFIED_ORIGIN,
  setupBrowserRuntime,
} from "../../deployment/staging/scripts/trusted_browser_service/browser-client.mjs";
import {
  createTrustedRuntimeProvider,
  TRUSTED_BROWSER_ENVIRONMENT,
} from "../../deployment/staging/scripts/trusted_browser_service/runtime-provider.mjs";

const EXTERNAL_CUSTODY_RUNTIME =
  "C:\\sentinel-dna-gate4-custody\\approved-playwright-runtime.mjs";

async function withFakeUpstream(source, callback) {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-trusted-browser-"));
  const modulePath = join(directory, "upstream-browser-client.mjs");
  await writeFile(modulePath, source, "utf8");
  try {
    return await callback(modulePath);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

test("adapts a valid runtime provider and forwards only the certified environment", async () => {
  const calls = [];
  const provider = createTrustedRuntimeProvider({
    setupBrowserRuntime: async (options) => {
      calls.push(options);
      return { browsers: { getForUrl: async () => ({}) } };
    },
  });
  const runtime = await provider.setupBrowserRuntime({
    environment: TRUSTED_BROWSER_ENVIRONMENT,
    metadata: { token: "must-not-forward" },
  });

  assert.equal(typeof runtime.browsers.getForUrl, "function");
  assert.deepEqual(calls, [{ environment: TRUSTED_BROWSER_ENVIRONMENT }]);
});

test("fails closed when the runtime provider is missing", async () => {
  assert.throws(
    () => createTrustedRuntimeProvider(undefined),
    (error) => {
      assert.equal(error.code, "TB_PROVIDER_EXPORT_INVALID");
      assert.match(error.message, /must export setupBrowserRuntime/);
      return true;
    },
  );
});

test("runtime provider sanitizes setup errors before they cross its interface", async () => {
  const provider = createTrustedRuntimeProvider({
    setupBrowserRuntime: async () => {
      throw new Error("password=must-not-escape");
    },
  });

  await assert.rejects(
    provider.setupBrowserRuntime({ environment: TRUSTED_BROWSER_ENVIRONMENT }),
    (error) => {
      assert.equal(error.code, "TB_RUNTIME_UNAVAILABLE");
      assert.doesNotMatch(error.message, /password|must-not-escape/i);
      return true;
    },
  );
});

test("reports a missing upstream client without exposing its path", async () => {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-missing-upstream-"));
  const missingPath = join(directory, "reviewed-browser-client.mjs");
  try {
    await assert.rejects(
      setupBrowserRuntime({ upstreamClientModule: missingPath }),
      (error) => {
        assert.equal(error.code, "TB_PROVIDER_MODULE_MISSING");
        assert.match(error.message, /provider.*module.*missing/i);
        assert.doesNotMatch(error.message, /reviewed-browser-client|sentinel-dna-missing-upstream/);
        return true;
      },
    );
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test("rejects an invalid runtime environment before upstream loading", async () => {
  await assert.rejects(
    setupBrowserRuntime({ environment: "node" }),
    (error) => {
      assert.equal(error.code, "TB_RUNTIME_UNAVAILABLE");
      assert.match(error.message, /requires environment codex-app/);
      return true;
    },
  );
});

test("creates a runtime from the repository's staging-only adapter stub", async () => {
  const modulePath = fileURLToPath(new URL("./fixtures/trusted-playwright-adapter-stub.mjs", import.meta.url));
  const upstream = await import(pathToFileURL(modulePath).href);
  upstream.state.selectedOrigins.length = 0;
  const runtime = await setupBrowserRuntime({ upstreamClientModule: modulePath });
  const browser = await runtime.browsers.getForUrl(CERTIFIED_ORIGIN);
  const tab = await browser.tabs.new();

  assert.deepEqual(upstream.state.selectedOrigins, [CERTIFIED_ORIGIN]);
  assert.equal(typeof tab.goto, "function");
  assert.equal(typeof tab.dom_cua.get_visible_dom, "function");
  assert.equal(typeof tab.playwright.locator, "function");
  assert.equal(typeof tab.playwright.evaluate, "function");
  assert.equal(typeof (await tab.capabilities.get("browserAuth")).request, "function");
});

test("adapts the operator custody runtime's native Playwright browser contract", {
  skip: !existsSync(EXTERNAL_CUSTODY_RUNTIME),
}, async () => {
  const runtime = await setupBrowserRuntime({
    upstreamClientModule: EXTERNAL_CUSTODY_RUNTIME,
  });
  let browser;
  let tab;

  try {
    browser = await runtime.browsers.getForUrl(CERTIFIED_ORIGIN);
    tab = await browser.tabs.new();

    assert.equal(typeof tab.goto, "function");
    assert.equal(typeof tab.playwright.locator, "function");
    assert.equal(typeof tab.playwright.evaluate, "function");
    assert.equal(typeof tab.dom_cua.get_visible_dom, "function");
    assert.equal(typeof tab.capabilities.get, "function");
    assert.equal(await tab.playwright.evaluate(() => document.title), "");
    await assert.rejects(
      tab.capabilities.get("browserAuth"),
      (error) => error.code === "TB_AUTH_BRIDGE_MISSING",
    );
  } finally {
    if (tab) await tab.close().catch(() => {});
    if (browser) await browser.close().catch(() => {});
    if (typeof runtime.close === "function") await runtime.close().catch(() => {});
  }
});

test("selects only the certified origin and exposes the runner contract", async () => {
  await withFakeUpstream(`
    export const state = { selected: [], navigated: [], authRequests: [] };
    const tab = {
      id: "tab-1",
      goto: async (url) => state.navigated.push(url),
      close: async () => {},
      playwright: {
        locator: (selector) => ({ selector }),
        evaluate: async () => ({ status: 200, body: { safe: true } }),
      },
      dom_cua: { get_visible_dom: async () => ({ safe: true }) },
      capabilities: {
        get: async (name) => name === "browserAuth" ? {
          request: async (request) => {
            state.authRequests.push(request);
            return { status: "submitted", password: "never-forwarded" };
          },
        } : undefined,
      },
    };
    export const browser = { tabs: { new: async () => tab } };
    export async function setupBrowserRuntime() {
      return { browsers: { getForUrl: async (origin) => {
        state.selected.push(origin);
        return browser;
      } } };
    }
  `, async (modulePath) => {
    const upstream = await import(pathToFileURL(modulePath).href);
    const runtime = await setupBrowserRuntime({ upstreamClientModule: modulePath });
    const browser = await runtime.browsers.getForUrl(CERTIFIED_ORIGIN);
    const tab = await browser.tabs.new();

    assert.deepEqual(upstream.state.selected, [CERTIFIED_ORIGIN]);
    assert.equal(typeof tab.playwright.locator, "function");
    assert.equal(typeof tab.playwright.evaluate, "function");
    assert.equal(typeof tab.dom_cua.get_visible_dom, "function");
    assert.equal(typeof tab.capabilities.get, "function");
    assert.deepEqual(Object.keys(tab).sort(), [
      "capabilities",
      "close",
      "dom_cua",
      "goto",
      "id",
      "playwright",
    ]);
    assert.equal(typeof (await tab.capabilities.get("browserAuth")).request, "function");
    assert.equal(await tab.capabilities.get("unapprovedCapability"), undefined);

    await tab.goto(`${CERTIFIED_ORIGIN}/login`);
    assert.deepEqual(upstream.state.navigated, [`${CERTIFIED_ORIGIN}/login`]);

    const auth = await tab.capabilities.get("browserAuth");
    const result = await auth.request({
      origin: CERTIFIED_ORIGIN,
      fields: [{
        id: "password",
        label: "Password",
        type: "password",
        required: true,
        selector: "#password",
      }],
      submit: { action: "click", selector: "#submit" },
    });
    assert.deepEqual(result, { status: "submitted" });
    assert.deepEqual(Object.keys(result), ["status"]);
    assert.equal(Object.prototype.hasOwnProperty.call(result, "password"), false);
    assert.equal(typeof upstream.state.authRequests[0].fields[0].selector, "string");
    assert.equal(typeof upstream.state.authRequests[0].submit.selector, "string");

    await assert.rejects(
      auth.request({
        origin: CERTIFIED_ORIGIN,
        fields: [{
          id: "password",
          label: "Password",
          type: "password",
          selector: { locator: "#password" },
        }],
      }),
      /field descriptor is invalid/,
    );
  });
});

test("fails closed for non-certified origins and external navigation", async () => {
  await withFakeUpstream(`
    export async function setupBrowserRuntime() {
      return { browsers: { getForUrl: async () => ({
        tabs: { new: async () => ({
          goto: async () => {},
          playwright: { locator: () => ({}), evaluate: async () => ({}) },
          dom_cua: { get_visible_dom: async () => ({}) },
          capabilities: { get: async () => ({ request: async () => ({ status: "submitted" }) }) },
        }) },
      }) } };
    }
  `, async (modulePath) => {
    const runtime = await setupBrowserRuntime({ upstreamClientModule: modulePath });
    await assert.rejects(
      runtime.browsers.getForUrl("https://example.invalid:18443"),
      /certified origin/,
    );
    const tab = await (await runtime.browsers.getForUrl(CERTIFIED_ORIGIN)).tabs.new();
    await assert.rejects(
      tab.goto("https://example.invalid/credential-capture"),
      /restricted to/,
    );
  });
});

test("redacts secret-shaped evaluation and DOM fields", async () => {
  await withFakeUpstream(`
    export async function setupBrowserRuntime() {
      return { browsers: { getForUrl: async () => ({
        tabs: { new: async () => ({
          goto: async () => {},
          playwright: {
            locator: () => ({}),
            evaluate: async () => ({
              accessToken: "hidden",
              nested: { session_cookie: "hidden", reference: "kept" },
            }),
          },
          dom_cua: { get_visible_dom: async () => ({ password: "hidden", label: "Login" }) },
          capabilities: { get: async () => ({ request: async () => ({ status: "submitted" }) }) },
        }) },
      }) } };
    }
  `, async (modulePath) => {
    const runtime = await setupBrowserRuntime({ upstreamClientModule: modulePath });
    const tab = await (await runtime.browsers.getForUrl(CERTIFIED_ORIGIN)).tabs.new();
    assert.deepEqual(await tab.playwright.evaluate(() => ({})), {
      nested: { reference: "kept" },
    });
    assert.deepEqual(await tab.dom_cua.get_visible_dom(), { label: "Login" });
  });
});

test("fails closed when an upstream tab lacks a required capability surface", async () => {
  await withFakeUpstream(`
    export async function setupBrowserRuntime() {
      return { browsers: { getForUrl: async () => ({
        tabs: { new: async () => ({
          goto: async () => {},
          playwright: { locator: () => {}, evaluate: async () => ({}) },
          capabilities: { get: async () => undefined },
        }) },
      }) } };
    }
  `, async (modulePath) => {
    const runtime = await setupBrowserRuntime({ upstreamClientModule: modulePath });
    const browser = await runtime.browsers.getForUrl(CERTIFIED_ORIGIN);
    await assert.rejects(
      browser.tabs.new(),
      (error) => {
        assert.equal(error.code, "TB_BROWSER_CONTRACT_FAILED");
        assert.match(error.message, /visible DOM inspection/);
        return true;
      },
    );
  });
});

test("does not accept credential-shaped setup options", async () => {
  await assert.rejects(
    setupBrowserRuntime({ password: "should-not-be-accepted" }),
    /does not accept credential material/,
  );
});

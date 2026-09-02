import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

import {
  TRUSTED_BROWSER_CLIENT_ENV,
} from "../../deployment/staging/scripts/trusted_browser_execution_adapter.mjs";
import {
  TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV,
} from "../../deployment/staging/scripts/trusted_browser_service/browser-client.mjs";
import {
  APPROVED_PLAYWRIGHT_RUNTIME_ENV,
  CERTIFIED_ORIGIN,
  setupBrowserRuntime as setupProviderRuntime,
  TRUSTED_BROWSER_ENVIRONMENT,
} from "../../deployment/staging/scripts/trusted_browser_service/providers/playwright-runtime-provider.mjs";
import { verifyTrustedBrowserProvider } from "../../deployment/staging/scripts/verify_trusted_browser_provider.mjs";

const SERVICE_MODULE = fileURLToPath(new URL(
  "../../deployment/staging/scripts/trusted_browser_service/browser-client.mjs",
  import.meta.url,
));
const PROVIDER_MODULE = fileURLToPath(new URL(
  "../../deployment/staging/scripts/trusted_browser_service/providers/playwright-runtime-provider.mjs",
  import.meta.url,
));

const VALID_RUNTIME = `
  export async function setupBrowserRuntime({ environment }) {
    if (environment !== "codex-app") throw new Error("unexpected environment");
    const tab = {
      goto: async () => {},
      close: async () => {},
      playwright: { locator: () => ({}), evaluate: async () => ({ safe: true }) },
      dom_cua: { get_visible_dom: async () => ({ safe: true }) },
      capabilities: { get: async (name) => name === "browserAuth" ? { request: async () => ({ status: "not-called" }) } : undefined },
    };
    return { browsers: { getForUrl: async (origin) => {
      if (origin !== "https://sentinel-dna-staging:18443") throw new Error("origin rejected");
      return { tabs: { new: async () => tab } };
    } } };
  }
`;

async function withConfiguration({ runtimeSource = VALID_RUNTIME, upstreamPath = PROVIDER_MODULE }, callback) {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-provider-verification-"));
  const runtimePath = join(directory, "approved-runtime.mjs");
  await writeFile(runtimePath, runtimeSource, "utf8");
  const names = [
    TRUSTED_BROWSER_CLIENT_ENV,
    TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV,
    APPROVED_PLAYWRIGHT_RUNTIME_ENV,
  ];
  const previous = Object.fromEntries(names.map((name) => [name, process.env[name]]));
  process.env[TRUSTED_BROWSER_CLIENT_ENV] = SERVICE_MODULE;
  process.env[TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV] = upstreamPath;
  process.env[APPROVED_PLAYWRIGHT_RUNTIME_ENV] = runtimePath;
  try {
    return await callback({ runtimePath, directory });
  } finally {
    for (const name of names) {
      if (previous[name] === undefined) delete process.env[name];
      else process.env[name] = previous[name];
    }
    await rm(directory, { recursive: true, force: true });
  }
}

test("verifies a complete configured provider chain", async () => {
  await withConfiguration({}, async () => {
    const result = await verifyTrustedBrowserProvider();
    assert.deepEqual(result, {
      status: "PASS",
      checks: {
        provider: "PASS",
        runtime: "PASS",
        origin: "PASS",
        browser_contract: "PASS",
        browser_auth: "PASS",
      },
    });
  });
});

test("reports a missing provider without exposing configuration paths", async () => {
  await withConfiguration({}, async () => {
    const previous = process.env[TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV];
    delete process.env[TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV];
    try {
      const result = await verifyTrustedBrowserProvider();
      assert.equal(result.status, "BLOCKED_WITH_REASON");
      assert.equal(result.failure_category, "TB_PROVIDER_NOT_CONFIGURED");
      assert.equal(result.checks.provider, "FAIL");
      assert.doesNotMatch(JSON.stringify(result), /sentinel-dna-provider-verification|approved-runtime/);
    } finally {
      process.env[TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV] = previous;
    }
  });
});

test("reports an invalid provider export", async () => {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-invalid-provider-"));
  const invalidPath = join(directory, "invalid-provider.mjs");
  await writeFile(invalidPath, "export const notSetupBrowserRuntime = true;", "utf8");
  try {
    await withConfiguration({ upstreamPath: invalidPath }, async () => {
      const result = await verifyTrustedBrowserProvider();
      assert.equal(result.status, "BLOCKED_WITH_REASON");
      assert.equal(result.failure_category, "TB_PROVIDER_EXPORT_INVALID");
      assert.equal(result.checks.provider, "FAIL");
    });
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test("reports an unavailable runtime without leaking provider errors", async () => {
  await withConfiguration({
    runtimeSource: `export async function setupBrowserRuntime() { throw new Error("password=must-not-escape"); }`,
  }, async () => {
    const result = await verifyTrustedBrowserProvider();
    assert.equal(result.status, "BLOCKED_WITH_REASON");
    assert.equal(result.failure_category, "TB_RUNTIME_UNAVAILABLE");
    assert.equal(result.checks.runtime, "FAIL");
    assert.doesNotMatch(JSON.stringify(result), /password|must-not-escape/);
  });
});

test("reports browser contract failure", async () => {
  await withConfiguration({
    runtimeSource: `
      export async function setupBrowserRuntime() {
        return { browsers: { getForUrl: async () => ({ tabs: { new: async () => ({ goto: async () => {} }) } }) } };
      }
    `,
  }, async () => {
    const result = await verifyTrustedBrowserProvider();
    assert.equal(result.status, "BLOCKED_WITH_REASON");
    assert.equal(result.failure_category, "TB_BROWSER_CONTRACT_FAILED");
    assert.equal(result.checks.browser_contract, "FAIL");
  });
});

test("reports missing browserAuth separately from the browser contract", async () => {
  await withConfiguration({
    runtimeSource: VALID_RUNTIME.replace(
      'name === "browserAuth" ? { request: async () => ({ status: "not-called" }) } : undefined',
      "false ? { request: async () => ({ status: \"not-called\" }) } : undefined",
    ),
  }, async () => {
    const result = await verifyTrustedBrowserProvider();
    assert.equal(result.status, "BLOCKED_WITH_REASON");
    assert.equal(result.failure_category, "TB_AUTH_CAPABILITY_MISSING");
    assert.equal(result.checks.browser_contract, "PASS");
    assert.equal(result.checks.browser_auth, "FAIL");
  });
});

test("closes the selected browser after provider verification", async () => {
  await withConfiguration({
    runtimeSource: `
      export const state = { closed: 0 };
      const tab = {
        goto: async () => {},
        close: async () => {},
        playwright: { locator: () => ({}), evaluate: async () => ({}) },
        dom_cua: { get_visible_dom: async () => ({}) },
        capabilities: { get: async () => ({ request: async () => ({ status: "not-called" }) }) },
      };
      const browser = {
        tabs: { new: async () => tab },
        close: async () => { state.closed += 1; },
      };
      export async function setupBrowserRuntime() {
        return { browsers: { getForUrl: async () => browser } };
      }
    `,
  }, async ({ runtimePath }) => {
    const runtime = await import(pathToFileURL(runtimePath).href);
    const result = await verifyTrustedBrowserProvider();
    assert.equal(result.status, "PASS");
    assert.equal(runtime.state.closed, 1);
  });
});

test("provider rejects a non-certified origin", async () => {
  await withConfiguration({}, async () => {
    const runtime = await setupProviderRuntime({ environment: TRUSTED_BROWSER_ENVIRONMENT });
    await assert.rejects(
      runtime.browsers.getForUrl("https://example.invalid:18443"),
      (error) => {
        assert.equal(error.code, "TB_ORIGIN_REJECTED");
        return true;
      },
    );
  });
});

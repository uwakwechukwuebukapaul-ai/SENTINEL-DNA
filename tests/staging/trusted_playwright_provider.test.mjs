import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { test } from "node:test";

import {
  APPROVED_PLAYWRIGHT_RUNTIME_ENV,
  CERTIFIED_ORIGIN,
  setupBrowserRuntime,
  TRUSTED_BROWSER_ENVIRONMENT,
} from "../../deployment/staging/scripts/trusted_browser_service/providers/playwright-runtime-provider.mjs";

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

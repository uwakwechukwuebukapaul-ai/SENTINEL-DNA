import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import {
  REQUIRED_DOCKERIGNORE_RULES,
  verifyBuildContextPolicy,
} from "../../deployment/staging/trusted_browser_runtime/verify-build-context.mjs";
import {
  buildInputManifest,
  assertProductionInputs,
} from "../../deployment/staging/trusted_browser_runtime/verify-image-inputs.mjs";

const ROOT = new URL("../../", import.meta.url);

test("build-context policy requires explicit sensitive-data exclusions and rejects broad COPY", () => {
  const dockerignore = readFileSync(new URL(".dockerignore", ROOT), "utf8");
  const dockerfile = readFileSync(new URL("deployment/staging/trusted_browser_runtime/Dockerfile", ROOT), "utf8");
  const result = verifyBuildContextPolicy({ dockerignore, dockerfile });
  assert.equal(result.status, "PASS");
  assert.deepEqual(result.requiredRules, REQUIRED_DOCKERIGNORE_RULES);
  assert.throws(
    () => verifyBuildContextPolicy({ dockerignore: ".git\n", dockerfile }),
    (error) => error.code === "TB_BUILD_CONTEXT_POLICY_INCOMPLETE",
  );
  assert.throws(
    () => verifyBuildContextPolicy({ dockerignore, dockerfile: `${dockerfile}\nCOPY . /unsafe\n` }),
    (error) => error.code === "TB_BUILD_CONTEXT_BROAD_COPY",
  );
});

test("build-input manifest marks unavailable external and Linux browser identities blocked", () => {
  const manifest = buildInputManifest({
    root: fileURLToPath(ROOT),
    env: {
      SENTINEL_DNA_SOURCE_COMMIT: "e1fd9ca89303b089ce7b437ab9f91f1526fc7c60",
      SENTINEL_DNA_SOURCE_TREE: "daefd5fe8c3935bc8be3a1efec7995e86b840806",
      SENTINEL_DNA_BROWSER_PLATFORM: "linux",
      SENTINEL_DNA_BROWSER_ARCH: "x64",
    },
  });
  assert.equal(manifest.status, "BLOCKED");
  assert.equal(manifest.source.status, "VERIFIED");
  assert.equal(manifest.playwright.status, "VERIFIED");
  assert.equal(manifest.playwright.revision, "1234");
  assert.equal(manifest.playwright.browserVersion, "151.0.7922.34");
  assert.equal(manifest.runtimeModule.status, "BLOCKED");
  assert.equal(manifest.browserExecutable.status, "BLOCKED");
  assert.equal(manifest.browserExecutable.platform, "linux");
  assert.equal(manifest.browserExecutable.architecture, "x64");
  assert.equal(manifest.baseImage.status, "BLOCKED");
  assert.ok(manifest.includedSourceFiles.some(({ path }) => path.endsWith("runtime-service.mjs")));
});

test("Windows browser identity cannot satisfy the Linux runtime contract", () => {
  const manifest = buildInputManifest({
    root: fileURLToPath(ROOT),
    env: {
      SENTINEL_DNA_BROWSER_PLATFORM: "windows",
      SENTINEL_DNA_BROWSER_ARCH: "x64",
      SENTINEL_DNA_BROWSER_EXECUTABLE: "C:/browser/chrome-win64/chrome.exe",
      SENTINEL_DNA_BROWSER_EXECUTABLE_SHA256: `sha256:${"a".repeat(64)}`,
    },
  });
  assert.equal(manifest.browserExecutable.status, "BLOCKED");
  assert.equal(manifest.browserExecutable.platform, "windows");
  assert.equal(manifest.browserExecutable.architecture, "x64");
  assert.equal(manifest.browserExecutable.reason, "LINUX_BROWSER_BYTES_OR_DIGEST_UNAVAILABLE");
  assert.throws(
    () => assertProductionInputs(manifest, {
      SENTINEL_DNA_BROWSER_PLATFORM: "windows",
      SENTINEL_DNA_BROWSER_ARCH: "x64",
      SENTINEL_DNA_BROWSER_EXECUTABLE: "C:/browser/chrome-win64/chrome.exe",
    }),
    (error) => error.code === "TB_IMAGE_BROWSER_PLATFORM_MISMATCH",
  );
});

test("runtime and browser identities require hashes of observed bytes", () => {
  const directory = mkdtempSync(join(tmpdir(), "sentinel-gate4-inputs-"));
  const runtimePath = join(directory, "approved-playwright-runtime.mjs");
  const browserPath = join(directory, "chrome-linux64");
  const runtimeBytes = "export async function setupBrowserRuntime() { return {}; }\n";
  const browserBytes = Buffer.from("linux-browser-bytes");
  writeFileSync(runtimePath, runtimeBytes);
  writeFileSync(browserPath, browserBytes);
  const digest = (value) => createHash("sha256").update(value).digest("hex");
  try {
    const manifest = buildInputManifest({
      root: fileURLToPath(ROOT),
      env: {
        SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME: runtimePath,
        SENTINEL_DNA_APPROVED_RUNTIME_DIGEST: `sha256:${digest(runtimeBytes)}`,
        SENTINEL_DNA_BROWSER_EXECUTABLE: browserPath,
        SENTINEL_DNA_BROWSER_EXECUTABLE_SHA256: `sha256:${digest(browserBytes)}`,
        SENTINEL_DNA_BROWSER_PLATFORM: "linux",
        SENTINEL_DNA_BROWSER_ARCH: "x64",
      },
    });
    assert.equal(manifest.runtimeModule.status, "VERIFIED");
    assert.equal(manifest.browserExecutable.status, "VERIFIED");
    const mismatch = buildInputManifest({
      root: fileURLToPath(ROOT),
      env: {
        SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME: runtimePath,
        SENTINEL_DNA_APPROVED_RUNTIME_DIGEST: `sha256:${"0".repeat(64)}`,
        SENTINEL_DNA_BROWSER_EXECUTABLE: browserPath,
        SENTINEL_DNA_BROWSER_EXECUTABLE_SHA256: `sha256:${"0".repeat(64)}`,
        SENTINEL_DNA_BROWSER_PLATFORM: "linux",
        SENTINEL_DNA_BROWSER_ARCH: "x64",
      },
    });
    assert.equal(mismatch.runtimeModule.status, "BLOCKED");
    assert.equal(mismatch.browserExecutable.status, "BLOCKED");
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

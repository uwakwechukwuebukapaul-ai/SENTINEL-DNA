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
  isImmutableImageReference,
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

test("Playwright base image requires an immutable sha256 reference", () => {
  assert.equal(isImmutableImageReference("mcr.microsoft.com/playwright:v1.62.1-noble"), false);
  assert.equal(isImmutableImageReference("mcr.microsoft.com/playwright:v1.62.1-noble@sha256:c091b21d9fae78c76e85cd4356431e9b018402f172a214fc7d7a5e9a7e29d8ac"), true);
  assert.equal(isImmutableImageReference("mcr.microsoft.com/playwright:v1.62.1-noble@sha256:abc"), false);
});

test("recorded Docker/browser evidence is observed release evidence", () => {
  const evidence = JSON.parse(readFileSync(new URL("../../provenance/gate4-docker-browser-provenance.json", import.meta.url), "utf8"));
  assert.equal(evidence.runtime_configuration, false);
  assert.equal(evidence.docker.linux_amd64_manifest.platform, "linux/amd64");
  assert.equal(evidence.browser.revision, "1234");
  assert.equal(evidence.browser.version, "151.0.7922.34");
  assert.equal(evidence.browser.executable_size, 290614600);
  assert.equal(evidence.browser.executable_sha256, "0b20b130e7edd9dd51873be867761295fe0cfad490c2b9a64f95bd3cfc08fa71");
  assert.equal(evidence.gate4_status.LINUX_BROWSER_PROVENANCE, "PASS");
  assert.equal(evidence.gate4_status.EXTERNAL_RUNTIME_PROVENANCE, "BLOCKED");
  assert.equal(evidence.gate4_status.EGRESS_CONNECTION_LAYER, "BLOCKED");
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
  assert.equal(manifest.browserExecutable.revision, "1234");
  assert.equal(manifest.browserExecutable.browserVersion, "151.0.7922.34");
  assert.equal(manifest.runtimeModule.status, "BLOCKED");
  assert.equal(manifest.browserExecutable.status, "BLOCKED");
  assert.equal(manifest.browserExecutable.platform, "linux");
  assert.equal(manifest.browserExecutable.architecture, "x64");
  assert.equal(manifest.baseImage.status, "BLOCKED");
  assert.ok(manifest.includedSourceFiles.some(({ path }) => path.endsWith("runtime-service.mjs")));
});

test("observed Linux/amd64 image and browser evidence is represented without runtime configuration", () => {
  const manifest = buildInputManifest({
    root: fileURLToPath(ROOT),
    env: {
      PLAYWRIGHT_BASE_IMAGE: "mcr.microsoft.com/playwright:v1.62.1-noble@sha256:c091b21d9fae78c76e85cd4356431e9b018402f172a214fc7d7a5e9a7e29d8ac",
      SENTINEL_DNA_BASE_IMAGE_DIGEST: "sha256:c091b21d9fae78c76e85cd4356431e9b018402f172a214fc7d7a5e9a7e29d8ac",
      SENTINEL_DNA_BASE_IMAGE_OCI_INDEX_DIGEST: "sha256:dcc5531e97840b9b5e794f2814476b21571c5124a3fca2267d73041f56e7580e",
      SENTINEL_DNA_BASE_IMAGE_PLATFORM: "linux/amd64",
      SENTINEL_DNA_BASE_IMAGE_DIGEST_VERIFIED: "true",
      SENTINEL_DNA_BROWSER_PLATFORM: "linux",
      SENTINEL_DNA_BROWSER_ARCH: "x64",
      SENTINEL_DNA_BROWSER_EXECUTABLE: "missing-browser",
      SENTINEL_DNA_BROWSER_EXECUTABLE_SHA256: "sha256:0b20b130e7edd9dd51873be867761295fe0cfad490c2b9a64f95bd3cfc08fa71",
    },
  });
  assert.equal(manifest.baseImage.status, "VERIFIED");
  assert.equal(manifest.baseImage.ociIndexDigest, "sha256:dcc5531e97840b9b5e794f2814476b21571c5124a3fca2267d73041f56e7580e");
  assert.equal(manifest.baseImage.manifestDigest, "sha256:c091b21d9fae78c76e85cd4356431e9b018402f172a214fc7d7a5e9a7e29d8ac");
  assert.equal(manifest.baseImage.platform, "linux/amd64");
  assert.equal(manifest.browserExecutable.sha256, null);
  assert.equal(manifest.playwright.revision, "1234");
  assert.equal(manifest.playwright.browserVersion, "151.0.7922.34");
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
      PLAYWRIGHT_BASE_IMAGE: "example.invalid/browser@sha256:" + "a".repeat(64),
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

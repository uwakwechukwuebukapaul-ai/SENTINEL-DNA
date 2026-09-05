import { createHash } from "node:crypto";
import { existsSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = process.env.SENTINEL_DNA_TRUSTED_BROWSER_SOURCE_ROOT || "/opt/sentinel/trusted-browser";
export const EXPECTED_FILES = Object.freeze([
  "deployment/staging/scripts/controlled_analyst_pilot_runner.mjs",
  "deployment/staging/scripts/trusted_browser_diagnostics.mjs",
  "deployment/staging/scripts/trusted_browser_execution_adapter.mjs",
  "deployment/staging/scripts/trusted_browser_service/browser-client.mjs",
  "deployment/staging/scripts/trusted_browser_service/policy/capability-policy.mjs",
  "deployment/staging/scripts/trusted_browser_service/policy/network-policy.mjs",
  "deployment/staging/scripts/trusted_browser_service/policy/origin-policy.mjs",
  "deployment/staging/scripts/trusted_browser_service/policy/runtime-policy.mjs",
  "deployment/staging/scripts/trusted_browser_service/policy/secret-fields.mjs",
  "deployment/staging/scripts/trusted_browser_service/policy/tenant-context.mjs",
  "deployment/staging/scripts/trusted_browser_service/providers/approved-playwright-runtime.mjs",
  "deployment/staging/scripts/trusted_browser_service/providers/playwright-runtime-provider.mjs",
  "deployment/staging/scripts/trusted_browser_service/runtime-provider.mjs",
  "deployment/staging/trusted_browser_runtime/healthcheck.mjs",
  "deployment/staging/trusted_browser_runtime/rpc-client.mjs",
  "deployment/staging/trusted_browser_runtime/runtime-service.mjs",
  "deployment/staging/trusted_browser_runtime/verify-image-inputs.mjs",
  "package.json",
  "package-lock.json",
]);

const SHA256 = /^sha256:[0-9a-f]{64}$/i;
const IMMUTABLE_IMAGE_REFERENCE = /^\S+@sha256:[0-9a-f]{64}$/i;

export function isImmutableImageReference(value) {
  return typeof value === "string" && IMMUTABLE_IMAGE_REFERENCE.test(value.trim());
}

function fail(code, details = undefined) {
  const error = new Error(code);
  error.code = code;
  if (details !== undefined) error.details = details;
  throw error;
}

function required(name, env = process.env) {
  const value = env[name]?.trim();
  if (!value) fail(`TB_IMAGE_INPUT_${name}`);
  return value;
}

function optionalDigest(value) {
  return typeof value === "string" && SHA256.test(value.trim())
    ? value.trim().toLowerCase()
    : null;
}

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function fileRecord(root, relativePath) {
  const path = join(root, relativePath);
  if (!existsSync(path) || !statSync(path).isFile()) fail("TB_IMAGE_SOURCE_INCOMPLETE", { relativePath });
  const bytes = readFileSync(path);
  return { path: relativePath, bytes: bytes.length, sha256: sha256(bytes) };
}

function readBrowserMetadata(root) {
  const manifestPath = join(root, "node_modules/playwright-core/browsers.json");
  if (!existsSync(manifestPath)) return { status: "BLOCKED", reason: "PLAYWRIGHT_BROWSER_METADATA_UNAVAILABLE" };
  const browserManifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  const chromium = browserManifest.browsers?.find((browser) => browser.name === "chromium");
  if (!chromium) return { status: "BLOCKED", reason: "PLAYWRIGHT_CHROMIUM_METADATA_UNAVAILABLE" };
  return {
    status: "VERIFIED",
    playwrightVersion: JSON.parse(readFileSync(join(root, "package.json"), "utf8")).dependencies?.playwright || null,
    revision: chromium.revision || null,
    browserVersion: chromium.browserVersion || null,
    title: chromium.title || null,
  };
}

export function buildInputManifest({ root = ROOT, env = process.env } = {}) {
  const includedFiles = EXPECTED_FILES.map((relativePath) => fileRecord(root, relativePath));
  const lockfile = includedFiles.find(({ path }) => path === "package-lock.json");
  const runtimePath = env.SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME?.trim() || null;
  const runtimeDigest = optionalDigest(env.SENTINEL_DNA_APPROVED_RUNTIME_DIGEST);
  const runtimeAvailable = runtimePath && existsSync(runtimePath) && statSync(runtimePath).isFile();
  const runtimeObservedDigest = runtimeAvailable ? sha256(readFileSync(runtimePath)) : null;
  const executablePath = env.SENTINEL_DNA_BROWSER_EXECUTABLE?.trim() || null;
  const executableDigest = optionalDigest(env.SENTINEL_DNA_BROWSER_EXECUTABLE_SHA256);
  const executableAvailable = executablePath && existsSync(executablePath) && statSync(executablePath).isFile();
  const executableObservedDigest = executableAvailable ? sha256(readFileSync(executablePath)) : null;
  const executableObservedSize = executableAvailable ? statSync(executablePath).size : null;
  const baseReference = env.PLAYWRIGHT_BASE_IMAGE?.trim() || null;
  const baseDigest = optionalDigest(env.SENTINEL_DNA_BASE_IMAGE_DIGEST);
  const baseIndexDigest = optionalDigest(env.SENTINEL_DNA_BASE_IMAGE_OCI_INDEX_DIGEST);
  const referencedManifestDigest = baseReference?.match(/@(?<digest>sha256:[0-9a-f]{64})$/i)?.groups?.digest?.toLowerCase() || null;
  const baseManifestDigest = optionalDigest(env.SENTINEL_DNA_BASE_IMAGE_MANIFEST_DIGEST) || referencedManifestDigest;
  const basePlatform = env.SENTINEL_DNA_BASE_IMAGE_PLATFORM?.trim() || null;
  const baseDigestVerified = env.SENTINEL_DNA_BASE_IMAGE_DIGEST_VERIFIED === "true";
  const platform = env.SENTINEL_DNA_BROWSER_PLATFORM?.trim() || null;
  const architecture = env.SENTINEL_DNA_BROWSER_ARCH?.trim() || null;
  const browserMetadata = readBrowserMetadata(root);
  const sourceCommit = env.SENTINEL_DNA_SOURCE_COMMIT?.trim() || null;
  const sourceTree = env.SENTINEL_DNA_SOURCE_TREE?.trim() || null;

  const manifest = {
    schema: "sentinel-dna.gate4.build-inputs.v1",
    status: "VERIFIED",
    source: {
      commit: sourceCommit,
      tree: sourceTree,
      status: sourceCommit && sourceTree ? "VERIFIED" : "UNVERIFIED",
    },
    includedSourceFiles: includedFiles,
    packageLockSha256: lockfile.sha256,
    runtimeModule: {
      source: "external-approved-runtime",
      configuredPath: runtimePath,
      sha256: runtimeObservedDigest,
      status: runtimeAvailable && runtimeDigest && runtimeObservedDigest === runtimeDigest.slice("sha256:".length) ? "VERIFIED" : "BLOCKED",
      reason: runtimeAvailable && runtimeDigest
        ? (runtimeObservedDigest === runtimeDigest.slice("sha256:".length) ? null : "EXTERNAL_RUNTIME_DIGEST_MISMATCH")
        : "EXTERNAL_RUNTIME_BYTES_OR_DIGEST_UNAVAILABLE",
    },
    playwright: browserMetadata,
    browserExecutable: {
      platform,
      architecture,
      path: executablePath,
      size: executableObservedSize,
      sha256: executableObservedDigest,
      revision: browserMetadata.revision || null,
      browserVersion: browserMetadata.browserVersion || null,
      status: executableAvailable && executableDigest && executableObservedDigest === executableDigest.slice("sha256:".length) ? "VERIFIED" : "BLOCKED",
      reason: executableAvailable && executableDigest
        ? (executableObservedDigest === executableDigest.slice("sha256:".length) ? null : "LINUX_BROWSER_DIGEST_MISMATCH")
        : "LINUX_BROWSER_BYTES_OR_DIGEST_UNAVAILABLE",
    },
    baseImage: {
      reference: baseReference,
      digest: baseDigest,
      ociIndexDigest: baseIndexDigest,
      manifestDigest: baseManifestDigest,
      platform: basePlatform,
      immutableReference: isImmutableImageReference(baseReference),
      status: isImmutableImageReference(baseReference) && baseDigest && baseDigestVerified && baseManifestDigest === referencedManifestDigest ? "VERIFIED" : "BLOCKED",
      reason: !baseReference
        ? "BASE_IMAGE_REFERENCE_OR_DIGEST_UNAVAILABLE"
        : !isImmutableImageReference(baseReference)
          ? "BASE_IMAGE_REFERENCE_NOT_IMMUTABLE"
          : !baseDigest
            ? "BASE_IMAGE_REFERENCE_OR_DIGEST_UNAVAILABLE"
            : baseManifestDigest !== referencedManifestDigest
              ? "BASE_IMAGE_MANIFEST_DIGEST_MISMATCH"
              : (baseDigestVerified ? null : "BASE_IMAGE_REGISTRY_VERIFICATION_REQUIRED"),
    },
  };

  const blocking = [manifest.source.status, manifest.runtimeModule.status, manifest.playwright.status,
    manifest.browserExecutable.status, manifest.baseImage.status].some((status) => status !== "VERIFIED");
  manifest.status = blocking ? "BLOCKED" : "VERIFIED";
  return manifest;
}

export function assertProductionInputs(manifest, env = process.env) {
  if (!isImmutableImageReference(env.PLAYWRIGHT_BASE_IMAGE)) fail("TB_IMAGE_BASE_REFERENCE_NOT_IMMUTABLE");
  if (env.SENTINEL_DNA_BROWSER_PLATFORM !== "linux" || env.SENTINEL_DNA_BROWSER_ARCH !== "x64") {
    fail("TB_IMAGE_BROWSER_PLATFORM_MISMATCH");
  }
  if (env.SENTINEL_DNA_BROWSER_EXECUTABLE?.replaceAll("\\", "/") !== "/ms-playwright/chromium-1234/chrome-linux64/chrome") {
    fail("TB_IMAGE_BROWSER_PATH_MISMATCH");
  }
  if (manifest.source.status !== "VERIFIED") fail("TB_IMAGE_SOURCE_IDENTITY_UNAVAILABLE");
  if (manifest.runtimeModule.status !== "VERIFIED") fail("TB_IMAGE_RUNTIME_IDENTITY_UNAVAILABLE");
  if (manifest.baseImage.status !== "VERIFIED") fail("TB_IMAGE_BASE_IDENTITY_UNAVAILABLE");
  if (manifest.browserExecutable.status !== "VERIFIED") fail("TB_IMAGE_BROWSER_DIGEST_UNAVAILABLE");
}

export async function verifyImageInputs({ root = ROOT, env = process.env } = {}) {
  const manifest = buildInputManifest({ root, env });
  assertProductionInputs(manifest, env);
  const runtimePath = required("SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME", env);
  const runtimeModule = await import(pathToFileURL(resolve(runtimePath)).href);
  if (typeof runtimeModule.setupBrowserRuntime !== "function") fail("TB_IMAGE_RUNTIME_EXPORT_INVALID");
  const packageJson = JSON.parse(readFileSync(join(root, "package.json"), "utf8"));
  const lock = JSON.parse(readFileSync(join(root, "package-lock.json"), "utf8"));
  if (packageJson.dependencies?.playwright !== "^1.62.1" || lock.packages?.["node_modules/playwright"]?.version !== "1.62.1" || lock.packages?.["node_modules/playwright-core"]?.version !== "1.62.1") fail("TB_IMAGE_DEPENDENCY_VERSION_MISMATCH");
  if (manifest.playwright.revision !== "1234" || manifest.playwright.browserVersion !== "151.0.7922.34") fail("TB_IMAGE_BROWSER_METADATA_MISMATCH");
  return manifest;
}

const invokedAsMain = process.argv[1] && resolve(process.argv[1]) === resolve(fileURLToPath(import.meta.url));
if (invokedAsMain) {
  try {
    const manifest = await verifyImageInputs();
    const output = process.env.SENTINEL_DNA_BUILD_INPUT_MANIFEST_OUTPUT;
    if (output) {
      const { writeFileSync } = await import("node:fs");
      writeFileSync(output, `${JSON.stringify(manifest, null, 2)}\n`, { encoding: "utf8", flag: "wx" });
    }
    process.stdout.write(`${JSON.stringify(manifest)}\nPASS\n`);
  } catch (error) {
    process.stderr.write(`${error?.code || "TB_IMAGE_INPUTS_INVALID"}\n`);
    process.exitCode = 1;
  }
}

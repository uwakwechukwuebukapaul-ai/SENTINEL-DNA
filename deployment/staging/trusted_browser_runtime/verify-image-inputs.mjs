import { createHash } from "node:crypto";
import { existsSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const ROOT = process.env.SENTINEL_DNA_TRUSTED_BROWSER_SOURCE_ROOT || "/opt/sentinel/trusted-browser";
const EXPECTED_FILES = [
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
];

function fail(code) { throw new Error(code); }
function required(name) { const value = process.env[name]?.trim(); if (!value) fail(`TB_IMAGE_INPUT_${name}`); return value; }
function sha256(bytes) { return createHash("sha256").update(bytes).digest("hex"); }

for (const file of EXPECTED_FILES) {
  const path = join(ROOT, file);
  if (!existsSync(path) || !statSync(path).isFile()) fail("TB_IMAGE_SOURCE_INCOMPLETE");
}

const artifactRecords = EXPECTED_FILES.map((file) => {
  const bytes = readFileSync(join(ROOT, file));
  return { path: file, bytes: bytes.length, sha256: sha256(bytes) };
}).sort((a, b) => a.path.localeCompare(b.path));
const canonicalArtifact = artifactRecords.map(({ path, bytes, sha256: digest }) => `${path}\t${bytes}\t${digest}`).join("\n") + "\n";
if (sha256(Buffer.from(canonicalArtifact, "utf8")) !== required("SENTINEL_DNA_ARTIFACT_SHA256")) fail("TB_IMAGE_ARTIFACT_DIGEST_MISMATCH");

const lockPath = join(ROOT, "package-lock.json");
if (!existsSync(lockPath)) fail("TB_IMAGE_LOCKFILE_MISSING");
if (sha256(readFileSync(lockPath)) !== required("SENTINEL_DNA_DEPENDENCY_LOCK_SHA256")) fail("TB_IMAGE_LOCKFILE_MISMATCH");

const runtimePath = required("SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME");
if (!existsSync(runtimePath) || !statSync(runtimePath).isFile()) fail("TB_IMAGE_RUNTIME_MISSING");
if (sha256(readFileSync(runtimePath)) !== required("SENTINEL_DNA_APPROVED_RUNTIME_DIGEST").replace(/^sha256:/i, "")) fail("TB_IMAGE_RUNTIME_DIGEST_MISMATCH");

const packageJson = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8"));
const lock = JSON.parse(readFileSync(lockPath, "utf8"));
if (packageJson.dependencies?.playwright !== "^1.62.1" || lock.packages?.["node_modules/playwright"]?.version !== "1.62.1" || lock.packages?.["node_modules/playwright-core"]?.version !== "1.62.1") fail("TB_IMAGE_DEPENDENCY_VERSION_MISMATCH");

const browserManifest = JSON.parse(readFileSync(join(ROOT, "node_modules/playwright-core/browsers.json"), "utf8"));
const chromium = browserManifest.browsers.find((browser) => browser.name === "chromium");
if (!chromium || chromium.revision !== "1234" || chromium.browserVersion !== "151.0.7922.34") fail("TB_IMAGE_BROWSER_METADATA_MISMATCH");

const browserPath = required("SENTINEL_DNA_BROWSER_EXECUTABLE");
if (!existsSync(browserPath) || !statSync(browserPath).isFile()) fail("TB_IMAGE_BROWSER_MISSING");
if (sha256(readFileSync(browserPath)) !== required("SENTINEL_DNA_BROWSER_EXECUTABLE_SHA256").replace(/^sha256:/i, "")) fail("TB_IMAGE_BROWSER_DIGEST_MISMATCH");

required("SENTINEL_DNA_SOURCE_COMMIT");
required("SENTINEL_DNA_SOURCE_TREE");
required("SENTINEL_DNA_BASE_IMAGE_DIGEST");
required("SENTINEL_DNA_BUILD_ID");
process.stdout.write("PASS\n");

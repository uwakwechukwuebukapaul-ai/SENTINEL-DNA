/**
 * Fail-closed custody checks for the operator-supplied trusted-browser
 * runtime module.
 *
 * The runtime is deliberately outside this repository.  This module checks
 * the exact bytes at the operator path before any import is attempted.  It
 * never prints the path, imports a browser, or accepts credentials.
 */

import { createHash } from "node:crypto";
import { existsSync, realpathSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const APPROVED_RUNTIME_DIGEST_ENV =
  "SENTINEL_DNA_APPROVED_RUNTIME_DIGEST";
export const RUNTIME_EXPORT = "setupBrowserRuntime";
export const RUNTIME_PACKAGE_MANIFEST = "package.json";
export const RUNTIME_LOCKFILE = "package-lock.json";

const DIGEST = /^sha256:[0-9a-f]{64}$/i;
const REJECTED_PATH_MARKERS = [
  "/tests/",
  "/test/",
  "/fixtures/",
  "/fixture/",
  "trusted-playwright-adapter-stub",
  "/stub/",
  "/mock/",
  "/fake/",
];

function custodyError(code) {
  const error = new Error(`[${code}] trusted browser runtime custody check failed`);
  error.code = code;
  return error;
}

function normalizeDigest(value) {
  return typeof value === "string" && DIGEST.test(value.trim())
    ? value.trim().toLowerCase()
    : null;
}

function toFileUrl(modulePath) {
  if (typeof modulePath !== "string" || !modulePath.trim()) {
    throw custodyError("TB_RUNTIME_UNAVAILABLE");
  }
  try {
    const url = modulePath.trim().startsWith("file:")
      ? new URL(modulePath.trim())
      : pathToFileURL(resolve(modulePath.trim()));
    if (url.protocol !== "file:" || url.search || url.hash) {
      throw new Error("runtime is not a plain file module");
    }
    return url;
  } catch {
    throw custodyError("TB_RUNTIME_UNAVAILABLE");
  }
}

function repositoryRoot() {
  return resolve(fileURLToPath(new URL("../../../", import.meta.url)));
}

function isRepositoryPath(modulePath) {
  const root = realpathSync(repositoryRoot());
  const target = realpathSync(modulePath);
  const targetRelative = relative(root, target);
  return !isAbsolute(targetRelative) && !targetRelative.startsWith("..");
}

function isRejectedPath(modulePath) {
  const normalized = modulePath.replaceAll("\\", "/").toLowerCase();
  return REJECTED_PATH_MARKERS.some((marker) => normalized.includes(marker));
}

export function resolveApprovedRuntimeModule(modulePath) {
  const url = toFileUrl(modulePath);
  let target;
  try {
    target = realpathSync(fileURLToPath(url));
  } catch {
    throw custodyError("TB_RUNTIME_UNAVAILABLE");
  }
  if (!existsSync(target) || isRepositoryPath(target) || isRejectedPath(target)) {
    throw custodyError("TB_RUNTIME_UNAVAILABLE");
  }
  return pathToFileURL(target);
}

async function sha256File(moduleUrl) {
  try {
    const bytes = await readFile(moduleUrl);
    return `sha256:${createHash("sha256").update(bytes).digest("hex")}`;
  } catch {
    throw custodyError("TB_RUNTIME_UNAVAILABLE");
  }
}

function dependencyNames(packageManifest) {
  return [
    ...Object.keys(packageManifest.dependencies || {}),
    ...Object.keys(packageManifest.optionalDependencies || {}),
  ].filter((name, index, names) => names.indexOf(name) === index).sort();
}

function canonicalJson(value) {
  if (Array.isArray(value)) return value.map(canonicalJson);
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.keys(value).sort().map((key) => [key, canonicalJson(value[key])]),
  );
}

function sameJson(left, right) {
  return JSON.stringify(canonicalJson(left)) === JSON.stringify(canonicalJson(right));
}

function packageLockEntry(lockfile, packageName) {
  return lockfile?.packages?.[`node_modules/${packageName}`];
}

function packageRootFromResolved(resolvedPath, dependencyRoot) {
  let current = resolve(resolvedPath);
  const root = resolve(dependencyRoot);
  while (current !== root && current.startsWith(`${root}${sep}`)) {
    const packageManifest = join(current, RUNTIME_PACKAGE_MANIFEST);
    if (existsSync(packageManifest)) return current;
    current = dirname(current);
  }
  return null;
}

/**
 * Verify the native Node dependency closure for an external runtime bundle.
 *
 * Node resolves a bare ESM import from the importing file's ancestor
 * node_modules directories. The only supported production layout therefore
 * keeps the custody runtime, package manifest, lockfile, and installed
 * dependencies in one external bundle. This function validates that layout;
 * it does not alter Node resolution or execute package code.
 */
export async function validateRuntimeDependencyClosure({
  moduleUrl,
  expectedLockfileDigest,
} = {}) {
  try {
    if (!moduleUrl || moduleUrl.protocol !== "file:") {
      throw new Error("runtime bundle is not local");
    }
    const runtimePath = realpathSync(fileURLToPath(moduleUrl));
    const dependencyRoot = resolve(dirname(runtimePath));
    const packageManifestPath = join(dependencyRoot, RUNTIME_PACKAGE_MANIFEST);
    const lockfilePath = join(dependencyRoot, RUNTIME_LOCKFILE);
    const packageManifest = JSON.parse(await readFile(packageManifestPath, "utf8"));
    const lockfile = JSON.parse(await readFile(lockfilePath, "utf8"));
    if (
      !packageManifest ||
      typeof packageManifest !== "object" ||
      Array.isArray(packageManifest) ||
      packageManifest.private !== true ||
      !lockfile ||
      typeof lockfile !== "object" ||
      !lockfile.packages?.[""]
    ) {
      throw new Error("runtime bundle metadata is invalid");
    }

    const dependencies = dependencyNames(packageManifest);
    const lockRoot = lockfile.packages[""];
    if (
      !sameJson(lockRoot.dependencies || {}, packageManifest.dependencies || {}) ||
      !sameJson(lockRoot.optionalDependencies || {}, packageManifest.optionalDependencies || {})
    ) {
      throw new Error("runtime bundle lockfile root does not match package manifest");
    }

    const lockfileDigest = await sha256File(pathToFileURL(lockfilePath));
    if (
      expectedLockfileDigest !== undefined &&
      normalizeDigest(expectedLockfileDigest) !== lockfileDigest
    ) {
      throw custodyError("TB_PROVIDER_MANIFEST_INVALID");
    }

    const requireFromRuntime = createRequire(pathToFileURL(runtimePath));
    const nodeModulesRoot = resolve(join(dependencyRoot, "node_modules"));
    for (const dependency of dependencies) {
      const resolved = requireFromRuntime.resolve(dependency);
      const resolvedRealPath = resolve(realpathSync(resolved));
      const packageRoot = packageRootFromResolved(resolvedRealPath, nodeModulesRoot);
      const lockEntry = packageLockEntry(lockfile, dependency);
      if (!packageRoot || !lockEntry) throw new Error("runtime dependency is outside the bundle");
      const installedManifest = JSON.parse(
        await readFile(join(packageRoot, RUNTIME_PACKAGE_MANIFEST), "utf8"),
      );
      if (installedManifest.name !== dependency || installedManifest.version !== lockEntry.version) {
        throw new Error("runtime dependency does not match the lockfile");
      }
    }

    return Object.freeze({
      status: "PASS",
      dependencyRoot: pathToFileURL(dependencyRoot),
      lockfileDigest,
      dependencies: Object.freeze(dependencies),
    });
  } catch (error) {
    if (error?.code === "TB_PROVIDER_MANIFEST_INVALID") throw error;
    throw custodyError("TB_RUNTIME_UNAVAILABLE");
  }
}

/**
 * Verify the exact external module bytes against custody metadata.
 *
 * `expectedDigest` is normally the digest from the validated activation
 * manifest. `operatorDigest`, when supplied by the activation helper, is an
 * independent operator input and must agree with both the file and manifest.
 */
export async function validateRuntimeModuleCustody({
  modulePath,
  expectedDigest,
  operatorDigest = undefined,
  expectedLockfileDigest = undefined,
  requireDependencyClosure = false,
} = {}) {
  const manifestDigest = normalizeDigest(expectedDigest);
  if (!manifestDigest) throw custodyError("TB_PROVIDER_MANIFEST_INVALID");

  const suppliedDigest = operatorDigest === undefined
    ? null
    : normalizeDigest(operatorDigest);
  if (operatorDigest !== undefined && !suppliedDigest) {
    throw custodyError("TB_PROVIDER_MANIFEST_INVALID");
  }
  if (suppliedDigest && suppliedDigest !== manifestDigest) {
    throw custodyError("TB_PROVIDER_MANIFEST_INVALID");
  }

  const runtimeUrl = resolveApprovedRuntimeModule(modulePath);
  const actualDigest = await sha256File(runtimeUrl);
  if (actualDigest !== manifestDigest || (suppliedDigest && actualDigest !== suppliedDigest)) {
    throw custodyError("TB_PROVIDER_MANIFEST_INVALID");
  }
  const dependencyClosure = requireDependencyClosure
    ? await validateRuntimeDependencyClosure({
      moduleUrl: runtimeUrl,
      expectedLockfileDigest,
    })
    : undefined;
  return Object.freeze({
    status: "PASS",
    digest: actualDigest,
    url: runtimeUrl,
    ...(dependencyClosure ? { dependencyClosure } : {}),
  });
}

/** Validate the required provider export without executing it. */
export async function validateRuntimeModuleExports(moduleUrl) {
  try {
    const module = await import(moduleUrl.href);
    if (typeof module[RUNTIME_EXPORT] !== "function") {
      throw custodyError("TB_PROVIDER_EXPORT_INVALID");
    }
    return Object.freeze({ status: "PASS" });
  } catch (error) {
    if (error?.code === "TB_PROVIDER_EXPORT_INVALID") throw error;
    throw custodyError("TB_RUNTIME_UNAVAILABLE");
  }
}

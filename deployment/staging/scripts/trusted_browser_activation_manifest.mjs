/**
 * Integrity-checked, non-secret activation manifest for the trusted browser.
 *
 * This module deliberately does not create signatures or hold signing keys.
 * The operator approval reference and any detached signature are supplied by
 * the approved custody system; this repository verifies the manifest schema
 * and its SHA-256 integrity value.
 */

import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

export const ACTIVATION_MANIFEST_ENV =
  "SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST";
export const ACTIVATION_MANIFEST_SCHEMA_VERSION = "1.0";
export const CERTIFIED_STAGING_ORIGIN = "https://sentinel-dna-staging:18443";

const SAFE_IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9._:/-]{2,127}$/;
const UTC_TIMESTAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/;
const IMAGE_DIGEST = /^sha256:[0-9a-f]{64}$/i;
const REQUIRED_FIELDS = [
  "schema_version",
  "provider_identity",
  "runtime_module_identity",
  "approved_runtime_module_digest",
  "approved_image_runtime_digest",
  "staging_origin",
  "activation_timestamp",
  "operator_approval_reference",
];
const ALLOWED_TOP_LEVEL_FIELDS = new Set([...REQUIRED_FIELDS, "integrity", "signature"]);
const OPTIONAL_RUNTIME_FIELDS = new Set([
  "approved_runtime_dependency_lockfile_digest",
  "approved_browser_auth_bridge_identity",
  "approved_browser_auth_bridge_digest",
]);

function manifestError(code) {
  const error = new Error(`[${code}] trusted browser activation manifest is invalid`);
  error.code = code;
  return error;
}

function canonicalize(value, { omitIntegrity = false } = {}) {
  if (Array.isArray(value)) return value.map((item) => canonicalize(item, { omitIntegrity }));
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.keys(value)
      .filter((key) => !(omitIntegrity && key === "integrity"))
      .sort()
      .map((key) => [key, canonicalize(value[key], { omitIntegrity })]),
  );
}

export function canonicalManifestPayload(manifest) {
  return JSON.stringify(canonicalize(manifest, { omitIntegrity: true }));
}

export function computeManifestHash(manifest) {
  return createHash("sha256")
    .update(canonicalManifestPayload(manifest), "utf8")
    .digest("hex");
}

function isSafeIdentifier(value) {
  return typeof value === "string" && SAFE_IDENTIFIER.test(value);
}

export function validateActivationManifest(manifest) {
  if (!manifest || typeof manifest !== "object" || Array.isArray(manifest)) {
    throw manifestError("TB_PROVIDER_MANIFEST_INVALID");
  }
  if (Object.keys(manifest).some((key) =>
    !ALLOWED_TOP_LEVEL_FIELDS.has(key) && !OPTIONAL_RUNTIME_FIELDS.has(key))) {
    throw manifestError("TB_PROVIDER_MANIFEST_INVALID");
  }
  if (manifest.schema_version !== ACTIVATION_MANIFEST_SCHEMA_VERSION) {
    throw manifestError("TB_PROVIDER_MANIFEST_INVALID");
  }
  if (!isSafeIdentifier(manifest.provider_identity) || !isSafeIdentifier(manifest.runtime_module_identity)) {
    throw manifestError("TB_PROVIDER_MANIFEST_INVALID");
  }
  if (!IMAGE_DIGEST.test(manifest.approved_runtime_module_digest || "")) {
    throw manifestError("TB_PROVIDER_MANIFEST_INVALID");
  }
  if (!IMAGE_DIGEST.test(manifest.approved_image_runtime_digest || "")) {
    throw manifestError("TB_PROVIDER_MANIFEST_INVALID");
  }
  if (
    manifest.approved_runtime_dependency_lockfile_digest !== undefined &&
    !IMAGE_DIGEST.test(manifest.approved_runtime_dependency_lockfile_digest)
  ) {
    throw manifestError("TB_PROVIDER_MANIFEST_INVALID");
  }
  const bridgeIdentity = manifest.approved_browser_auth_bridge_identity;
  const bridgeDigest = manifest.approved_browser_auth_bridge_digest;
  if ((bridgeIdentity === undefined) !== (bridgeDigest === undefined)) {
    throw manifestError("TB_PROVIDER_MANIFEST_INVALID");
  }
  if (bridgeIdentity !== undefined && !isSafeIdentifier(bridgeIdentity)) {
    throw manifestError("TB_PROVIDER_MANIFEST_INVALID");
  }
  if (bridgeDigest !== undefined && !IMAGE_DIGEST.test(bridgeDigest)) {
    throw manifestError("TB_PROVIDER_MANIFEST_INVALID");
  }
  if (manifest.staging_origin !== CERTIFIED_STAGING_ORIGIN) {
    throw manifestError("TB_ORIGIN_REJECTED");
  }
  if (
    typeof manifest.activation_timestamp !== "string" ||
    !UTC_TIMESTAMP.test(manifest.activation_timestamp) ||
    Number.isNaN(Date.parse(manifest.activation_timestamp))
  ) {
    throw manifestError("TB_PROVIDER_MANIFEST_INVALID");
  }
  if (!isSafeIdentifier(manifest.operator_approval_reference)) {
    throw manifestError("TB_PROVIDER_MANIFEST_INVALID");
  }
  if (
    !manifest.integrity ||
    Object.keys(manifest.integrity).some((key) => !["algorithm", "manifest_hash"].includes(key)) ||
    manifest.integrity.algorithm !== "sha256" ||
    !/^[0-9a-f]{64}$/i.test(manifest.integrity.manifest_hash || "") ||
    manifest.integrity.manifest_hash.toLowerCase() !== computeManifestHash(manifest).toLowerCase()
  ) {
    throw manifestError("TB_PROVIDER_MANIFEST_INVALID");
  }
  if (manifest.signature !== undefined) {
    if (
      !manifest.signature ||
      Object.keys(manifest.signature).some((key) => !["scheme", "key_reference", "signature_reference"].includes(key)) ||
      manifest.signature.scheme !== "detached-external" ||
      !isSafeIdentifier(manifest.signature.key_reference) ||
      !isSafeIdentifier(manifest.signature.signature_reference)
    ) {
      throw manifestError("TB_PROVIDER_MANIFEST_INVALID");
    }
  }
  for (const field of REQUIRED_FIELDS) {
    if (manifest[field] === undefined) throw manifestError("TB_PROVIDER_MANIFEST_INVALID");
  }
  return Object.freeze({ ...manifest });
}

export async function loadActivationManifest() {
  const configured = process.env?.[ACTIVATION_MANIFEST_ENV];
  if (typeof configured !== "string" || !configured.trim()) {
    throw manifestError("TB_PROVIDER_MANIFEST_MISSING");
  }
  let source;
  try {
    source = configured.trim().startsWith("file:")
      ? new URL(configured.trim())
      : pathToFileURL(resolve(configured.trim()));
    if (source.protocol !== "file:" || source.search || source.hash) throw new Error("invalid manifest source");
  } catch {
    throw manifestError("TB_PROVIDER_MANIFEST_MISSING");
  }
  let manifest;
  try {
    manifest = JSON.parse(await readFile(source, "utf8"));
  } catch {
    throw manifestError("TB_PROVIDER_MANIFEST_MISSING");
  }
  return validateActivationManifest(manifest);
}

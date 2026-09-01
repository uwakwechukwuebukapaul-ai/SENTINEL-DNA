/**
 * NON-PRODUCTION simulation-only activation manifest generator.
 *
 * It creates a synthetic manifest and an ephemeral detached signature bundle.
 * No private key is written. The generated artifacts are not trusted by the
 * production activation gate and must never be registered as a production
 * provider or runtime.
 */

import { createHash, generateKeyPairSync, sign, verify } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import {
  CERTIFIED_STAGING_ORIGIN,
  computeManifestHash,
  validateActivationManifest,
} from "../scripts/trusted_browser_activation_manifest.mjs";

export const SIMULATION_MODE = "NON-PRODUCTION_SIMULATION";
export const SIMULATION_IMAGE_DIGEST = `sha256:${createHash("sha256")
  .update("SENTINEL-DNA-NON-PRODUCTION-SIMULATION-IMAGE", "utf8")
  .digest("hex")}`;
export const SIMULATION_RUNTIME_DIGEST = `sha256:${createHash("sha256")
  .update("SENTINEL-DNA-NON-PRODUCTION-SIMULATION-RUNTIME", "utf8")
  .digest("hex")}`;
export const SIMULATION_OUTPUT_DIRECTORY = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "output",
);

function simulationError(code, message) {
  const error = new Error(`[${code}] simulation manifest generation failed`);
  error.code = code;
  error.safeMessage = message;
  return error;
}

function assertSimulationMode(options = {}) {
  if (
    options.simulationMode !== true ||
    process.env?.SENTINEL_DNA_SIMULATION_MODE !== "1"
  ) {
    throw simulationError("TB_SIMULATION_MODE_REQUIRED", "explicit non-production simulation mode is required");
  }
}

function assertSafeOutputDirectory(outputDirectory) {
  const target = resolve(outputDirectory);
  const normalized = target.replaceAll("\\", "/").toLowerCase();
  if (
    normalized.includes("/pilot-evidence") ||
    normalized.includes("/programdata/sentinel-dna") ||
    !target
  ) {
    throw simulationError("TB_SIMULATION_OUTPUT_REJECTED", "simulation output cannot target production evidence custody");
  }
  return target;
}

function simulationManifest() {
  const manifest = {
    schema_version: "1.0",
    provider_identity: "simulation-reviewed-provider:non-production",
    runtime_module_identity: "simulation-runtime:ephemeral-contract",
    approved_runtime_module_digest: SIMULATION_RUNTIME_DIGEST,
    approved_image_runtime_digest: SIMULATION_IMAGE_DIGEST,
    staging_origin: CERTIFIED_STAGING_ORIGIN,
    activation_timestamp: new Date().toISOString().replace(/\.(\d{3})Z$/, ".$1Z"),
    operator_approval_reference: "SIMULATION-APPROVAL-NONPRODUCTION",
    signature: {
      scheme: "detached-external",
      key_reference: "simulation:ephemeral-public-key",
      signature_reference: "simulation:ephemeral-signature",
    },
  };
  manifest.integrity = {
    algorithm: "sha256",
    manifest_hash: computeManifestHash(manifest),
  };
  return validateActivationManifest(manifest);
}

export async function generateSimulationActivationManifest({
  outputDirectory = SIMULATION_OUTPUT_DIRECTORY,
  simulationMode = false,
} = {}) {
  assertSimulationMode({ simulationMode });
  const targetDirectory = assertSafeOutputDirectory(outputDirectory);
  await mkdir(targetDirectory, { recursive: true });

  const manifest = simulationManifest();
  const manifestPayload = `${JSON.stringify(manifest, null, 2)}\n`;
  const { publicKey, privateKey } = generateKeyPairSync("ed25519");
  const signature = sign(null, Buffer.from(manifest.integrity.manifest_hash, "utf8"), privateKey)
    .toString("base64");
  if (!verify(
    null,
    Buffer.from(manifest.integrity.manifest_hash, "utf8"),
    publicKey,
    Buffer.from(signature, "base64"),
  )) {
    throw simulationError("TB_SIMULATION_SIGNATURE_INVALID", "simulation signature self-check failed");
  }
  const signatureBundle = {
    mode: SIMULATION_MODE,
    algorithm: "ed25519",
    key_reference: manifest.signature.key_reference,
    signature_reference: manifest.signature.signature_reference,
    signed_manifest_hash: manifest.integrity.manifest_hash,
    public_key_pem: publicKey.export({ format: "pem", type: "spki" }),
    signature_base64: signature,
    private_key_written: false,
  };

  const manifestName = "trusted-browser-activation-manifest.simulation.json";
  const signatureName = "trusted-browser-activation-signature.simulation.json";
  await writeFile(join(targetDirectory, manifestName), manifestPayload, { encoding: "utf8", flag: "wx" });
  await writeFile(
    join(targetDirectory, signatureName),
    `${JSON.stringify(signatureBundle, null, 2)}\n`,
    { encoding: "utf8", flag: "wx" },
  );

  return Object.freeze({
    mode: SIMULATION_MODE,
    manifest,
    manifest_file: manifestName,
    signature_file: signatureName,
    image_digest: SIMULATION_IMAGE_DIGEST,
    output_directory: relative(SIMULATION_OUTPUT_DIRECTORY, targetDirectory),
  });
}

const invokedAsMain = process.argv[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (invokedAsMain) {
  try {
    const explicitFlag = process.argv.includes("--non-production-simulation");
    const result = await generateSimulationActivationManifest({ simulationMode: explicitFlag });
    console.log(JSON.stringify({
      mode: result.mode,
      status: "SIMULATION_MANIFEST_GENERATED",
      simulation_only: true,
      production_authorization: false,
      manifest_file: result.manifest_file,
      signature_file: result.signature_file,
    }, null, 2));
  } catch (error) {
    console.log(JSON.stringify({
      mode: SIMULATION_MODE,
      status: "BLOCKED_WITH_REASON",
      simulation_only: true,
      production_authorization: false,
      code: error?.code || "TB_SIMULATION_MANIFEST_FAILED",
    }, null, 2));
    process.exitCode = 1;
  }
}

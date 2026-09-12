import assert from "node:assert/strict";
import { verify } from "node:crypto";
import { mkdtemp, readFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import test from "node:test";

import {
  generateSimulationActivationManifest,
  SIMULATION_IMAGE_DIGEST,
  SIMULATION_MODE,
} from "../../deployment/staging/simulation/generate_simulation_activation_manifest.mjs";
import {
  simulateControlledAnalystPilotActivation,
} from "../../deployment/staging/simulation/simulate_controlled_analyst_pilot_activation.mjs";
import {
  validateActivationManifest,
} from "../../deployment/staging/scripts/trusted_browser_activation_manifest.mjs";
import {
  CERTIFIED_ORIGIN,
  isSyntheticCertifiedOriginReachable,
} from "../../deployment/staging/simulation/fixtures/synthetic-certified-staging-endpoint.mjs";

test("simulation requires an explicit non-production guard", { concurrency: false }, async () => {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-simulation-"));
  const previousMode = process.env.SENTINEL_DNA_SIMULATION_MODE;
  delete process.env.SENTINEL_DNA_SIMULATION_MODE;
  try {
    await assert.rejects(
      () => simulateControlledAnalystPilotActivation({ outputDirectory: directory }),
      (error) => error.code === "TB_SIMULATION_MODE_REQUIRED",
    );
  } finally {
    if (previousMode === undefined) delete process.env.SENTINEL_DNA_SIMULATION_MODE;
    else process.env.SENTINEL_DNA_SIMULATION_MODE = previousMode;
  }
});

test("simulation demonstrates blocked then simulation-ready without production authorization", { concurrency: false }, async () => {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-simulation-"));
  const previousMode = process.env.SENTINEL_DNA_SIMULATION_MODE;
  process.env.SENTINEL_DNA_SIMULATION_MODE = "1";
  let report;
  try {
    report = await simulateControlledAnalystPilotActivation({
      outputDirectory: directory,
      simulationMode: true,
    });
  } finally {
    if (previousMode === undefined) delete process.env.SENTINEL_DNA_SIMULATION_MODE;
    else process.env.SENTINEL_DNA_SIMULATION_MODE = previousMode;
  }

  assert.equal(report.mode, SIMULATION_MODE);
  assert.equal(report.simulation_only, true);
  assert.equal(report.production_authorization, false);
  assert.equal(report.initial_readiness_status, "BLOCKED_WITH_REASON");
  assert.ok(report.initial_blocked_codes.includes("TB_PROVIDER_MODULE_MISSING"));
  assert.equal(report.status, "SIMULATION_READY_FOR_ANALYST_PILOT");
  assert.equal(report.final_readiness_decision, "SIMULATION_READY_FOR_ANALYST_PILOT");
  assert.ok(report.checks.every((check) => check.status !== "BLOCKED"));
  assert.equal(report.evidence.analyst_access_approval.status, "SIMULATION_ONLY");
  assert.equal(report.evidence.analyst_access_approval.production_authorization, false);

  const serialized = JSON.stringify(report);
  assert.doesNotMatch(serialized, /C:\\|\/Users\/|password|cookie|token|authorization header|private key/i);
  assert.ok(Object.values(report.artifacts).every((name) => !name.includes(":\\") && !name.startsWith("/")));

});

test("simulation manifest has valid SHA-256 binding and an ephemeral public signature", { concurrency: false }, async () => {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-simulation-"));
  const previousMode = process.env.SENTINEL_DNA_SIMULATION_MODE;
  process.env.SENTINEL_DNA_SIMULATION_MODE = "1";
  let result;
  try {
    result = await generateSimulationActivationManifest({
      outputDirectory: directory,
      simulationMode: true,
    });
  } finally {
    if (previousMode === undefined) delete process.env.SENTINEL_DNA_SIMULATION_MODE;
    else process.env.SENTINEL_DNA_SIMULATION_MODE = previousMode;
  }
  const manifest = JSON.parse(await readFile(join(directory, result.manifest_file), "utf8"));
  const signatureBundle = JSON.parse(await readFile(join(directory, result.signature_file), "utf8"));
  assert.equal(validateActivationManifest(manifest).approved_image_runtime_digest, SIMULATION_IMAGE_DIGEST);
  assert.equal(signatureBundle.mode, SIMULATION_MODE);
  assert.equal(signatureBundle.private_key_written, false);
  assert.equal(signatureBundle.signed_manifest_hash, manifest.integrity.manifest_hash);
  assert.equal(
    verify(
      null,
      Buffer.from(manifest.integrity.manifest_hash, "utf8"),
      signatureBundle.public_key_pem,
      Buffer.from(signatureBundle.signature_base64, "base64"),
    ),
    true,
  );
});

test("simulation output cannot target production evidence custody", { concurrency: false }, async () => {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-simulation-"));
  const previousMode = process.env.SENTINEL_DNA_SIMULATION_MODE;
  process.env.SENTINEL_DNA_SIMULATION_MODE = "1";
  try {
    await assert.rejects(
      () => generateSimulationActivationManifest({
        outputDirectory: join(directory, "pilot-evidence"),
        simulationMode: true,
      }),
      (error) => error.code === "TB_SIMULATION_OUTPUT_REJECTED",
    );
  } finally {
    if (previousMode === undefined) delete process.env.SENTINEL_DNA_SIMULATION_MODE;
    else process.env.SENTINEL_DNA_SIMULATION_MODE = previousMode;
  }
});

test("synthetic endpoint accepts only the certified origin", () => {
  assert.equal(isSyntheticCertifiedOriginReachable(CERTIFIED_ORIGIN), true);
  assert.equal(isSyntheticCertifiedOriginReachable("https://example.invalid"), false);
});

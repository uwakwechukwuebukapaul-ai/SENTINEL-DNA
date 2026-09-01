import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

import { validateActivationManifest } from "../../deployment/staging/scripts/trusted_browser_activation_manifest.mjs";

const CONFIG_HELPER = new URL(
  "../../deployment/staging/scripts/configure_gate4_provider_environment.ps1",
  import.meta.url,
);
const VALIDATOR = new URL(
  "../../deployment/staging/scripts/configure_trusted_browser_provider.ps1",
  import.meta.url,
);
const ACTIVATION_MANIFEST = new URL(
  "../../pilot-evidence/gate4/trusted-browser-activation-manifest.json",
  import.meta.url,
);

test("Gate 4 configuration helper pins the facade and approved provider boundary", async () => {
  const source = await readFile(CONFIG_HELPER, "utf8");
  assert.match(source, /trusted_browser_service\\browser-client\.mjs/);
  assert.match(source, /trusted_browser_service\\providers\\playwright-runtime-provider\.mjs/);
  assert.match(source, /ApprovedRuntimeModule/);
  assert.match(source, /ActivationManifest/);
  assert.match(source, /SENTINEL_DNA_ENV = "staging"/);
  assert.doesNotMatch(source, /password|token|cookie|authorization/i);
});

test("Gate 4 validator requires the exact reviewed facade and provider boundary", async () => {
  const source = await readFile(VALIDATOR, "utf8");
  assert.match(source, /expectedProviderFiles/);
  assert.match(source, /browser-client\.mjs/);
  assert.match(source, /providers\\\\playwright-runtime-provider\.mjs|providers\\playwright-runtime-provider\.mjs/);
  assert.match(source, /does not resolve to the reviewed repository module/);
});

test("Gate 4 activation manifest is integrity-bound to the certified origin", async () => {
  const manifest = JSON.parse(await readFile(ACTIVATION_MANIFEST, "utf8"));
  const validated = validateActivationManifest(manifest);
  assert.equal(validated.staging_origin, "https://sentinel-dna-staging:18443");
  assert.equal(validated.integrity.algorithm, "sha256");
});

import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { checkControlledPilotReadiness } from "../../deployment/staging/scripts/check_controlled_pilot_readiness.mjs";
import {
  TRUSTED_BROWSER_CLIENT_ENV,
} from "../../deployment/staging/scripts/trusted_browser_execution_adapter.mjs";
import {
  TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV,
} from "../../deployment/staging/scripts/trusted_browser_service/browser-client.mjs";
import {
  APPROVED_PLAYWRIGHT_RUNTIME_ENV,
} from "../../deployment/staging/scripts/trusted_browser_service/providers/playwright-runtime-provider.mjs";
import {
  APPROVED_RUNTIME_DIGEST_ENV,
} from "../../deployment/staging/scripts/trusted_browser_runtime_custody.mjs";
import {
  ACTIVATION_MANIFEST_ENV,
  computeManifestHash,
} from "../../deployment/staging/scripts/trusted_browser_activation_manifest.mjs";
import { generateTrustedBrowserReadinessReport } from "../../deployment/staging/scripts/generate_trusted_browser_readiness_report.mjs";
import { generateTrustedBrowserActivationTroubleshootingReport } from "../../deployment/staging/scripts/generate_trusted_browser_activation_troubleshooting_report.mjs";

const SERVICE_MODULE = fileURLToPath(new URL(
  "../../deployment/staging/scripts/trusted_browser_service/browser-client.mjs",
  import.meta.url,
));
const PROVIDER_MODULE = fileURLToPath(new URL(
  "../../deployment/staging/scripts/trusted_browser_service/providers/playwright-runtime-provider.mjs",
  import.meta.url,
));
const ENVIRONMENT_VARIABLES = [
  "SENTINEL_DNA_ENV",
  "SENTINEL_DNA_IMAGE_DIGEST",
  "SENTINEL_DNA_PILOT_ACCESS_REQUIRED",
  "SENTINEL_DNA_SECURE_COOKIES",
  "FLASK_DEBUG",
  "SENTINEL_DNA_TENANT_ISOLATION_ENABLED",
  "SENTINEL_DNA_AUDIT_LOGGING_ENABLED",
  ACTIVATION_MANIFEST_ENV,
  TRUSTED_BROWSER_CLIENT_ENV,
  TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV,
  APPROVED_PLAYWRIGHT_RUNTIME_ENV,
  APPROVED_RUNTIME_DIGEST_ENV,
];

const VALID_RUNTIME = `
  export async function setupBrowserRuntime() {
    const tab = {
      goto: async () => {},
      close: async () => {},
      playwright: { locator: () => ({}), evaluate: async () => ({ safe: true }) },
      dom_cua: { get_visible_dom: async () => ({ safe: true }) },
      capabilities: { get: async (name) => name === "browserAuth" ? { request: async () => ({ status: "not-called" }) } : undefined },
    };
    return { browsers: { getForUrl: async (origin) => {
      if (origin !== "https://uwakwe-desktop.taile388cc.ts.net") throw new Error("origin rejected");
      return { tabs: { new: async () => tab } };
    } } };
  }
`;

async function withReadinessConfiguration({ runtimeSource = VALID_RUNTIME, providerPath = PROVIDER_MODULE, configure = true } = {}, callback) {
  const directory = await mkdtemp(join(tmpdir(), "sentinel-dna-readiness-"));
  const runtimePath = join(directory, "reviewed-runtime.mjs");
  await writeFile(runtimePath, runtimeSource, "utf8");
  const runtimeDigest = createHash("sha256").update(runtimeSource, "utf8").digest("hex");
  const manifestPath = join(directory, "activation-manifest.json");
  const manifest = {
    schema_version: "1.0",
    provider_identity: "reviewed-provider:test",
    runtime_module_identity: "reviewed-runtime:test",
    approved_runtime_module_digest: `sha256:${runtimeDigest}`,
    approved_image_runtime_digest: `sha256:${"a".repeat(64)}`,
    staging_origin: "https://uwakwe-desktop.taile388cc.ts.net",
    activation_timestamp: "2026-09-01T12:00:00Z",
    operator_approval_reference: "APPROVAL-TEST-001",
  };
  manifest.integrity = { algorithm: "sha256", manifest_hash: computeManifestHash(manifest) };
  await writeFile(manifestPath, `${JSON.stringify(manifest)}\n`, "utf8");
  const previous = Object.fromEntries(ENVIRONMENT_VARIABLES.map((name) => [name, process.env[name]]));
  for (const name of ENVIRONMENT_VARIABLES) delete process.env[name];
  if (configure) {
    process.env.SENTINEL_DNA_ENV = "staging";
    process.env.SENTINEL_DNA_IMAGE_DIGEST = `sha256:${"a".repeat(64)}`;
    process.env.SENTINEL_DNA_PILOT_ACCESS_REQUIRED = "1";
    process.env.SENTINEL_DNA_SECURE_COOKIES = "1";
    process.env.FLASK_DEBUG = "0";
    process.env.SENTINEL_DNA_TENANT_ISOLATION_ENABLED = "1";
    process.env.SENTINEL_DNA_AUDIT_LOGGING_ENABLED = "1";
    process.env[ACTIVATION_MANIFEST_ENV] = manifestPath;
    process.env[TRUSTED_BROWSER_CLIENT_ENV] = SERVICE_MODULE;
    process.env[TRUSTED_BROWSER_UPSTREAM_CLIENT_ENV] = providerPath;
    process.env[APPROVED_PLAYWRIGHT_RUNTIME_ENV] = runtimePath;
    process.env[APPROVED_RUNTIME_DIGEST_ENV] = `sha256:${runtimeDigest}`;
  }
  try {
    return await callback({ directory, manifestPath });
  } finally {
    for (const name of ENVIRONMENT_VARIABLES) {
      if (previous[name] === undefined) delete process.env[name];
      else process.env[name] = previous[name];
    }
    await rm(directory, { recursive: true, force: true });
  }
}

test("readiness blocks when the provider is missing", { concurrency: false }, async () => {
  await withReadinessConfiguration({ configure: false }, async ({ directory }) => {
    const readiness = await checkControlledPilotReadiness({
      evidenceDir: directory,
      originReachability: async () => true,
    });
    assert.equal(readiness.status, "BLOCKED_WITH_REASON");
    assert.equal(readiness.checks.find((item) => item.name === "provider_configured").status, "BLOCKED");
    assert.doesNotMatch(JSON.stringify(readiness), /approved-runtime|secret-token|must-not-escape/i);
    const troubleshooting = await generateTrustedBrowserActivationTroubleshootingReport({
      evidenceDir: directory,
      originReachability: async () => true,
    });
    assert.equal(troubleshooting.status, "BLOCKED_WITH_REASON");
    assert.ok(troubleshooting.blockers.every((blocker) => /^TB_[A-Z0-9_]+$/.test(blocker.code)));
    assert.doesNotMatch(JSON.stringify(troubleshooting), /approved-runtime|secret-token|must-not-escape/i);
  });
});

test("readiness blocks an invalid provider path", { concurrency: false }, async () => {
  await withReadinessConfiguration({ providerPath: join(tmpdir(), "missing-reviewed-provider.mjs") }, async ({ directory }) => {
    const readiness = await checkControlledPilotReadiness({
      evidenceDir: directory,
      originReachability: async () => true,
    });
    assert.equal(readiness.status, "BLOCKED_WITH_REASON");
    assert.equal(readiness.checks.find((item) => item.name === "provider_verification").reason, "TB_PROVIDER_MODULE_MISSING");
    assert.doesNotMatch(JSON.stringify(readiness), /missing-reviewed-provider|secret-token|must-not-escape/i);
  });
});

test("readiness reports provider verification failure by safe category", { concurrency: false }, async () => {
  await withReadinessConfiguration({
    runtimeSource: `export async function setupBrowserRuntime() { throw new Error("secret-token=must-not-escape"); }`,
  }, async ({ directory }) => {
    const readiness = await checkControlledPilotReadiness({
      evidenceDir: directory,
      originReachability: async () => true,
    });
    assert.equal(readiness.status, "BLOCKED_WITH_REASON");
    assert.equal(readiness.checks.find((item) => item.name === "provider_verification").reason, "TB_RUNTIME_UNAVAILABLE");
    assert.doesNotMatch(JSON.stringify(readiness), /secret-token|must-not-escape/i);
  });
});

test("readiness blocks an invalid image digest", { concurrency: false }, async () => {
  await withReadinessConfiguration({}, async ({ directory, manifestPath }) => {
    process.env.SENTINEL_DNA_IMAGE_DIGEST = "sha256:not-a-valid-digest";
    const readiness = await checkControlledPilotReadiness({
      evidenceDir: directory,
      originReachability: async () => true,
    });
    assert.equal(readiness.status, "BLOCKED_WITH_REASON");
    assert.equal(readiness.checks.find((item) => item.name === "image_digest").status, "BLOCKED");
    assert.equal(readiness.checks.find((item) => item.name === "activation_manifest").status, "PASS");
    assert.ok(manifestPath);
  });
});

test("readiness blocks an activation manifest for an invalid origin", { concurrency: false }, async () => {
  await withReadinessConfiguration({}, async ({ directory, manifestPath }) => {
    const manifest = {
      schema_version: "1.0",
      provider_identity: "reviewed-provider:test",
      runtime_module_identity: "reviewed-runtime:test",
      approved_runtime_module_digest: `sha256:${"a".repeat(64)}`,
      approved_image_runtime_digest: `sha256:${"a".repeat(64)}`,
      staging_origin: "https://example.invalid:18443",
      activation_timestamp: "2026-09-01T12:00:00Z",
      operator_approval_reference: "APPROVAL-TEST-001",
    };
    manifest.integrity = { algorithm: "sha256", manifest_hash: computeManifestHash(manifest) };
    await writeFile(manifestPath, `${JSON.stringify(manifest)}\n`, "utf8");
    const readiness = await checkControlledPilotReadiness({
      evidenceDir: directory,
      originReachability: async () => true,
    });
    assert.equal(readiness.status, "BLOCKED_WITH_REASON");
    assert.equal(readiness.checks.find((item) => item.name === "activation_manifest").reason, "TB_ORIGIN_REJECTED");
  });
});

test("readiness blocks a tampered activation manifest", { concurrency: false }, async () => {
  await withReadinessConfiguration({}, async ({ directory, manifestPath }) => {
    const manifest = {
      schema_version: "1.0",
      provider_identity: "reviewed-provider:test",
      runtime_module_identity: "reviewed-runtime:test",
      approved_runtime_module_digest: `sha256:${"a".repeat(64)}`,
      approved_image_runtime_digest: `sha256:${"a".repeat(64)}`,
      staging_origin: "https://uwakwe-desktop.taile388cc.ts.net",
      activation_timestamp: "2026-09-01T12:00:00Z",
      operator_approval_reference: "APPROVAL-TEST-001",
      integrity: { algorithm: "sha256", manifest_hash: "b".repeat(64) },
    };
    await writeFile(manifestPath, `${JSON.stringify(manifest)}\n`, "utf8");
    const readiness = await checkControlledPilotReadiness({
      evidenceDir: directory,
      originReachability: async () => true,
    });
    assert.equal(readiness.status, "BLOCKED_WITH_REASON");
    assert.equal(readiness.checks.find((item) => item.name === "activation_manifest").reason, "TB_PROVIDER_MANIFEST_INVALID");
  });
});

test("readiness succeeds with an isolated reviewed-runtime test fixture", { concurrency: false }, async () => {
  await withReadinessConfiguration({}, async ({ directory }) => {
    const readiness = await checkControlledPilotReadiness({
      evidenceDir: directory,
      originReachability: async (origin) => origin === "https://uwakwe-desktop.taile388cc.ts.net",
    });
    assert.equal(readiness.status, "READY_FOR_ANALYST_PILOT", JSON.stringify(readiness));
    assert.ok(readiness.checks.every((item) => item.status === "PASS"));
  });
});

test("readiness blocks failed certified-origin reachability without leaking secrets", { concurrency: false }, async () => {
  await withReadinessConfiguration({}, async ({ directory }) => {
    const readiness = await checkControlledPilotReadiness({
      evidenceDir: directory,
      originReachability: async () => false,
    });
    assert.equal(readiness.status, "BLOCKED_WITH_REASON");
    assert.equal(readiness.checks.find((item) => item.name === "certified_origin").status, "BLOCKED");
    assert.equal(
      readiness.checks.find((item) => item.name === "certified_origin").reason,
      "TB_ORIGIN_UNREACHABLE",
    );
    assert.doesNotMatch(JSON.stringify(readiness), /secret-token|must-not-escape|Bearer|eyJ/i);
  });
});

test("readiness blocks when tenant isolation is not enabled", { concurrency: false }, async () => {
  await withReadinessConfiguration({}, async ({ directory }) => {
    delete process.env.SENTINEL_DNA_TENANT_ISOLATION_ENABLED;
    const readiness = await checkControlledPilotReadiness({
      evidenceDir: directory,
      originReachability: async () => true,
    });
    assert.equal(readiness.status, "BLOCKED_WITH_REASON");
    assert.equal(readiness.checks.find((item) => item.name === "tenant_isolation").status, "BLOCKED");
    assert.equal(
      readiness.checks.find((item) => item.name === "tenant_isolation").reason,
      "SENTINEL_DNA_TENANT_ISOLATION_ENABLED must be 1",
    );
    assert.doesNotMatch(JSON.stringify(readiness), /secret-token|must-not-escape|Bearer|eyJ/i);
  });
});

test("readiness blocks when audit logging is not enabled", { concurrency: false }, async () => {
  await withReadinessConfiguration({}, async ({ directory }) => {
    delete process.env.SENTINEL_DNA_AUDIT_LOGGING_ENABLED;
    const readiness = await checkControlledPilotReadiness({
      evidenceDir: directory,
      originReachability: async () => true,
    });
    assert.equal(readiness.status, "BLOCKED_WITH_REASON");
    assert.equal(readiness.checks.find((item) => item.name === "audit_logging").status, "BLOCKED");
    assert.equal(
      readiness.checks.find((item) => item.name === "audit_logging").reason,
      "SENTINEL_DNA_AUDIT_LOGGING_ENABLED must be 1",
    );
    assert.doesNotMatch(JSON.stringify(readiness), /secret-token|must-not-escape|Bearer|eyJ/i);
  });
});

test("readiness report exposes safe provider and audit statuses", { concurrency: false }, async () => {
  await withReadinessConfiguration({}, async ({ directory }) => {
    const report = await generateTrustedBrowserReadinessReport({
      evidenceDir: directory,
      originReachability: async () => true,
    });
    assert.equal(report.status, "READY_FOR_ANALYST_PILOT");
    assert.equal(report.manifest_status, "PASS");
    assert.equal(report.provider_status, "PASS");
    assert.equal(report.image_digest_status, "PASS");
    assert.equal(report.origin_status, "PASS");
    assert.equal(report.tenant_isolation_status, "PASS");
    assert.equal(report.audit_status, "PASS");
    assert.equal(report.final_readiness_decision, "READY_FOR_ANALYST_PILOT");
    assert.deepEqual(
      report.checks.map((item) => item.name),
      [
        "provider_configured",
        "runtime_reachable",
        "browser_contract_valid",
        "origin_reachable",
        "browser_auth_available",
        "evidence_directory_writable",
        "audit_prerequisites_available",
        "activation_manifest_valid",
      ],
    );
    assert.ok(report.checks.every((item) => item.status === "PASS"));
    const troubleshooting = await generateTrustedBrowserActivationTroubleshootingReport({
      evidenceDir: directory,
      originReachability: async () => true,
    });
    assert.equal(troubleshooting.status, "READY_FOR_ANALYST_PILOT");
    assert.deepEqual(troubleshooting.blockers, []);
  });
});

test("readiness report blocks a provider without browserAuth", { concurrency: false }, async () => {
  await withReadinessConfiguration({
    runtimeSource: VALID_RUNTIME.replace(
      'name === "browserAuth" ? { request: async () => ({ status: "not-called" }) } : undefined',
      "undefined",
    ),
  }, async ({ directory }) => {
    const report = await generateTrustedBrowserReadinessReport({
      evidenceDir: directory,
      originReachability: async () => true,
    });
    assert.equal(report.status, "BLOCKED_WITH_REASON");
    assert.equal(
      report.checks.find((item) => item.name === "browser_auth_available").reason,
      "TB_AUTH_CAPABILITY_MISSING",
    );
    assert.doesNotMatch(JSON.stringify(report), /password|secret-token|must-not-escape/i);
  });
});

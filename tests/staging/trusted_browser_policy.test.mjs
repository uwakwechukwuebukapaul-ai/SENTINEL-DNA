import assert from "node:assert/strict";
import { test } from "node:test";

import { parseTrustedOrigin, parseTrustedNavigation } from "../../deployment/staging/scripts/trusted_browser_service/policy/origin-policy.mjs";
import { resolveAndValidateNetworkTarget, assertResolvedAddress } from "../../deployment/staging/scripts/trusted_browser_service/policy/network-policy.mjs";
import { createTenantContext, assertSameTenantContext } from "../../deployment/staging/scripts/trusted_browser_service/policy/tenant-context.mjs";
import { assertApprovedCapability, assertRestrictedBrowserSurface } from "../../deployment/staging/scripts/trusted_browser_service/policy/capability-policy.mjs";
import { assertNoSecretFields } from "../../deployment/staging/scripts/trusted_browser_service/policy/secret-fields.mjs";
import { createRuntimePolicy } from "../../deployment/staging/scripts/trusted_browser_service/policy/runtime-policy.mjs";

const CERTIFIED_ORIGIN = "https://staging.example.test";

test("origin policy canonicalizes only the configured HTTPS origin", () => {
  assert.equal(parseTrustedOrigin(CERTIFIED_ORIGIN, { certifiedOrigin: CERTIFIED_ORIGIN }).origin, CERTIFIED_ORIGIN);
  for (const value of [
    "http://staging.example.test",
    "https://staging.example.test.evil",
    "https://user:pass@staging.example.test",
    "https://staging.example.test/path",
    "https://staging.example.test?next=https://evil.example",
  ]) {
    assert.throws(() => parseTrustedOrigin(value, { certifiedOrigin: CERTIFIED_ORIGIN }), /TB_ORIGIN_REJECTED/);
  }
});

test("navigation policy permits paths but rejects origin and URL confusion", () => {
  assert.equal(
    parseTrustedNavigation("/login?step=1", { certifiedOrigin: CERTIFIED_ORIGIN }),
    `${CERTIFIED_ORIGIN}/login?step=1`,
  );
  for (const value of [
    "https://user:pass@staging.example.test/login",
    "https://staging.example.test.evil/login",
    "https://staging.example.test/login#fragment",
    "https://staging.example.test:444/login",
  ]) {
    assert.throws(() => parseTrustedNavigation(value, { certifiedOrigin: CERTIFIED_ORIGIN }), /TB_ORIGIN_REJECTED/);
  }
});

test("network policy rejects forbidden literal and resolved addresses", async () => {
  for (const address of [
    "127.0.0.1", "::1", "::ffff:127.0.0.1", "10.0.0.1", "172.16.0.1", "192.168.1.1",
    "169.254.169.254", "224.0.0.1", "0.0.0.0", "fc00::1", "fe80::1", "::",
  ]) {
    assert.throws(() => assertResolvedAddress(address), /TB_NETWORK_TARGET_REJECTED/);
  }
  await assert.rejects(
    resolveAndValidateNetworkTarget("http://metadata.google.internal/", {
      lookup: async () => [{ address: "203.0.113.10", family: 4 }],
    }),
    /TB_NETWORK_TARGET_REJECTED/,
  );
  await assert.rejects(
    resolveAndValidateNetworkTarget("https://public.example/", {
      lookup: async () => [{ address: "127.0.0.1", family: 4 }],
    }),
    /TB_NETWORK_TARGET_REJECTED/,
  );
  const result = await resolveAndValidateNetworkTarget("https://public.example/", {
    lookup: async () => [{ address: "203.0.113.10", family: 4 }],
  });
  assert.deepEqual(result.addresses, ["203.0.113.10"]);
});

test("tenant context is mandatory and cannot cross tenants", () => {
  const left = createTenantContext({ tenantId: "tenant-a", subjectId: "analyst-a" });
  const right = createTenantContext({ tenantId: "tenant-b", subjectId: "analyst-a" });
  assert.equal(assertSameTenantContext(left, left), true);
  assert.throws(() => assertSameTenantContext(left, right), /TB_TENANT_CONTEXT_MISMATCH/);
  assert.throws(() => createTenantContext({ tenantId: "tenant-a" }), /TB_TENANT_CONTEXT_INVALID/);
});

test("capability policy rejects raw browser surfaces and unknown capabilities", () => {
  const browser = { tabs: { new: async () => ({}) }, close: async () => {} };
  assert.equal(assertRestrictedBrowserSurface(browser), browser);
  assert.equal(assertApprovedCapability("browserAuth"), "browserAuth");
  assert.throws(() => assertApprovedCapability("rawPlaywright"), /TB_CAPABILITY_UNAVAILABLE/);
  assert.throws(() => assertRestrictedBrowserSurface({ newPage: () => {}, newContext: () => {} }), /TB_BROWSER_CONTRACT_FAILED/);
});

test("secret-field policy rejects credential-shaped inputs", () => {
  assert.equal(assertNoSecretFields({ environment: "test", fields: ["selector"] }), true);
  for (const value of [
    { password: "value" },
    { nested: { authorization: "Bearer value" } },
    { session_id: "value" },
  ]) {
    assert.throws(() => assertNoSecretFields(value), /TB_CREDENTIAL_FIELD_REJECTED/);
  }
});

test("runtime policy requires tenant context in production and binds navigation policy", async () => {
  assert.throws(
    () => createRuntimePolicy({ certifiedOrigin: CERTIFIED_ORIGIN, production: true }),
    /TB_TENANT_CONTEXT_INVALID/,
  );
  const policy = createRuntimePolicy({
    certifiedOrigin: CERTIFIED_ORIGIN,
    tenantContext: { tenantId: "tenant-a", subjectId: "analyst-a" },
    production: true,
    lookup: async () => [{ address: "203.0.113.10", family: 4 }],
  });
  assert.equal(await policy.validateNavigation("/login"), `${CERTIFIED_ORIGIN}/login`);
  assert.throws(() => policy.bindTenant({ tenantId: "tenant-b", subjectId: "analyst-a" }), /TB_TENANT_CONTEXT_MISMATCH/);
});

test("security context rejects session, authorization, and expiry mismatches", () => {
  const context = createTenantContext({
    tenantId: "tenant-a",
    subjectId: "analyst-a",
    sessionId: "session-a",
    authorizationContext: "manager",
  });
  assert.throws(() => assertSameTenantContext(context, { ...context, sessionId: "session-b" }), /TB_TENANT_CONTEXT_MISMATCH/);
  assert.throws(() => assertSameTenantContext(context, { ...context, authorizationContext: "viewer" }), /TB_TENANT_CONTEXT_MISMATCH/);
  assert.throws(() => createTenantContext({ tenantId: "tenant-a", subjectId: "analyst-a", expiresAt: Date.now() - 1 }), /TB_TENANT_CONTEXT_INVALID/);
});

test("production policy never permits a generic evaluation capability", () => {
  const policy = createRuntimePolicy({
    certifiedOrigin: CERTIFIED_ORIGIN,
    tenantContext: { tenantId: "tenant-a", subjectId: "analyst-a", sessionId: "session-a", authorizationContext: "manager" },
    production: true,
    lookup: async () => [{ address: "203.0.113.10", family: 4 }],
  });
  assert.equal(typeof policy.evaluate, "undefined");
  assert.deepEqual(policy.audit("tab.getTitle", { tenant: "tenant-a" }).tenantId, "tenant-a");
  assert.throws(() => policy.audit("tab.read", { authorization: "secret" }), /TB_CREDENTIAL_FIELD_REJECTED/);
});

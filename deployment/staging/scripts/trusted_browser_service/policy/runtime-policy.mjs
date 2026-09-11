import { parseTrustedOrigin, parseTrustedNavigation } from "./origin-policy.mjs";
import { resolveAndValidateNetworkTarget } from "./network-policy.mjs";
import { createTenantContext, assertSameTenantContext } from "./tenant-context.mjs";
import { assertApprovedCapability } from "./capability-policy.mjs";
import { assertNoSecretFields } from "./secret-fields.mjs";

/**
 * The single policy object shared by the provider boundary and candidate
 * runtime. It contains no deployment hostname and cannot be constructed
 * without an activation/configuration-supplied certified origin.
 */
export function createRuntimePolicy({
  certifiedOrigin,
  tenantContext,
  lookup,
  production = true,
  runtimeIdentity = null,
} = {}) {
  const origin = parseTrustedOrigin(certifiedOrigin, { certifiedOrigin }).origin;
  const tenant = tenantContext ? createTenantContext(tenantContext) : null;
  if (production && !tenant) throw new Error("TB_TENANT_CONTEXT_INVALID");
  return Object.freeze({
    origin,
    tenant,
    securityContext: tenant ? Object.freeze({ ...tenant }) : null,
    production: Boolean(production),
    runtimeIdentity,
    parseOrigin(value) { return parseTrustedOrigin(value, { certifiedOrigin: origin }).origin; },
    parseNavigation(value) { return parseTrustedNavigation(value, { certifiedOrigin: origin }); },
    async validateNavigation(value) {
      const href = parseTrustedNavigation(value, { certifiedOrigin: origin });
      if (production) await resolveAndValidateNetworkTarget(href, { lookup });
      return href;
    },
    bindTenant(actual) { assertSameTenantContext(tenant, actual); return true; },
    audit(operation, details = {}) {
      if (!tenant || typeof operation !== "string" || !operation.trim()) throw new Error("TB_AUDIT_CONTEXT_MISSING");
      assertNoSecretFields(details);
      return Object.freeze({ operation, ...tenant, details: Object.freeze({ ...details }) });
    },
    assertCapability(name) { return assertApprovedCapability(name); },
    assertNoSecrets(value) { return assertNoSecretFields(value); },
  });
}

const TENANT_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{1,127}$/;

export function createTenantContext({ tenantId, subjectId, sessionId = subjectId, authorizationContext = "analyst", correlationId = undefined, expiresAt = undefined } = {}) {
  const invalidExpiry = expiresAt !== undefined &&
    (!Number.isFinite(expiresAt) || expiresAt <= Date.now());
  if (typeof tenantId !== "string" || !TENANT_ID.test(tenantId) ||
      typeof subjectId !== "string" || !TENANT_ID.test(subjectId) ||
      typeof sessionId !== "string" || !TENANT_ID.test(sessionId) ||
      typeof authorizationContext !== "string" || !TENANT_ID.test(authorizationContext) ||
      (correlationId !== undefined && (typeof correlationId !== "string" || !TENANT_ID.test(correlationId))) ||
      invalidExpiry) {
    throw new Error("TB_TENANT_CONTEXT_INVALID");
  }
  return Object.freeze({ tenantId, subjectId, sessionId, authorizationContext, ...(correlationId === undefined ? {} : { correlationId }), ...(expiresAt === undefined ? {} : { expiresAt }) });
}

export function assertSameTenantContext(expected, actual) {
  if (!expected || !actual || expected.tenantId !== actual.tenantId ||
      expected.subjectId !== actual.subjectId || expected.sessionId !== actual.sessionId ||
      expected.authorizationContext !== actual.authorizationContext ||
      expected.correlationId !== actual.correlationId ||
      (expected.expiresAt !== undefined && expected.expiresAt <= Date.now())) {
    throw new Error("TB_TENANT_CONTEXT_MISMATCH");
  }
  return true;
}

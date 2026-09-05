/**
 * Pure trusted-browser origin policy.  The certified origin is supplied by
 * validated activation configuration; this module contains no deployment
 * hostname or environment-specific default.
 */

export function parseTrustedOrigin(value, { certifiedOrigin } = {}) {
  if (typeof value !== "string" || !value.trim() || typeof certifiedOrigin !== "string") {
    throw new Error("TB_ORIGIN_REJECTED");
  }

  let expected;
  let actual;
  try {
    expected = new URL(certifiedOrigin);
    actual = new URL(value);
  } catch {
    throw new Error("TB_ORIGIN_REJECTED");
  }

  if (
    expected.protocol !== "https:" ||
    expected.username ||
    expected.password ||
    expected.pathname !== "/" ||
    expected.search ||
    expected.hash ||
    actual.origin !== expected.origin ||
    actual.username ||
    actual.password ||
    actual.pathname !== "/" ||
    actual.search ||
    actual.hash
  ) {
    throw new Error("TB_ORIGIN_REJECTED");
  }

  return Object.freeze({ origin: actual.origin, hostname: actual.hostname });
}

export function configuredCertifiedOrigin(explicitValue = undefined) {
  const value = explicitValue ?? process.env?.SENTINEL_DNA_CERTIFIED_ORIGIN ?? process.env?.SENTINEL_DNA_BASE_URL;
  if (typeof value !== "string" || !value.trim()) throw new Error("TB_ORIGIN_REJECTED");
  return parseTrustedOrigin(value, { certifiedOrigin: value }).origin;
}

export function assertTrustedOrigin(value, options) {
  return parseTrustedOrigin(value, options).origin;
}

export function parseTrustedNavigation(value, { certifiedOrigin, allowQuery = true, allowFragment = false } = {}) {
  if (typeof value !== "string" || !value.trim() || typeof certifiedOrigin !== "string") {
    throw new Error("TB_ORIGIN_REJECTED");
  }
  let expected;
  let parsed;
  try {
    expected = new URL(certifiedOrigin);
    parsed = new URL(value, expected);
  } catch {
    throw new Error("TB_ORIGIN_REJECTED");
  }
  if (expected.protocol !== "https:" || expected.username || expected.password ||
      expected.pathname !== "/" || expected.search || expected.hash ||
      parsed.origin !== expected.origin || parsed.username || parsed.password ||
      (!allowQuery && parsed.search) || (!allowFragment && parsed.hash)) {
    throw new Error("TB_ORIGIN_REJECTED");
  }
  return parsed.href;
}

export function assertTrustedNavigation(value, options) {
  return parseTrustedNavigation(value, options);
}

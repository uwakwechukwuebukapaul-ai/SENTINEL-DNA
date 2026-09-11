const SECRET_PARTS = [
  "password", "passwd", "secret", "token", "api_key", "apikey",
  "authorization", "cookie", "credential", "privatekey", "jwt",
];

export function isSecretFieldName(key) {
  const normalized = String(key).toLowerCase().replace(/[^a-z0-9]/g, "");
  if (normalized === "sessionid") return key !== "sessionId";
  return SECRET_PARTS.some((part) => normalized.includes(part.replace(/[^a-z0-9]/g, "")));
}

export function assertNoSecretFields(value, seen = new WeakSet()) {
  if (!value || typeof value !== "object") return true;
  if (seen.has(value)) return true;
  seen.add(value);
  for (const [key, child] of Object.entries(value)) {
    const normalized = key.toLowerCase().replace(/[^a-z0-9]/g, "");
    if (isSecretFieldName(key)) {
      throw new Error("TB_CREDENTIAL_FIELD_REJECTED");
    }
    assertNoSecretFields(child, seen);
  }
  return true;
}

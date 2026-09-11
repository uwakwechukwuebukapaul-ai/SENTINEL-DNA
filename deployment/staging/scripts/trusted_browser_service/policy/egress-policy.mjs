import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import net from "node:net";
import { resolveAndValidateNetworkTarget, revalidateBeforeConnect } from "./network-policy.mjs";

export const EGRESS_POLICY_FILE_ENV = "SENTINEL_DNA_EGRESS_POLICY_FILE";
export const EGRESS_POLICY_DIGEST_ENV = "SENTINEL_DNA_EGRESS_POLICY_DIGEST";

function fail(code) { const error = new Error(code); error.code = code; throw error; }

function canonicalJson(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
}

function assertHostname(hostname) {
  if (typeof hostname !== "string" || !/^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/i.test(hostname) || net.isIP(hostname)) fail("TB_EGRESS_POLICY_INVALID");
  return hostname.toLowerCase();
}

export function validateEgressPolicy(value) {
  if (!value || typeof value !== "object" || Array.isArray(value) || value.schema !== "sentinel-dna-egress-policy-v1" || !Array.isArray(value.destinations) || value.destinations.length === 0) fail("TB_EGRESS_POLICY_INVALID");
  const schemes = value.schemes;
  const ports = value.ports;
  if (!Array.isArray(schemes) || !schemes.length || schemes.some((item) => !["https"].includes(item))) fail("TB_EGRESS_POLICY_INVALID");
  if (!Array.isArray(ports) || !ports.length || ports.some((item) => !Number.isInteger(item) || item < 1 || item > 65535)) fail("TB_EGRESS_POLICY_INVALID");
  const destinations = value.destinations.map((item) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) fail("TB_EGRESS_POLICY_INVALID");
    const hostname = assertHostname(item.hostname);
    const itemPorts = item.ports ?? ports;
    if (!Array.isArray(itemPorts) || itemPorts.some((port) => !ports.includes(port))) fail("TB_EGRESS_POLICY_INVALID");
    return Object.freeze({ hostname, ports: Object.freeze([...new Set(itemPorts)]) });
  });
  return Object.freeze({ schema: value.schema, schemes: Object.freeze([...new Set(schemes)]), ports: Object.freeze([...new Set(ports)]), destinations: Object.freeze(destinations) });
}

export async function loadEgressPolicy({ env = process.env, read = readFile } = {}) {
  const path = env?.[EGRESS_POLICY_FILE_ENV];
  const expected = env?.[EGRESS_POLICY_DIGEST_ENV];
  if (typeof path !== "string" || !path.trim() || typeof expected !== "string" || !/^sha256:[a-f0-9]{64}$/i.test(expected)) fail("TB_EGRESS_POLICY_UNAVAILABLE");
  let bytes;
  try { bytes = await read(path); } catch { fail("TB_EGRESS_POLICY_UNAVAILABLE"); }
  const actual = `sha256:${createHash("sha256").update(bytes).digest("hex")}`;
  if (actual.toLowerCase() !== expected.toLowerCase()) fail("TB_EGRESS_POLICY_DIGEST_MISMATCH");
  let parsed;
  try { parsed = JSON.parse(bytes.toString("utf8")); } catch { fail("TB_EGRESS_POLICY_INVALID"); }
  return Object.freeze({ policy: validateEgressPolicy(parsed), digest: actual });
}

export function validateDestination(url, policy) {
  const parsed = (() => { try { return new URL(url); } catch { fail("TB_DESTINATION_REJECTED"); } })();
  if (!policy || !policy.schemes.includes(parsed.protocol.slice(0, -1)) || !policy.ports.includes(Number(parsed.port || 443)) || parsed.username || parsed.password || parsed.hash) fail("TB_DESTINATION_REJECTED");
  const destination = policy.destinations.find((item) => item.hostname === parsed.hostname.toLowerCase() && item.ports.includes(Number(parsed.port || 443)));
  if (!destination) fail("TB_DESTINATION_REJECTED");
  return Object.freeze({ url: parsed.href, hostname: parsed.hostname.toLowerCase(), port: Number(parsed.port || 443) });
}

export async function authorizeConnection({ url, policy, lookup, previousAddresses } = {}) {
  const destination = validateDestination(url, policy);
  const resolved = await resolveAndValidateNetworkTarget(destination.url, { lookup });
  if (previousAddresses) await revalidateBeforeConnect({ hostname: destination.hostname, addresses: previousAddresses, lookup });
  return Object.freeze({ ...destination, addresses: resolved.addresses });
}

export { canonicalJson };

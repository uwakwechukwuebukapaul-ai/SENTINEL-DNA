import dns from "node:dns/promises";
import net from "node:net";

const METADATA_HOSTS = new Set([
  "169.254.169.254",
  "metadata.google.internal",
  "metadata.google.internal.",
  "instance-data.ec2.internal",
]);

function ipv4Parts(address) {
  return address.split(".").map(Number);
}

function normalizeAddress(address) {
  const value = String(address).trim().toLowerCase();
  const mapped = value.match(/^::ffff:(\d+\.\d+\.\d+\.\d+)$/i);
  return mapped ? mapped[1] : value;
}

function inIpv4(address, [network, mask]) {
  const value = ipv4Parts(address);
  const base = ipv4Parts(network);
  return value.every((part, index) => (part & mask[index]) === (base[index] & mask[index]));
}

function isForbiddenIp(address) {
  address = normalizeAddress(address);
  const family = net.isIP(address);
  if (family === 4) {
    const masks = [
      ["0.0.0.0", [255, 0, 0, 0]],
      ["10.0.0.0", [255, 0, 0, 0]],
      ["100.64.0.0", [255, 192, 0, 0]],
      ["127.0.0.0", [255, 0, 0, 0]],
      ["169.254.0.0", [255, 255, 0, 0]],
      ["172.16.0.0", [255, 240, 0, 0]],
      ["192.0.0.0", [255, 255, 255, 0]],
      ["192.168.0.0", [255, 255, 0, 0]],
      ["192.0.2.0", [255, 255, 255, 0]],
      ["198.18.0.0", [255, 254, 0, 0]],
      ["198.51.100.0", [255, 255, 255, 0]],
      ["203.0.113.0", [255, 255, 255, 0]],
      ["224.0.0.0", [240, 0, 0, 0]],
    ];
    return masks.some((entry) => inIpv4(address, entry));
  }
  if (family === 6) {
    const normalized = address.toLowerCase();
    return normalized === "::" || normalized === "::1" ||
      normalized.startsWith("fc") || normalized.startsWith("fd") ||
      normalized.startsWith("fe8") || normalized.startsWith("fe9") ||
      normalized.startsWith("fea") || normalized.startsWith("feb") ||
      normalized.startsWith("ff") || /^2001:(?:0{0,3})db8:/i.test(normalized);
  }
  return false;
}

export async function resolveAndValidateNetworkTarget(url, { lookup = dns.lookup } = {}) {
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    throw new Error("TB_NETWORK_TARGET_REJECTED");
  }
  if (parsed.protocol !== "https:" || parsed.username || parsed.password || parsed.port && parsed.port !== "443") {
    throw new Error("TB_NETWORK_TARGET_REJECTED");
  }
  const hostname = parsed.hostname.toLowerCase().replace(/^\[|\]$/g, "").replace(/\.$/, "");
  if (net.isIP(hostname) !== 0) throw new Error("TB_NETWORK_TARGET_REJECTED");
  if (METADATA_HOSTS.has(hostname) || isForbiddenIp(hostname)) {
    throw new Error("TB_NETWORK_TARGET_REJECTED");
  }

  let results;
  try {
    results = await lookup(hostname, { all: true, verbatim: true });
  } catch {
    throw new Error("TB_NETWORK_TARGET_REJECTED");
  }
  if (!Array.isArray(results) || results.length === 0 || results.some((item) => !item || isForbiddenIp(item.address))) {
    throw new Error("TB_NETWORK_TARGET_REJECTED");
  }
  return Object.freeze({ origin: parsed.origin, hostname, addresses: results.map((item) => item.address) });
}

export async function revalidateBeforeConnect({ hostname, addresses, lookup = dns.lookup } = {}) {
  if (typeof hostname !== "string" || !hostname || !Array.isArray(addresses) || !addresses.length) {
    throw new Error("TB_NETWORK_TOCTOU_REJECTED");
  }
  let current;
  try { current = await lookup(hostname, { all: true, verbatim: true }); } catch { throw new Error("TB_NETWORK_TOCTOU_REJECTED"); }
  if (!Array.isArray(current) || !current.length) throw new Error("TB_NETWORK_TOCTOU_REJECTED");
  const original = new Set(addresses.map((address) => normalizeAddress(address)));
  const currentAddresses = current.map((item) => item?.address);
  if (currentAddresses.some((address) => !address || isForbiddenIp(address) || !original.has(normalizeAddress(address)))) {
    throw new Error("TB_NETWORK_TOCTOU_REJECTED");
  }
  return Object.freeze(currentAddresses);
}

export function assertResolvedAddress(address) {
  if (net.isIP(address) === 0 || isForbiddenIp(address)) throw new Error("TB_NETWORK_TARGET_REJECTED");
  return address;
}

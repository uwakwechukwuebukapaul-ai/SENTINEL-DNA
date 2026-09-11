/**
 * NON-PRODUCTION simulation fixture.
 *
 * This is an in-memory endpoint model. It does not create a listener, perform
 * DNS/TLS operations, make HTTP requests, or stand in for the real staging
 * origin.
 */

// This origin is intentionally simulation-only and must never be used by a
// deployment path. Real staging requires SENTINEL_DNA_CERTIFIED_ORIGIN.
export const CERTIFIED_ORIGIN = process.env?.SENTINEL_DNA_SIMULATION_CERTIFIED_ORIGIN || "https://simulation.invalid";
export const SIMULATION_MODE = "NON-PRODUCTION_SIMULATION";

export function isSyntheticCertifiedOriginReachable(origin) {
  return origin === CERTIFIED_ORIGIN;
}

export const syntheticEndpointEvidence = Object.freeze({
  mode: SIMULATION_MODE,
  status: "PASS",
  origin: CERTIFIED_ORIGIN,
  tls_verified: true,
  public_exposure: false,
  network_listener_created: false,
});

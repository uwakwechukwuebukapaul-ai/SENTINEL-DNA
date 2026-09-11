# External approved Playwright runtime contract

The trusted-browser image requires an operator-supplied module at the path
provided by `SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME`. The repository does not
contain, generate, or substitute this module.

The module must export exactly the reviewed runtime entrypoint:

```js
export async function setupBrowserRuntime({
  environment,
  certifiedOrigin,
  tenantContext,
  securityMode,
}) {
  return {
    browsers: {
      async getForUrl(certifiedOrigin) {
        return {
          tabs: {
            async new() { /* native objects remain inside this runtime */ },
          },
        };
      },
    },
    async close() {},
  };
}
```

Required contract properties:

- `environment` must be `codex-app`.
- `certifiedOrigin` must be the validated runtime-injected HTTPS origin.
- `tenantContext` and `securityMode` must be accepted without credential
  fields; production setup uses `securityMode: "trusted-rpc"`.
- `setupBrowserRuntime` must return `browsers.getForUrl` and the selected
  browser must expose only the reviewed provider surface.
- Native Playwright, filesystem, socket, download, CDP, and page objects must
  remain inside the external runtime and must never cross the RPC boundary.
- The module must not be a repository path, test fixture, stub, mock, or fake.

The image build contract is fail-closed:

1. The external path is injected through `SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME`.
2. The expected SHA-256 is injected through
   `SENTINEL_DNA_APPROVED_RUNTIME_DIGEST`.
3. `verify-image-inputs.mjs` requires the file, verifies its bytes against the
   supplied digest, dynamically verifies the `setupBrowserRuntime` export, and
   records the identity in the deterministic build-input manifest.
   The base image digest is marked verified only when a separate registry tool
   has supplied the digest and the explicit verification attestation
   `SENTINEL_DNA_BASE_IMAGE_DIGEST_VERIFIED=true`.
4. Missing bytes, malformed digests, export mismatch, dependency mismatch, or
   path-policy violations fail the build before the runtime can start.
5. The runtime is copied into the image only from the externally supplied
   build context at `runtime/approved-playwright-runtime.mjs` and is not
   sourced from repository code.
6. Later custody must bind the exact module bytes, dependency closure, review
   identity, and supplied digest to the activation manifest. Until that
   custody exists, runtime provenance remains blocked.

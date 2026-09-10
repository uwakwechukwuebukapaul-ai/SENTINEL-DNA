# syntax=docker/dockerfile:1.7

ARG PLAYWRIGHT_BASE_IMAGE
FROM ${PLAYWRIGHT_BASE_IMAGE}

USER root

ARG PLAYWRIGHT_BASE_IMAGE
# Release images must be addressed by a content digest. A mutable tag is never
# accepted, and malformed digests fail the build before any image is produced.
RUN node -e "const v=process.env.PLAYWRIGHT_BASE_IMAGE||''; if (!/^\\S+@sha256:[0-9a-f]{64}$/i.test(v)) { console.error('TB_IMAGE_BASE_REFERENCE_NOT_IMMUTABLE'); process.exit(1); }"

ARG SENTINEL_DNA_SOURCE_COMMIT
ARG SENTINEL_DNA_SOURCE_TREE
ARG SENTINEL_DNA_ARTIFACT_SHA256
ARG SENTINEL_DNA_DEPENDENCY_LOCK_SHA256
ARG SENTINEL_DNA_BASE_IMAGE_DIGEST
ARG SENTINEL_DNA_BUILD_ID
ARG SENTINEL_DNA_APPROVED_RUNTIME_DIGEST
ARG SENTINEL_DNA_BROWSER_EXECUTABLE_SHA256
ARG SENTINEL_DNA_BROWSER_PLATFORM=linux
ARG SENTINEL_DNA_BROWSER_ARCH=x64
ARG SENTINEL_DNA_BASE_IMAGE_DIGEST_VERIFIED=false

ENV NODE_ENV=production \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
    SENTINEL_DNA_TRUSTED_BROWSER_SOURCE_ROOT=/opt/sentinel/trusted-browser \
    SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME=/opt/sentinel/trusted-browser/deployment/staging/scripts/trusted_browser_service/providers/approved-playwright-runtime.mjs \
    SENTINEL_DNA_BROWSER_EXECUTABLE=/ms-playwright/chromium-1234/chrome-linux64/chrome \
    SENTINEL_DNA_SOURCE_COMMIT=${SENTINEL_DNA_SOURCE_COMMIT} \
    SENTINEL_DNA_SOURCE_TREE=${SENTINEL_DNA_SOURCE_TREE} \
    SENTINEL_DNA_ARTIFACT_SHA256=${SENTINEL_DNA_ARTIFACT_SHA256} \
    SENTINEL_DNA_DEPENDENCY_LOCK_SHA256=${SENTINEL_DNA_DEPENDENCY_LOCK_SHA256} \
    SENTINEL_DNA_BASE_IMAGE_DIGEST=${SENTINEL_DNA_BASE_IMAGE_DIGEST} \
    SENTINEL_DNA_BUILD_ID=${SENTINEL_DNA_BUILD_ID} \
    SENTINEL_DNA_APPROVED_RUNTIME_DIGEST=${SENTINEL_DNA_APPROVED_RUNTIME_DIGEST} \
    SENTINEL_DNA_BROWSER_EXECUTABLE_SHA256=${SENTINEL_DNA_BROWSER_EXECUTABLE_SHA256} \
    SENTINEL_DNA_BROWSER_PLATFORM=${SENTINEL_DNA_BROWSER_PLATFORM} \
    SENTINEL_DNA_BROWSER_ARCH=${SENTINEL_DNA_BROWSER_ARCH} \
    SENTINEL_DNA_BASE_IMAGE_DIGEST_VERIFIED=${SENTINEL_DNA_BASE_IMAGE_DIGEST_VERIFIED}

WORKDIR /opt/sentinel/trusted-browser

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --omit=dev --no-audit --no-fund

COPY deployment/staging/scripts/controlled_analyst_pilot_runner.mjs deployment/staging/scripts/controlled_analyst_pilot_runner.mjs
COPY deployment/staging/scripts/trusted_browser_diagnostics.mjs deployment/staging/scripts/trusted_browser_diagnostics.mjs
COPY deployment/staging/scripts/trusted_browser_activation_manifest.mjs deployment/staging/scripts/trusted_browser_activation_manifest.mjs
COPY deployment/staging/scripts/trusted_browser_execution_adapter.mjs deployment/staging/scripts/trusted_browser_execution_adapter.mjs
COPY deployment/staging/scripts/trusted_browser_service deployment/staging/scripts/trusted_browser_service
COPY deployment/staging/trusted_browser_runtime/runtime-service.mjs deployment/staging/trusted_browser_runtime/runtime-service.mjs
COPY deployment/staging/trusted_browser_runtime/rpc-client.mjs deployment/staging/trusted_browser_runtime/rpc-client.mjs
COPY deployment/staging/trusted_browser_runtime/healthcheck.mjs deployment/staging/trusted_browser_runtime/healthcheck.mjs
COPY deployment/staging/trusted_browser_runtime/verify-image-inputs.mjs deployment/staging/trusted_browser_runtime/verify-image-inputs.mjs

# The custody runtime is intentionally absent from the repository source tree.
# A future custody-controlled build context must provide this exact file.
COPY runtime/approved-playwright-runtime.mjs deployment/staging/scripts/trusted_browser_service/providers/approved-playwright-runtime.mjs

RUN node deployment/staging/trusted_browser_runtime/verify-image-inputs.mjs

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin trustedbrowser \
    && chown -R trustedbrowser:trustedbrowser /opt/sentinel/trusted-browser

USER trustedbrowser
EXPOSE 3000
ENTRYPOINT ["node", "deployment/staging/trusted_browser_runtime/runtime-service.mjs"]

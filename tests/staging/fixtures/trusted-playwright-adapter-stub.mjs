/**
 * Test-only upstream adapter for the checked-in trusted browser facade.
 *
 * This is not a browser implementation and must never be configured for the
 * controlled analyst pilot. It provides the reviewed client's shape without
 * launching a browser, opening a socket, making HTTP requests, or accepting
 * credential values. An operator-supplied reviewed Playwright client remains
 * required for any real authenticated run.
 */

export const state = {
  selectedOrigins: [],
  navigated: [],
  authRequests: [],
};

const CERTIFIED_ORIGIN = "https://sentinel-dna-staging:18443";

function assertCertifiedUrl(url) {
  const parsed = new URL(url);
  if (parsed.origin !== CERTIFIED_ORIGIN) {
    throw new Error("test stub only permits the certified staging origin");
  }
  return parsed.href;
}

function locator(selector) {
  return Object.freeze({
    selector,
    count: async () => 1,
    isVisible: async () => true,
    isEnabled: async () => true,
    fill: async () => {},
    click: async () => {},
    textContent: async () => "",
  });
}

function createTab() {
  return {
    id: "staging-test-tab",
    goto: async (url) => {
      const safeUrl = assertCertifiedUrl(url);
      state.navigated.push(safeUrl);
    },
    close: async () => {},
    playwright: {
      locator,
      evaluate: async () => ({ status: 200, body: { safe: true } }),
    },
    dom_cua: {
      get_visible_dom: async () => ({ page: "staging-test-fixture" }),
    },
    capabilities: {
      get: async (name) => name === "browserAuth"
        ? {
            request: async (request) => {
              state.authRequests.push({
                origin: request.origin,
                fieldCount: request.fields?.length ?? 0,
              });
              return { status: "stubbed" };
            },
          }
        : undefined,
    },
  };
}

const browser = Object.freeze({
  tabs: Object.freeze({
    new: async () => createTab(),
  }),
});

export async function setupBrowserRuntime({ environment } = {}) {
  if (environment !== "codex-app") {
    throw new Error("test stub requires codex-app");
  }
  return Object.freeze({
    browsers: Object.freeze({
      getForUrl: async (origin) => {
        if (origin !== CERTIFIED_ORIGIN) {
          throw new Error("test stub only permits the certified origin");
        }
        state.selectedOrigins.push(origin);
        return browser;
      },
    }),
  });
}

const ALLOWED_CAPABILITIES = new Set(["browserAuth"]);
const ALLOWED_BROWSER_CALLABLES = new Set(["close"]);

export function assertApprovedCapability(name) {
  if (!ALLOWED_CAPABILITIES.has(name)) throw new Error("TB_CAPABILITY_UNAVAILABLE");
  return name;
}

export function assertRestrictedBrowserSurface(browser) {
  if (!browser || typeof browser !== "object" ||
      typeof browser.newPage === "function" ||
      typeof browser.newContext === "function" ||
      !browser.tabs || typeof browser.tabs !== "object" ||
      typeof browser.tabs.new !== "function") {
    throw new Error("TB_BROWSER_CONTRACT_FAILED");
  }
  for (const [key, value] of Object.entries(browser)) {
    if (typeof value === "function" && !ALLOWED_BROWSER_CALLABLES.has(key)) {
      throw new Error("TB_BROWSER_CONTRACT_FAILED");
    }
  }
  return browser;
}

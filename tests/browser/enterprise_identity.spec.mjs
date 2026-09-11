import test from "node:test";
import assert from "node:assert/strict";
import { chromium } from "playwright";

const baseURL = process.env.SENTINEL_DNA_BASE_URL || "https://localhost";
const isLocalhost = new URL(baseURL).hostname === "localhost";

async function openBrowserPage(browser, path) {
  const contextOptions = isLocalhost ? { ignoreHTTPSErrors: true } : {};
  const context = await browser.newContext(contextOptions);
  const page = await context.newPage();
  const url = new URL(path, baseURL).toString();

  try {
    const response = await page.goto(url);
    if (!response) {
      throw new Error("navigation returned no response");
    }
    if (response.status() >= 500) {
      throw new Error(`server returned HTTP ${response.status()}`);
    }
    return { context, page };
  } catch (error) {
    await context.close();
    await browser.close();
    const reason = error instanceof Error ? error.message : String(error);
    assert.fail(`Failed to navigate to ${url}: ${reason}`);
  }
}

test.describe("Sentinel DNA enterprise identity surfaces", () => {
  test("login exposes password, federation, and passkey readiness", async (t) => {
    const browser = await chromium.launch({ headless: true }).catch(() => null);
    if (!browser) return t.skip("Chromium is not installed");
    const { context, page } = await openBrowserPage(browser, "/login");
    try {
      assert.equal(await page.getByLabel("Work email").isVisible(), true);
      assert.equal(await page.getByRole("button", { name: /Use passkey/ }).isVisible(), true);
      assert.equal(await page.locator("[data-idp-selector]").isVisible(), true);
    } finally {
      await context.close();
      await browser.close();
    }
  });

  test("signup exposes an accessible country selector", async (t) => {
    const browser = await chromium.launch({ headless: true }).catch(() => null);
    if (!browser) return t.skip("Chromium is not installed");
    const { context, page } = await openBrowserPage(browser, "/signup");
    try {
      const trigger = page.getByRole("button", { name: /Select country/ });
      assert.equal(await trigger.isVisible(), true);
      await trigger.click();
      assert.equal(await page.getByRole("searchbox", { name: "Search countries" }).isVisible(), true);
    } finally {
      await context.close();
      await browser.close();
    }
  });
});

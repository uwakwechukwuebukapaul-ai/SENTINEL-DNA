import test from "node:test";
import assert from "node:assert/strict";
import { chromium } from "playwright";

const baseURL = process.env.SENTINEL_DNA_BASE_URL || "https://localhost";

test.describe("Sentinel DNA enterprise identity surfaces", () => {
  test("login exposes password, federation, and passkey readiness", async (t) => {
    const browser = await chromium.launch({ headless: true }).catch(() => null);
    if (!browser) return t.skip("Chromium is not installed");
    const page = await browser.newPage(); const response = await page.goto(`${baseURL}/login`).catch(() => null);
    if (!response || response.status() >= 500) { await browser.close(); return t.skip("Sentinel DNA server is not available"); }
    assert.equal(await page.getByLabel("Work email").isVisible(), true); assert.equal(await page.getByRole("button", { name: /Use passkey/ }).isVisible(), true); assert.equal(await page.locator("[data-idp-selector]").isVisible(), true); await browser.close();
  });

  test("signup exposes an accessible country selector", async (t) => {
    const browser = await chromium.launch({ headless: true }).catch(() => null);
    if (!browser) return t.skip("Chromium is not installed");
    const page = await browser.newPage(); const response = await page.goto(`${baseURL}/signup`).catch(() => null);
    if (!response || response.status() >= 500) { await browser.close(); return t.skip("Sentinel DNA server is not available"); }
    const trigger = page.getByRole("button", { name: /Select country/ }); assert.equal(await trigger.isVisible(), true); await trigger.click(); assert.equal(await page.getByRole("searchbox", { name: "Search countries" }).isVisible(), true); await browser.close();
  });
});

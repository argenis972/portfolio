import { test, expect } from '@playwright/test';

/**
 * Chaos Playground E2E Smoke Tests
 *
 * Verifies that each chaos action button (Drain, Retry, Latency) fires a
 * POST request to the backend that returns a 2xx response.
 *
 * Strategy: intercept network calls with `page.waitForResponse` so we
 * validate the real network round-trip without relying on UI copy.
 *
 * Prerequisites:
 *  - The app must be running at BASE_URL (set env var or use local dev server)
 *  - VITE_ENABLE_CHAOS_PLAYGROUND=true must be set in the build
 */

const CHAOS_ENDPOINTS = [
  { name: 'drain',   path: '/api/v1/chaos/drain' },
  { name: 'retry',   path: '/api/v1/chaos/retry' },
  { name: 'latency', path: '/api/v1/chaos/latency' },
] as const;

test.describe('Chaos Playground — smoke tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the main page and wait until network is idle
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  for (const { name, path } of CHAOS_ENDPOINTS) {
    test(`chaos.${name} button sends POST and receives 2xx`, async ({ page }) => {
      // Locate the button by its data-testid attribute
      const button = page.locator(`[data-testid="chaos-btn-${name}"]`);

      // Wait for the button to be visible (Chaos Playground section must be enabled)
      await expect(button).toBeVisible({ timeout: 10_000 });

      // Intercept the network response BEFORE clicking the button
      const [response] = await Promise.all([
        page.waitForResponse(
          (res) => res.url().includes(path) && res.request().method() === 'POST',
          { timeout: 15_000 },
        ),
        button.click(),
      ]);

      // Assert the backend returned a successful status
      expect(response.status(), `Expected 2xx for ${path}`).toBeLessThan(300);
    });
  }
});

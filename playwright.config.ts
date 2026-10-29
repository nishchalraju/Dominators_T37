import { defineConfig, devices } from '@playwright/test'

/**
 * End-to-end tests drive a REAL browser against a REAL running server (backend + built frontend).
 *
 *   1. npm run build
 *   2. start the backend:   cd backend && python -m uvicorn app.main:app --port 8000     (fresh database recommended:
 *      the first account that registers becomes the administrator, which the admin-only steps need)
 *   3. npm run test:e2e
 *
 * Point it elsewhere with E2E_BASE_URL.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8000',
    locale: 'en-IN',
    timezoneId: 'Asia/Calcutta',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})

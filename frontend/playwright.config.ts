import {defineConfig, devices} from '@playwright/test';

// Tests target an explicitly started local stack. No server, browser download,
// dependency installation, dataset acquisition or model training is launched.
export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90_000,
  expect: {timeout: 15_000},
  reporter: [['list']],
  outputDir: '../artifacts/browser-tests',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'off',
    video: 'off',
    screenshot: 'off',
    actionTimeout: 15_000,
  },
  projects: [
    {name: 'desktop-chromium', use: {...devices['Desktop Chrome']}},
    {name: 'mobile-chromium', use: {...devices['Pixel 7']}},
  ],
});

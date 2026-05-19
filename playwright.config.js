// @ts-check
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  retries: 0,
  use: {
    baseURL: 'http://localhost:8000',
    locale: 'ru-RU',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'tests/e2e/report' }],
  ],
});

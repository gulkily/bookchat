const { defineConfig } = require('@playwright/test');

// Get port from environment variable or default to 5000
const PORT = process.env.SERVER_PORT || 5000;

module.exports = defineConfig({
  testDir: './__tests__',
  testMatch: '**/*.test.js',  // Run all test files
  use: {
    baseURL: `http://localhost:${PORT}`,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    headless: false,  // Run in headed mode
    launchOptions: {
      slowMo: 500,  // Slow down each action by 500ms
    },
  },
  // Show browser logs in terminal
  reporter: [['list'], ['html']],
});

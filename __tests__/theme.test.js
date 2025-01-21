const { test, expect } = require('@playwright/test');

// Get port from environment variable or default to 5000
const PORT = process.env.SERVER_PORT || 5000;

test.describe('Theme System', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`http://localhost:${PORT}`);
  });

  test('default theme matches system preference', async ({ page }) => {
    // Check if body has correct theme class based on system preference
    const isDarkMode = await page.evaluate(() => 
      window.matchMedia('(prefers-color-scheme: dark)').matches
    );
    const expectedClass = isDarkMode ? 'dark-theme' : 'light-theme';
    await expect(page.locator('body')).toHaveClass(new RegExp(expectedClass));
  });

  test('theme toggle button works', async ({ page }) => {
    // Get initial theme
    const initialTheme = await page.evaluate(() => 
      document.body.classList.contains('dark-theme') ? 'dark' : 'light'
    );

    // Click theme toggle
    await page.click('#theme-toggle');

    // Verify theme changed
    const newTheme = initialTheme === 'dark' ? 'light' : 'dark';
    await expect(page.locator('body')).toHaveClass(`${newTheme}-theme`);

    // Verify theme persists after reload
    await page.reload();
    await expect(page.locator('body')).toHaveClass(`${newTheme}-theme`);
  });

  test('theme affects element colors', async ({ page }) => {
    // Force dark theme
    await page.evaluate(() => {
      localStorage.setItem('theme', 'dark');
      document.body.classList.remove('light-theme');
      document.body.classList.add('dark-theme');
    });
    await page.reload();

    // Check key elements have correct dark theme colors
    const messageInput = page.locator('#message-input');
    const sendButton = page.locator('#send-button');
    const messagesContainer = page.locator('#messages');

    // Get computed styles
    const inputBg = await messageInput.evaluate(el => 
      window.getComputedStyle(el).getPropertyValue('background-color')
    );
    const buttonBg = await sendButton.evaluate(el => 
      window.getComputedStyle(el).getPropertyValue('background-color')
    );
    const containerBg = await messagesContainer.evaluate(el => 
      window.getComputedStyle(el).getPropertyValue('background-color')
    );

    // Convert rgb/rgba to hex for easier comparison
    const rgbToHex = (rgb) => {
      const values = rgb.match(/\d+/g);
      return `#${values.map(x => parseInt(x).toString(16).padStart(2, '0')).join('')}`;
    };

    // Verify dark theme colors
    expect(rgbToHex(inputBg)).toBe('#2d2d2d');  // --input-bg
    expect(rgbToHex(buttonBg)).toBe('#3b82f6');  // --button-bg
    expect(rgbToHex(containerBg)).toBe('#1a1a1a');  // --bg-primary
  });

  test('theme affects text colors', async ({ page }) => {
    // Force dark theme
    await page.evaluate(() => {
      localStorage.setItem('theme', 'dark');
      document.body.classList.remove('light-theme');
      document.body.classList.add('dark-theme');
    });
    await page.reload();

    // Add a test message
    await page.fill('#message-input', 'Test Message');
    await page.click('#send-button');

    // Check text colors
    const messageText = page.locator('.message .content').last();
    const textColor = await messageText.evaluate(el => 
      window.getComputedStyle(el).getPropertyValue('color')
    );

    // Convert rgb/rgba to hex
    const rgbToHex = (rgb) => {
      const values = rgb.match(/\d+/g);
      return `#${values.map(x => parseInt(x).toString(16).padStart(2, '0')).join('')}`;
    };

    // Verify dark theme text color
    expect(rgbToHex(textColor)).toBe('#e2e8f0');  // --text-primary
  });
});

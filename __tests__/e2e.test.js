const { test, expect } = require('@playwright/test');

// Get port from environment variable or default to 5000
const PORT = process.env.SERVER_PORT || 5000;

// Helper function to highlight an element
async function highlight(element) {
  await element.evaluate((node) => {
    const originalBackground = node.style.backgroundColor;
    const originalTransition = node.style.transition;
    node.style.transition = 'background-color 0.5s';
    node.style.backgroundColor = 'yellow';
    setTimeout(() => {
      node.style.backgroundColor = originalBackground;
      node.style.transition = originalTransition;
    }, 500);
  });
}

test.describe('BookChat Frontend', () => {
  test.beforeEach(async ({ page }) => {
    // Make sure the Python server is running before each test
    try {
      await page.goto(`http://localhost:${PORT}`);
    } catch (error) {
      throw new Error(
        `Unable to connect to server at http://localhost:${PORT}. ` +
        'Make sure the Python server is running and the SERVER_PORT ' +
        'environment variable matches the server\'s port.'
      );
    }
  });

  test('message input and send functionality', async ({ page }) => {
    // Wait for the message input to be available
    const messageInput = page.locator('#message-input');
    await messageInput.waitFor({ state: 'visible' });
    await highlight(messageInput);
    
    // Type a message
    const testMessage = 'Hello from Playwright!';
    await messageInput.fill(testMessage);
    
    // Click send button
    const sendButton = page.locator('#send-button');
    await highlight(sendButton);
    await sendButton.click();
    
    // Wait for message to appear in the messages container
    const messageContent = page.locator('.message .content').last();
    await expect(messageContent).toContainText(testMessage, {
      timeout: 5000
    });
    await highlight(messageContent);
  });

  test('message sending status transitions correctly', async ({ page }) => {
    // Wait for the message input to be available
    const messageInput = page.locator('#message-input');
    await messageInput.waitFor({ state: 'visible' });
    await highlight(messageInput);
    
    // Type and send a message
    const testMessage = 'Testing message status';
    await messageInput.fill(testMessage);
    
    const sendButton = page.locator('#send-button');
    await highlight(sendButton);
    
    // Get timestamp element before clicking (it shouldn't exist yet)
    const timestamp = page.locator('.message:last-child .timestamp');
    
    // Click send button
    await sendButton.click();
    
    // Wait for the "Sending..." status to appear and be visible
    await expect(timestamp).toBeVisible({ timeout: 2000 });
    await expect(timestamp).toHaveText('Sending...', { timeout: 2000 });
    await expect(timestamp).toHaveClass(/pending/, { timeout: 2000 });
    await highlight(timestamp);
    
    // Now wait for the POST request to complete
    const response = await page.waitForResponse(
      response => response.url().includes('/messages') && 
                 response.request().method() === 'POST'
    );
    expect(response.ok()).toBeTruthy();
    
    // Wait for the timestamp to update
    await expect(timestamp).not.toHaveText('Sending...', { timeout: 5000 });
    await expect(timestamp).not.toHaveClass(/pending/, { timeout: 5000 });
    await highlight(timestamp);
    
    // Verify timestamp format (e.g., "Jan 17, 21:00")
    const timestampText = await timestamp.textContent();
    expect(timestampText).toMatch(/[A-Z][a-z]{2} \d{1,2}, \d{2}:\d{2}/);
  });

  test('username change functionality', async ({ page }) => {
    // Set up dialog handler before triggering the prompt
    const newUsername = 'TestUser123';
    page.on('dialog', async dialog => {
      expect(dialog.type()).toBe('prompt');
      await dialog.accept(newUsername);
    });
    
    // Trigger the username change action
    await page.click('#change-username-btn');
    
    // Wait for the username display to update
    const usernameDisplay = page.locator('#username-display');
    await expect(usernameDisplay).toHaveText(newUsername, { timeout: 5000 });
  });

  test('message persistence across page reloads', async ({ page }) => {
    // Wait for the message input
    const messageInput = page.locator('#message-input');
    await messageInput.waitFor({ state: 'visible' });
    await highlight(messageInput);

    // Send a test message
    const testMessage = 'This message should persist';
    await messageInput.fill(testMessage);
    
    const sendButton = page.locator('#send-button');
    await highlight(sendButton);
    await sendButton.click();
    
    // Wait for message to appear
    const messageContent = page.locator('.message .content').last();
    await expect(messageContent).toContainText(testMessage, {
      timeout: 5000
    });
    await highlight(messageContent);
    
    // Reload the page
    await page.reload();
    
    // Wait for messages to load and verify message still exists
    const persistedMessage = page.locator('.message .content').last();
    await expect(persistedMessage).toContainText(testMessage, {
      timeout: 5000
    });
    await highlight(persistedMessage);
  });
});

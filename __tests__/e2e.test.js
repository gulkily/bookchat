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
    // Enable console logging
    page.on('console', msg => console.log('Browser log:', msg.text()));
    
    // Wait for the message input to be available
    console.log('Waiting for message input...');
    const messageInput = page.locator('#message-input');
    await messageInput.waitFor({ state: 'visible' });
    await highlight(messageInput);
    console.log('Message input found');
    
    // Type and send a message
    const testMessage = 'Testing message status';
    console.log('Filling message:', testMessage);
    await messageInput.fill(testMessage);
    
    const sendButton = page.locator('#send-button');
    await highlight(sendButton);
    
    // Set up response listener before clicking
    console.log('Setting up POST response listener...');
    const responsePromise = page.waitForResponse(
      response => response.url().includes('/messages') && 
                 response.request().method() === 'POST'
    );
    
    // Click send button
    console.log('Clicking send button...');
    await sendButton.click();
    
    // Wait for the POST request to complete first
    console.log('Waiting for POST response...');
    const response = await responsePromise;
    console.log('Got POST response:', response.status());
    expect(response.ok()).toBeTruthy();
    
    // Now look for the timestamp
    const timestamp = page.locator('.message:last-child .timestamp');
    console.log('Checking timestamp...');
    
    // Get the timestamp text and verify format
    const timestampText = await timestamp.textContent();
    console.log('Found timestamp text:', timestampText);
    expect(timestampText).toBe('Just now');
    
    // Verify it's not an error state
    expect(timestampText).not.toBe('Failed to send');
    expect(timestampText).not.toBe('Unknown time');
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

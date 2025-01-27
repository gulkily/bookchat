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

  test('username persists in messages after page reload', async ({ page }) => {
    // Set up dialog handler for username change
    const testUsername = 'PersistenceTestUser';
    page.on('dialog', async dialog => {
      expect(dialog.type()).toBe('prompt');
      await dialog.accept(testUsername);
    });

    // Wait for username button to be available and verify initial state
    const usernameButton = page.locator('#change-username-btn');
    await usernameButton.waitFor({ state: 'visible' });
    await expect(usernameButton).toContainText('anonymous');
    
    // Click username button to set username
    await usernameButton.click();
    
    // Verify button updates with new username
    await expect(usernameButton).toContainText(testUsername, { timeout: 5000 });
    expect(await usernameButton.textContent()).toMatch(new RegExp(`.*${testUsername}.*`));

    // Send a test message
    const testMessage = 'Testing username persistence';
    const messageInput = page.locator('#message-input');
    await messageInput.waitFor({ state: 'visible' });
    await messageInput.fill(testMessage);
    
    const sendButton = page.locator('#send-button');
    await sendButton.waitFor({ state: 'visible' });
    await sendButton.click();

    // Wait for message to appear and verify username initially
    const messageElement = page.locator('.message').last();
    await messageElement.waitFor({ state: 'visible' });
    await expect(messageElement.locator('.username')).toContainText(testUsername);
    await expect(messageElement.locator('.content')).toContainText(testMessage);

    // Store the message count before reload
    const beforeCount = await page.locator('.message').count();

    // Reload the page
    await page.reload();

    // Wait for username button to be available and verify it shows the persisted username
    await usernameButton.waitFor({ state: 'visible' });
    await expect(usernameButton).toContainText(testUsername, { timeout: 5000 });
    expect(await usernameButton.textContent()).toMatch(new RegExp(`.*${testUsername}.*`));

    // Wait for messages to load by checking that we have at least as many messages as before
    await page.waitForFunction((expectedCount) => {
      const messages = document.querySelectorAll('.message');
      return messages.length >= expectedCount;
    }, beforeCount, { timeout: 5000 });

    // Additional wait to ensure messages are fully loaded
    await page.waitForTimeout(1000);

    // Get the last message and verify its content and username
    const lastMessage = page.locator('.message').last();
    await lastMessage.waitFor({ state: 'visible' });
    
    const content = await lastMessage.locator('.content').textContent();
    const username = await lastMessage.locator('.username').textContent();
    
    expect(content).toBe(testMessage);
    expect(username).toBe(testUsername);
  });

  test('should scroll to bottom on initial load', async ({ page }) => {
    // Load some test messages first to ensure there's enough content to scroll
    for (let i = 0; i < 3; i++) {
      const messageInput = page.locator('#message-input');
      await messageInput.fill(`Test message ${i}`);
      const sendButton = page.locator('#send-button');
      await sendButton.click();
      // Small delay to prevent rate limiting
      await page.waitForTimeout(100);
    }

    // Reload the page
    await page.reload();

    // Wait for messages container to be visible
    const messagesContainer = page.locator('#messages');
    await messagesContainer.waitFor({ state: 'visible' });

    // Get the scroll position and container height
    const scrollPosition = await messagesContainer.evaluate((container) => {
      return {
        scrollTop: container.scrollTop,
        scrollHeight: container.scrollHeight,
        clientHeight: container.clientHeight
      };
    });

    // Verify that we're scrolled to the bottom (with small margin of error)
    expect(scrollPosition.scrollTop + scrollPosition.clientHeight).toBeCloseTo(
      scrollPosition.scrollHeight,
      -1 // Precision of 1 decimal place
    );
  });

  test('should scroll to bottom when new message is sent', async ({ page }) => {
    // Load some initial messages
    for (let i = 0; i < 3; i++) {
      const messageInput = page.locator('#message-input');
      await messageInput.fill(`Initial message ${i}`);
      const sendButton = page.locator('#send-button');
      await sendButton.click();
      // Small delay to prevent rate limiting
      await page.waitForTimeout(100);
    }

    // Send a new message
    const messageInput = page.locator('#message-input');
    await messageInput.fill('New message');
    const sendButton = page.locator('#send-button');
    await sendButton.click();

    // Wait for message to appear
    await page.waitForSelector('.message:has-text("New message")');

    // Wait a bit for scroll animation to complete
    await page.waitForTimeout(100);

    // Get the scroll position and container height
    const messagesContainer = page.locator('#messages');
    const scrollPosition = await messagesContainer.evaluate((container) => {
      return {
        scrollTop: container.scrollTop,
        scrollHeight: container.scrollHeight,
        clientHeight: container.clientHeight
      };
    });

    // Verify that we're scrolled to the bottom (with small margin of error)
    expect(scrollPosition.scrollTop + scrollPosition.clientHeight).toBeCloseTo(
      scrollPosition.scrollHeight,
      -1 // Precision of 1 decimal place
    );
  });
});

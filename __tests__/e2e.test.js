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

    // Click username button to set username
    const usernameButton = page.locator('#change-username-btn');
    await usernameButton.click();

    // Send a test message
    const testMessage = 'Testing username persistence';
    const messageInput = page.locator('#message-input');
    await messageInput.fill(testMessage);
    
    const sendButton = page.locator('#send-button');
    await sendButton.click();

    // Wait for message to appear and verify username initially
    const messageElement = page.locator('.message').last();
    await expect(messageElement.locator('.username')).toContainText(testUsername);

    // Reload the page
    await page.reload();

    // Wait for messages to load after reload
    await page.waitForSelector('.message');

    // Find our test message and verify username is still correct
    const messages = page.locator('.message');
    const count = await messages.count();
    let found = false;
    
    for (let i = 0; i < count; i++) {
      const message = messages.nth(i);
      const content = await message.locator('.content').textContent();
      if (content.includes(testMessage)) {
        const username = await message.locator('.username').textContent();
        expect(username).toContain(testUsername);
        expect(username).not.toContain('anonymous');
        found = true;
        break;
      }
    }
    
    expect(found).toBeTruthy();
  });

  test('should scroll to bottom on initial load', async ({ page }) => {
    // Load some test messages first to ensure there's enough content to scroll
    for (let i = 0; i < 20; i++) {
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
    for (let i = 0; i < 20; i++) {
      const messageInput = page.locator('#message-input');
      await messageInput.fill(`Initial message ${i}`);
      const sendButton = page.locator('#send-button');
      await sendButton.click();
      // Small delay to prevent rate limiting
      await page.waitForTimeout(100);
    }

    // Scroll to the middle of the messages
    const messagesContainer = page.locator('#messages');
    await messagesContainer.evaluate((container) => {
      container.scrollTop = container.scrollHeight / 2;
    });

    // Send a new message
    const messageInput = page.locator('#message-input');
    await messageInput.fill('New message that should trigger scroll');
    const sendButton = page.locator('#send-button');
    await sendButton.click();

    // Wait a moment for the scroll animation
    await page.waitForTimeout(500);

    // Verify that we're scrolled to the bottom
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

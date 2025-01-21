/**
 * Tests for main.js functionality
 */

const { setupMessageInput } = require('./main.js');

describe('formatTimestamp', () => {
    const now = new Date('2025-01-18T18:42:12-05:00');
    const originalDate = global.Date;
    
    beforeAll(() => {
        // Mock Date to return fixed time
        global.Date = class extends Date {
            constructor(...args) {
                if (args.length === 0) {
                    return now;
                }
                return new originalDate(...args);
            }
        };
    });
    
    afterAll(() => {
        global.Date = originalDate;
    });
    
    test('formats just now', () => {
        const timestamp = new Date(now - 30 * 1000).toISOString(); // 30 seconds ago
        expect(formatTimestamp(timestamp)).toBe('Just now');
    });
    
    test('formats minutes ago', () => {
        const timestamp = new Date(now - 5 * 60 * 1000).toISOString(); // 5 minutes ago
        expect(formatTimestamp(timestamp)).toBe('5m ago');
    });
    
    test('formats hours ago', () => {
        const timestamp = new Date(now - 3 * 60 * 60 * 1000).toISOString(); // 3 hours ago
        expect(formatTimestamp(timestamp)).toBe('3h ago');
    });
    
    test('formats days ago', () => {
        const timestamp = new Date(now - 2 * 24 * 60 * 60 * 1000).toISOString(); // 2 days ago
        expect(formatTimestamp(timestamp)).toBe('2d ago');
    });
    
    test('formats older dates', () => {
        const timestamp = new Date('2024-12-25T12:00:00-05:00').toISOString();
        expect(formatTimestamp(timestamp)).toBe('Dec 25, 2024');
    });
    
    test('handles invalid dates', () => {
        expect(formatTimestamp('invalid-date')).toBe('invalid-date');
    });
});

describe('sendMessage', () => {
    beforeEach(() => {
        // Reset DOM
        document.body.innerHTML = `
            <div id="messages-container"></div>
            <div id="messages"></div>
        `;
        
        // Mock fetch
        global.fetch = jest.fn();
    });
    
    test('handles successful message send', async () => {
        const messageData = {
            id: '123',
            content: 'Test message',
            author: 'test_user',
            timestamp: '2025-01-18T18:42:12-05:00'
        };
        
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ success: true, data: messageData })
        });
        
        const result = await sendMessage('Test message');
        expect(result.success).toBe(true);
        expect(result.message).toEqual(messageData);
    });
    
    test('handles server error', async () => {
        global.fetch.mockResolvedValueOnce({
            ok: false,
            status: 500
        });
        
        const result = await sendMessage('Test message');
        expect(result.success).toBe(false);
        expect(result.error).toContain('HTTP error');
    });
    
    test('handles network error', async () => {
        global.fetch.mockRejectedValueOnce(new Error('Network error'));
        
        const result = await sendMessage('Test message');
        expect(result.success).toBe(false);
        expect(result.error).toContain('Network error');
    });
});

describe('Character Counter', () => {
    beforeEach(() => {
        // Set up our document body
        document.body.innerHTML = `
            <form id="js-message-form">
                <textarea id="message-input"></textarea>
                <div id="js-char-counter" class="char-counter">Characters: 0</div>
            </form>
        `;
        
        // Initialize the message input
        setupMessageInput();
    });

    test('updates character count when typing', () => {
        const messageInput = document.getElementById('message-input');
        const charCounter = document.getElementById('js-char-counter');
        
        // Simulate typing text
        messageInput.value = 'Hello';
        messageInput.dispatchEvent(new Event('input'));
        expect(charCounter.textContent).toBe('Characters: 5');
        
        // Add more text
        messageInput.value = 'Hello, world!';
        messageInput.dispatchEvent(new Event('input'));
        expect(charCounter.textContent).toBe('Characters: 13');
        
        // Clear text
        messageInput.value = '';
        messageInput.dispatchEvent(new Event('input'));
        expect(charCounter.textContent).toBe('Characters: 0');
    });
});

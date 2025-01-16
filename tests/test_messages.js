// Using Jest for testing

describe('Message Persistence', () => {
    beforeEach(() => {
        // Clear localStorage/sessionStorage
        localStorage.clear();
        sessionStorage.clear();
        
        // Reset DOM
        document.body.innerHTML = `
            <div id="messages">
                <div id="messages-container"></div>
            </div>
        `;
    });

    test('new messages should be saved to server', async () => {
        const testMessage = {
            content: 'Test message',
            author: 'testuser',
            timestamp: '2025-01-16T11:49:08-05:00'
        };

        // Mock fetch for sending message
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ success: true })
            })
        );

        await sendMessage(testMessage.content);

        // Verify fetch was called with correct data
        expect(fetch).toHaveBeenCalledWith('/messages', expect.objectContaining({
            method: 'POST',
            body: expect.any(String)
        }));

        const sentData = JSON.parse(fetch.mock.calls[0][1].body);
        expect(sentData.content).toBe(testMessage.content);
    });
});

describe('Message Display', () => {
    test('should not display signature in message content', () => {
        const message = {
            content: 'Test message\n-- \nSignature block',
            author: 'testuser',
            timestamp: '2025-01-16T11:49:08-05:00'
        };

        const messageElement = createMessageElement(message);
        const contentDiv = messageElement.querySelector('.content');
        
        expect(contentDiv.textContent).not.toContain('-- ');
        expect(contentDiv.textContent).not.toContain('Signature block');
    });
});

describe('Scroll Behavior', () => {
    beforeEach(() => {
        document.body.innerHTML = `
            <div id="messages">
                <div id="messages-container"></div>
            </div>
        `;
    });

    test('should scroll to bottom when new message is added', () => {
        const messages = document.getElementById('messages');
        messages.scrollTop = 0;
        messages.scrollHeight = 1000;

        // Add new message
        const message = {
            content: 'New message',
            author: 'testuser',
            timestamp: '2025-01-16T11:49:08-05:00'
        };
        
        const messageElement = createMessageElement(message);
        document.getElementById('messages-container').appendChild(messageElement);
        
        // Verify scroll position
        expect(messages.scrollTop).toBe(messages.scrollHeight);
    });

    test('should scroll to bottom on initial load', async () => {
        const messages = document.getElementById('messages');
        messages.scrollTop = 0;
        messages.scrollHeight = 1000;

        // Mock fetch response
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({
                    messages: [{
                        content: 'Test message',
                        author: 'testuser',
                        timestamp: '2025-01-16T11:49:08-05:00'
                    }]
                })
            })
        );

        await loadMessages();
        
        // Verify scroll position
        expect(messages.scrollTop).toBe(messages.scrollHeight);
    });
});

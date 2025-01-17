// Chat Functionality Test Suite

const TEST_TIMESTAMP = '2025-01-17T11:55:44-05:00';

describe('Chat UI Functionality', () => {
    beforeEach(() => {
        // Set up our DOM for testing
        document.body.innerHTML = `
            <div class="message-input-container">
                <form id="js-message-form" class="message-form">
                    <div class="input-wrapper">
                        <textarea id="message-input" maxlength="2000"></textarea>
                        <span id="js-char-counter" class="char-counter">0/2000</span>
                    </div>
                    <button id="send-button" type="submit">Send</button>
                </form>
            </div>
            <div id="messages">
                <div id="messages-container"></div>
            </div>
        `;
        
        // Clear storage
        localStorage.clear();
        sessionStorage.clear();
        
        // Reset fetch mocks
        global.fetch = jest.fn();
    });

    test('character counter updates correctly', () => {
        const input = document.getElementById('message-input');
        const counter = document.getElementById('js-char-counter');
        
        input.value = 'Hello';
        input.dispatchEvent(new Event('input'));
        expect(counter.textContent).toBe('5/2000');
        
        input.value = 'x'.repeat(2000);
        input.dispatchEvent(new Event('input'));
        expect(counter.textContent).toBe('2000/2000');
    });

    test('shift+enter creates new line', () => {
        const input = document.getElementById('message-input');
        const event = new KeyboardEvent('keydown', {
            key: 'Enter',
            shiftKey: true,
            bubbles: true
        });
        
        input.value = 'Line 1';
        input.dispatchEvent(event);
        expect(input.value).toBe('Line 1\\n');
    });

    test('messages display in correct order', async () => {
        const testMessages = [
            { content: 'First', author: 'user1', timestamp: TEST_TIMESTAMP },
            { content: 'Second', author: 'user2', timestamp: new Date(Date.parse(TEST_TIMESTAMP) + 1000).toISOString() },
            { content: 'Third', author: 'user3', timestamp: new Date(Date.parse(TEST_TIMESTAMP) + 2000).toISOString() }
        ];
        
        global.fetch.mockImplementationOnce(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ messages: testMessages })
            })
        );

        await loadMessages();
        
        const messageElements = document.querySelectorAll('.message');
        expect(messageElements.length).toBe(3);
        expect(messageElements[0].querySelector('.content').textContent).toBe('First');
        expect(messageElements[2].querySelector('.content').textContent).toBe('Third');
    });

    test('username display and persistence', () => {
        const testUsername = 'testUser123';
        localStorage.setItem('username', testUsername);
        
        const message = {
            content: 'Test message',
            author: testUsername,
            timestamp: TEST_TIMESTAMP
        };
        
        const messageElement = createMessageElement(message);
        expect(messageElement.querySelector('.author').textContent).toBe(testUsername);
    });

    test('message verification status display', () => {
        const message = {
            content: 'Test message',
            author: 'user',
            timestamp: TEST_TIMESTAMP,
            verified: 'true'
        };
        
        const messageElement = createMessageElement(message);
        expect(messageElement.querySelector('.verified-badge')).not.toBeNull();
    });
});

describe('Error Handling', () => {
    test('handles network errors gracefully', async () => {
        global.fetch.mockImplementationOnce(() =>
            Promise.reject(new Error('Network error'))
        );
        
        await loadMessages();
        expect(document.querySelector('.error-message')).not.toBeNull();
    });
});

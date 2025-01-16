// BookChat JavaScript (2025-01-08T12:20:30-05:00)

// Chat Application
class ChatApp {
    constructor() {
        // Application state
        this.state = {
            messages: [],
            currentUsername: 'anonymous',
            settings: {
                messageVerificationEnabled: false
            },
            pendingMessages: new Map()
        };
        
        // Bind methods
        this.init = this.init.bind(this);
        this.loadMessages = this.loadMessages.bind(this);
        this.sendMessage = this.sendMessage.bind(this);
        this.updateUI = this.updateUI.bind(this);
        this.handleServerResponse = this.handleServerResponse.bind(this);
        this.createMessageElement = this.createMessageElement.bind(this);
        this.handleFormSubmit = this.handleFormSubmit.bind(this);
    }
    
    async init() {
        try {
            console.log('Initializing chat application...');
            
            // Get DOM elements
            this.messagesContainer = document.getElementById('messages-container');
            this.messageForm = document.getElementById('js-message-form');
            this.messageInput = document.getElementById('message-input');
            this.sendButton = document.getElementById('send-button');
            this.outerContainer = document.getElementById('messages');
            
            if (!this.messagesContainer || !this.messageInput || !this.sendButton || !this.outerContainer) {
                throw new Error('Required DOM elements not found');
            }
            
            // Hide no-JS form and show JS form
            const noJsForm = document.getElementById('message-form');
            if (noJsForm) {
                noJsForm.style.display = 'none';
            }
            if (this.messageForm) {
                this.messageForm.style.display = 'flex';
            }
            
            // Add event listeners
            this.messageForm.addEventListener('submit', this.handleFormSubmit);
            
            this.messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.handleFormSubmit(e);
                }
            });
            
            // Load initial messages
            await this.loadMessages();
            
            console.log('Chat application initialized');
            
        } catch (error) {
            console.error('Error initializing chat application:', error);
            this.showError('Failed to initialize chat application');
        }
    }
    
    async loadMessages() {
        try {
            console.log('Attempting to load messages from server');
            
            const response = await fetch('/messages');
            
            // Log raw response details
            console.log('Response status:', response.status);
            console.log('Response headers:', Object.fromEntries(response.headers.entries()));
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Server error response:', errorText);
                throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
            }
            
            let result;
            try {
                result = await response.json();
            } catch (jsonError) {
                console.error('JSON parsing error:', jsonError);
                const responseText = await response.text();
                console.error('Response text:', responseText);
                throw new Error(`Failed to parse JSON: ${jsonError.message}`);
            }
            
            console.log('Parsed server response:', result);
            
            if (!result.success) {
                console.error('Server returned unsuccessful response:', result);
                throw new Error(result.error || 'Failed to load messages');
            }
            
            // Update state
            this.state.messages = result.messages || [];
            this.state.settings.messageVerificationEnabled = result.messageVerificationEnabled || false;
            
            console.log(`Loaded ${this.state.messages.length} messages`);
            
            // Update UI
            await this.updateUI();
            
        } catch (error) {
            console.error('Detailed error loading messages:', error);
            console.error('Error stack:', error.stack);
            this.showError(`Failed to load messages: ${error.message}`);
        }
    }
    
    async sendMessage(content) {
        try {
            // Ensure content is a string and trim it
            content = String(content || '').trim();
            console.log('sendMessage called with content:', content, 'Length:', content.length);
            
            if (!content) {
                console.error('Empty message content in sendMessage');
                return;
            }
            
            // Clear input
            this.messageInput.value = '';
            
            // Create temporary message
            const tempId = 'pending-' + Date.now();
            const tempMessage = {
                id: tempId,
                content: content,
                author: this.state.currentUsername,
                timestamp: new Date().toISOString(),
                verified: false,
                pending: true
            };
            
            // Add to pending messages
            this.state.pendingMessages.set(tempId, tempMessage);
            
            // Add to UI immediately
            const messageElement = this.createMessageElement(tempMessage);
            this.messagesContainer.insertBefore(messageElement, this.messagesContainer.firstChild);
            
            // Send to server
            const response = await fetch('/messages', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: content,
                    username: this.state.currentUsername
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Handle server response
            const result = await response.json();
            if (!result.success) {
                throw new Error(result.error || 'Failed to send message');
            }
            
            // Update message with server data
            await this.handleServerResponse(tempId, result.data);
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.showError('Failed to send message');
            
            // Update UI to show error for the specific message
            const messageElement = document.querySelector(`[data-message-id="${tempId}"]`);
            if (messageElement) {
                messageElement.classList.add('error');
                const timestamp = messageElement.querySelector('.timestamp');
                if (timestamp) {
                    timestamp.textContent = 'Failed to send';
                    timestamp.title = error.message;
                }
            }
        }
    }
    
    async handleServerResponse(tempId, serverMessage) {
        try {
            // Remove from pending messages
            this.state.pendingMessages.delete(tempId);
            
            // Find message element
            const messageElement = document.querySelector(`[data-message-id="${tempId}"]`);
            if (!messageElement) {
                console.error('Message element not found:', tempId);
                return;
            }
            
            // Update message ID
            messageElement.dataset.messageId = serverMessage.id;
            messageElement.classList.remove('pending');
            
            // Update timestamp
            const timestamp = messageElement.querySelector('.timestamp');
            if (timestamp) {
                const messageDate = new Date(serverMessage.timestamp);
                timestamp.textContent = messageDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                timestamp.title = messageDate.toLocaleString();
                timestamp.classList.remove('pending');
            }
            
        } catch (error) {
            console.error('Error handling server response:', error);
            this.showError('Error updating message status');
        }
    }
    
    async handleFormSubmit(event) {
        event.preventDefault();
        const content = this.messageInput.value;
        await this.sendMessage(content);
    }
    
    showError(message) {
        // TODO: Implement better error handling UI
        console.error(message);
    }
    
    async updateUI() {
        try {
            // Clear messages container
            while (this.messagesContainer.firstChild) {
                this.messagesContainer.removeChild(this.messagesContainer.firstChild);
            }
            
            // Preserve original message order from server
            const messages = [...this.state.messages];
            
            // Add all messages
            for (const message of messages) {
                const messageElement = this.createMessageElement(message);
                this.messagesContainer.appendChild(messageElement);
            }
            
        } catch (error) {
            console.error('Error updating UI:', error);
            this.showError('Failed to update UI');
        }
    }
    
    createMessageElement(message) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message';
        if (message.pending) {
            messageElement.classList.add('pending');
        }
        messageElement.dataset.messageId = message.id;
        
        const authorElement = document.createElement('div');
        authorElement.className = 'author';
        authorElement.textContent = message.author;
        messageElement.appendChild(authorElement);
        
        const contentElement = document.createElement('div');
        contentElement.className = 'content';
        contentElement.textContent = message.content;
        messageElement.appendChild(contentElement);
        
        const metaElement = document.createElement('div');
        metaElement.className = 'meta';
        
        const timestampElement = document.createElement('span');
        timestampElement.className = 'timestamp';
        if (message.pending) {
            timestampElement.textContent = 'Sending...';
            timestampElement.classList.add('pending');
        } else {
            try {
                const messageDate = new Date(message.timestamp);
                if (isNaN(messageDate.getTime())) {
                    throw new Error('Invalid date');
                }
                timestampElement.textContent = messageDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                timestampElement.title = messageDate.toLocaleString();
            } catch (error) {
                console.error('Error formatting timestamp:', error);
                timestampElement.textContent = 'Invalid timestamp';
            }
        }
        metaElement.appendChild(timestampElement);
        
        messageElement.appendChild(metaElement);
        
        return messageElement;
    }
}

// Initialize chat application
document.addEventListener('DOMContentLoaded', () => {
    const app = new ChatApp();
    app.init();
});

// BookChat JavaScript (2025-01-08T12:20:30-05:00)

let currentUsername = 'anonymous';
let messageVerificationEnabled = false;

// Initialize everything
document.addEventListener('DOMContentLoaded', async () => {
    await verifyUsername();
    setupMessageInput();
    setupUsernameUI();
    await loadMessages();
});

async function verifyUsername() {
    try {
        // TODO: Add timeout to fetch request to prevent hanging
        // TODO: Add retry logic for failed requests
        const response = await fetch('/verify_username');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        currentUsername = data.username;
        
        localStorage.setItem('username', currentUsername);
        
        const usernameDisplay = document.getElementById('username-display');
        if (usernameDisplay) {
            usernameDisplay.textContent = currentUsername;
        }
        
        return data.status === 'verified';
    } catch (error) {
        console.error('Error verifying username:', error);
        currentUsername = localStorage.getItem('username') || 'anonymous';
        return false;
    }
}

async function loadMessages() {
    try {
        const response = await fetch('/messages');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        let messages = data.messages;
        messageVerificationEnabled = data.messageVerificationEnabled;
        
        // Filter out unverified messages when verification is enabled
        if (messageVerificationEnabled) {
            messages = messages.filter(message => {
                if (typeof message.verified === 'string') {
                    return message.verified.toLowerCase() === 'true';
                }
                return !!message.verified;
            });
        }
        
        const messagesDiv = document.getElementById('messages');
        const messagesContainer = document.getElementById('messages-container');
        messagesContainer.innerHTML = '';
        
        // Sort messages by date (newest at bottom)
        messages.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        messages.reverse();
        
        // Add messages to container
        for (const message of messages) {
            messagesContainer.appendChild(createMessageElement(message));
        }
        
        // Scroll to bottom
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        
        // Update current username
        if (data.currentUsername) {
            currentUsername = data.currentUsername;
            localStorage.setItem('username', currentUsername);
            const usernameDisplay = document.getElementById('username-display');
            if (usernameDisplay) {
                usernameDisplay.textContent = currentUsername;
            }
        }
        
        // Update verification status
        updateGlobalVerificationStatus();
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

function createMessageElement(message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    messageDiv.dataset.messageId = message.id || '';

    // Create message header
    const header = document.createElement('div');
    header.className = 'message-header';
    
    const headerLeft = document.createElement('div');
    headerLeft.className = 'header-left';

    // Add author
    const author = document.createElement('span');
    author.className = 'author';
    author.textContent = message.author || 'anonymous';
    headerLeft.appendChild(author);

    // Add timestamp
    const timestamp = document.createElement('span');
    timestamp.className = 'timestamp';
    if (message.pending) {
        timestamp.textContent = 'Sending...';
        timestamp.className += ' pending';
    } else {
        try {
            // Use either timestamp or createdAt field
            const messageDate = new Date(message.timestamp || message.createdAt);
            const options = { 
                month: 'short', 
                day: 'numeric',
                hour: '2-digit', 
                minute: '2-digit',
                hour12: false 
            };
            timestamp.textContent = messageDate.toLocaleString([], options);
            timestamp.title = messageDate.toLocaleString();
        } catch (error) {
            console.error('Error formatting date:', error);
            timestamp.textContent = 'Unknown time';
        }
    }
    headerLeft.appendChild(timestamp);
    header.appendChild(headerLeft);
    messageDiv.appendChild(header);

    // Create message content
    const content = document.createElement('div');
    content.className = 'content';
    
    // Strip signature block from content
    let messageContent = message.content;
    const signatureIndex = messageContent.indexOf('\n-- \n');
    if (signatureIndex !== -1) {
        messageContent = messageContent.substring(0, signatureIndex);
    }
    
    content.textContent = messageContent;
    messageDiv.appendChild(content);

    return messageDiv;
}

async function sendMessage(content, type = 'message') {
    let tempMessage;  // Declare outside try block so catch block can access it
    try {
        // Ensure content is a string and trim it
        content = String(content || '').trim();
        console.log('sendMessage called with content:', content, 'Length:', content.length);
        
        if (!content) {
            console.error('Empty message content in sendMessage');
            return;
        }

        // Create a temporary message object
        tempMessage = {
            content: content,
            author: currentUsername,
            timestamp: new Date().toISOString(),
            id: 'pending-' + Date.now(),
            verified: false,
            pending: true
        };
        console.log('Created temporary message:', tempMessage);

        // Immediately add message to UI
        const messagesContainer = document.getElementById('messages-container');
        messagesContainer.appendChild(createMessageElement(tempMessage));
        
        // Scroll to bottom
        const messagesDiv = document.getElementById('messages');
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

        // Add a small delay to ensure the "Sending..." status is visible
        await new Promise(resolve => setTimeout(resolve, 100));

        // Create request body and log it
        const requestBody = {
            content: content,
            username: currentUsername
        };
        console.log('Sending request:', requestBody);
        
        const response = await fetch('/messages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Server error response:', errorText);
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }
        
        const result = await response.json();
        console.log('Server response:', result);
        
        // Update the pending message with the real data
        const pendingMessage = document.querySelector(`[data-message-id="${tempMessage.id}"]`);
        console.log('Found pending message:', pendingMessage ? 'yes' : 'no');
        
        if (pendingMessage && result.data) {
            console.log('Updating message with server data:', result.data);
            
            // Update message ID
            pendingMessage.dataset.messageId = result.data.id || tempMessage.id;
            
            // Update the timestamp
            const timestamp = pendingMessage.querySelector('.timestamp');
            console.log('Found timestamp element:', timestamp ? 'yes' : 'no');
            console.log('Server timestamp:', result.data.timestamp);
            
            if (timestamp) {
                try {
                    const messageDate = new Date(result.data.timestamp);
                    console.log('Parsed message date:', messageDate);
                    
                    const options = { 
                        month: 'short', 
                        day: 'numeric',
                        hour: '2-digit', 
                        minute: '2-digit',
                        hour12: false 
                    };
                    const formattedDate = messageDate.toLocaleString([], options);
                    console.log('Formatted date:', formattedDate);
                    
                    // Add a small delay before updating the timestamp
                    await new Promise(resolve => setTimeout(resolve, 100));
                    
                    // Remove the pending class first
                    timestamp.classList.remove('pending');
                    // Then update the text content
                    timestamp.textContent = formattedDate;
                    timestamp.title = messageDate.toLocaleString();
                    console.log('Updated timestamp element:', {
                        text: timestamp.textContent,
                        classList: timestamp.className
                    });
                } catch (error) {
                    console.error('Error updating timestamp:', error);
                    timestamp.textContent = 'Unknown time';
                    timestamp.title = 'Error parsing date';
                }
            } else {
                console.warn('Missing timestamp element');
            }
        } else {
            console.warn('Could not update message:', {
                hasPendingMessage: !!pendingMessage,
                hasResultData: !!result.data
            });
        }
        
        return result;
    } catch (error) {
        console.error('Error sending message:', error);
        // Update pending message to show error
        const pendingMessage = document.querySelector(`[data-message-id="${tempMessage?.id}"]`);
        if (pendingMessage) {
            const timestamp = pendingMessage.querySelector('.timestamp');
            if (timestamp) {
                timestamp.className = 'timestamp error';
                timestamp.textContent = 'Failed to send';
                timestamp.title = 'Message failed to send';
            }
        }
        throw error;
    }
}

async function changeUsername(newUsername) {
    try {
        // Validate username format
        if (!USERNAME_REGEX.test(newUsername)) {
            alert('Username must be 3-20 characters long and contain only letters, numbers, and underscores.');
            return false;
        }

        // Call the username change endpoint
        const response = await fetch('/change_username', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                old_username: currentUsername,
                new_username: newUsername
            })
        });

        if (!response.ok) {
            const error = await response.text();
            alert(error);
            return false;
        }

        // Update local state
        currentUsername = newUsername;
        localStorage.setItem('username', newUsername);
        
        // Update display
        const usernameDisplay = document.getElementById('username-display');
        if (usernameDisplay) {
            usernameDisplay.textContent = currentUsername;
        }
        
        return true;
    } catch (error) {
        console.error('Error changing username:', error);
        alert('Failed to change username. Please try again.');
        return false;
    }
}

// Add username change UI
function setupUsernameUI() {
    // Update username display
    const usernameDisplay = document.getElementById('username-display');
    if (usernameDisplay) {
        usernameDisplay.textContent = currentUsername;
    }

    // Set up change username button click handler
    const changeButton = document.getElementById('change-username-btn');
    if (changeButton) {
        changeButton.onclick = async () => {
            const newUsername = prompt('Enter new username:');
            if (newUsername) {
                const success = await changeUsername(newUsername);
                if (!success) {
                    alert('Failed to change username. Please try a different username.');
                }
            }
        };
    }
}

function setupMessageInput() {
    // Hide no-JS form and show JS form
    const noJsForm = document.getElementById('message-form');
    const jsForm = document.getElementById('js-message-form');
    if (noJsForm && jsForm) {
        noJsForm.style.display = 'none';
        jsForm.style.display = 'flex';
    }
    
    const messageForm = document.getElementById('js-message-form');
    const messageInput = document.getElementById('message-input');
    
    if (messageForm && messageInput) {
        // Function to validate and send message
        const validateAndSendMessage = async (content) => {
            // Ensure content is a string and properly trimmed
            content = String(content || '').trim();
            
            if (!content) {
                console.log('Empty content detected, preventing submission');
                messageInput.classList.add('error');
                setTimeout(() => messageInput.classList.remove('error'), 2000);
                return false;
            }

            // Clear input immediately
            const originalContent = content;
            messageInput.value = '';
            
            try {
                await sendMessage(originalContent);
                return true;
            } catch (error) {
                console.error('Failed to send message:', error);
                messageInput.value = originalContent;
                messageInput.classList.add('error');
                setTimeout(() => messageInput.classList.remove('error'), 2000);
                
                // Show error message to user
                const errorDiv = document.createElement('div');
                errorDiv.className = 'error-message';
                errorDiv.textContent = 'Failed to send message. Please try again.';
                messageForm.appendChild(errorDiv);
                setTimeout(() => errorDiv.remove(), 3000);
                return false;
            }
        };

        // Handle form submit (for button click)
        messageForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await validateAndSendMessage(messageInput.value);
        });
        
        // Handle Enter key press (Shift+Enter for new line)
        messageInput.addEventListener('keydown', async (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                await validateAndSendMessage(messageInput.value);
            }
        });
    }
}

// Update global verification status based on all messages
function updateGlobalVerificationStatus() {
    // Only update if verification is enabled
    if (!messageVerificationEnabled) {
        const globalStatus = document.getElementById('global-verification-status');
        if (globalStatus) {
            globalStatus.style.display = 'none';
        }
        return;
    }
    
    const messages = document.querySelectorAll('.message');
    const globalStatus = document.getElementById('global-verification-status');
    
    if (!messages.length || !globalStatus) return;
    
    let allVerified = true;
    let anyVerified = false;
    
    messages.forEach(message => {
        const status = message.querySelector('.verification-status');
        if (status && status.classList.contains('verified')) {
            anyVerified = true;
        } else {
            allVerified = false;
        }
    });
    
    globalStatus.className = 'global-verification-status';
    
    if (allVerified) {
        globalStatus.classList.add('verified');
        globalStatus.textContent = 'Chat Verification Status: All Messages Verified';
    } else if (anyVerified) {
        globalStatus.classList.add('partial');
        globalStatus.textContent = 'Chat Verification Status: Some Messages Verified';
    } else {
        globalStatus.classList.add('unverified');
        globalStatus.textContent = 'Chat Verification Status: No Messages Verified';
    }
}

// Username validation regex - only allow alphanumeric and underscore, 3-20 chars
const USERNAME_REGEX = /^[a-zA-Z0-9_]{3,20}$/;

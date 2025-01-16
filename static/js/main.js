// BookChat JavaScript (2025-01-08T12:20:30-05:00)

let currentUsername = 'anonymous';
let messageVerificationEnabled = false;

// Initialize everything
document.addEventListener('DOMContentLoaded', async () => {
    await initializeUsername();
    setupMessageInput();
    setupUsernameUI();
    await loadMessages();
});

async function initializeUsername() {
    try {
        // Get username from cookie or default to anonymous
        currentUsername = document.cookie.split('; ').find(row => row.startsWith('username='))?.split('=')[1] || 'anonymous';
        
        // Update all UI elements that show username
        updateUsernameDisplay(currentUsername);
        
        return true;
    } catch (error) {
        console.error('Error initializing username:', error);
        currentUsername = 'anonymous';
        updateUsernameDisplay(currentUsername);
        return false;
    }
}

function updateUsernameDisplay(username) {
    // Update username display in header
    const usernameDisplay = document.getElementById('username-display');
    if (usernameDisplay) {
        usernameDisplay.textContent = username;
    }
    
    // Update current-username span for no-js version
    const currentUsernameSpan = document.querySelector('.current-username');
    if (currentUsernameSpan) {
        currentUsernameSpan.textContent = `(Current: ${username})`;
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
            messages = messages.filter(message => message.verified && message.verified.toLowerCase() === 'true');
        }
        
        const messagesDiv = document.getElementById('messages');
        const messagesContainer = document.getElementById('messages-container');
        messagesContainer.innerHTML = '';
        
        // Sort messages by date (newest at bottom)
        messages.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
        messages.reverse();
        
        // Add messages to container
        for (const message of messages) {
            messagesContainer.appendChild(createMessageElement(message));
        }
        
        // Scroll to bottom
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        
        // Update username if it changed server-side
        if (data.currentUsername && data.currentUsername !== currentUsername) {
            currentUsername = data.currentUsername;
            updateUsernameDisplay(currentUsername);
        }
        
        // Update current username
        if (data.currentUsername) {
            currentUsername = data.currentUsername;
            const usernameDisplay = document.getElementById('current-username');
            if (usernameDisplay) {
                usernameDisplay.textContent = `Current username: ${currentUsername}`;
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
    messageDiv.dataset.messageId = message.id;
    
    // Create message header for author and timestamp
    const messageHeader = document.createElement('div');
    messageHeader.className = 'message-header';
    
    // Create left section for author and verification status
    const leftSection = document.createElement('div');
    leftSection.className = 'header-left';
    
    // Add author name
    const authorSpan = document.createElement('span');
    authorSpan.className = 'author';
    authorSpan.textContent = message.author || 'anonymous';
    leftSection.appendChild(authorSpan);
    
    // Add verification status if enabled
    if (messageVerificationEnabled) {
        const verifiedSpan = document.createElement('span');
        verifiedSpan.className = `verification-status ${message.verified && message.verified.toLowerCase() === 'true' ? 'verified' : 'unverified'}`;
        verifiedSpan.title = message.verified && message.verified.toLowerCase() === 'true' ? 'Message signature verified' : 'Message not verified';
        verifiedSpan.innerHTML = message.verified && message.verified.toLowerCase() === 'true' ? '&#10003;' : '&#33;';
        leftSection.appendChild(verifiedSpan);
    }
    
    // Create right section for timestamp and commit hash
    const rightSection = document.createElement('div');
    rightSection.className = 'header-right';
    
    // Add timestamp
    const timestampSpan = document.createElement('span');
    timestampSpan.className = 'timestamp';
    if (message.pending) {
        timestampSpan.className += ' pending';
        timestampSpan.textContent = 'Sending...';
        timestampSpan.title = 'Message is being sent';
    } else {
        try {
            // Handle ISO 8601 dates with timezone offset
            const date = message.createdAt;
            if (date && date !== "No timestamp") {
                // Try to parse the date, handling both ISO 8601 and other formats
                try {
                    // First try to parse as ISO 8601
                    const messageDate = new Date(date);
                    if (!isNaN(messageDate.getTime())) {
                        const options = { hour: '2-digit', minute: '2-digit' };
                        timestampSpan.textContent = messageDate.toLocaleTimeString([], options);
                        timestampSpan.title = messageDate.toLocaleString();
                    } else {
                        // If not a valid date, just display the raw string
                        timestampSpan.textContent = date;
                        timestampSpan.title = date;
                    }
                } catch (error) {
                    console.error('Error parsing date:', error, date);
                    timestampSpan.textContent = date;
                    timestampSpan.title = 'Error parsing date';
                }
            } else {
                timestampSpan.textContent = date || 'Unknown time';
                timestampSpan.title = date || 'Unknown time';
            }
        } catch (error) {
            console.error('Error formatting date:', error, message.createdAt);
            timestampSpan.textContent = message.createdAt || 'Invalid date';
            timestampSpan.title = 'Error parsing date';
        }
    }
    rightSection.appendChild(timestampSpan);
    
    messageHeader.appendChild(leftSection);
    messageHeader.appendChild(rightSection);
    messageDiv.appendChild(messageHeader);
    
    // Add message content
    const content = document.createElement('div');
    content.className = 'content';
    content.textContent = message.content || 'No message content';
    messageDiv.appendChild(content);
    
    // Add reactions section
    const reactionsDiv = document.createElement('div');
    reactionsDiv.className = 'message-reactions';
    
    // Add existing reactions
    const reactions = message.reactions || {};
    for (const [emoji, users] of Object.entries(reactions)) {
        const reactionButton = createReactionButton(emoji, users, message.id);
        reactionsDiv.appendChild(reactionButton);
    }
    
    // Add "Add Reaction" button
    const addReactionButton = document.createElement('button');
    addReactionButton.className = 'add-reaction-button';
    addReactionButton.innerHTML = '&#128512;'; // Smiley face emoji
    addReactionButton.title = 'Add reaction';
    addReactionButton.onclick = (e) => {
        e.stopPropagation();
        showReactionPicker(message.id, reactionsDiv, addReactionButton);
    };
    reactionsDiv.appendChild(addReactionButton);
    
    messageDiv.appendChild(reactionsDiv);
    
    return messageDiv;
}

function createReactionButton(emoji, users, messageId) {
    const button = document.createElement('button');
    button.className = 'reaction-button';
    if (users.includes(currentUsername)) {
        button.classList.add('active');
    }
    
    const emojiSpan = document.createElement('span');
    emojiSpan.textContent = emoji;
    button.appendChild(emojiSpan);
    
    const countSpan = document.createElement('span');
    countSpan.className = 'reaction-count';
    countSpan.textContent = users.length;
    button.appendChild(countSpan);
    
    button.onclick = async (e) => {
        e.stopPropagation();
        const action = users.includes(currentUsername) ? 'remove' : 'add';
        await toggleReaction(messageId, emoji, action);
    };
    
    return button;
}

function showReactionPicker(messageId, reactionsDiv, addButton) {
    // Remove existing picker if any
    const existingPicker = document.querySelector('.reaction-picker');
    if (existingPicker) {
        existingPicker.remove();
    }
    
    const picker = document.createElement('div');
    picker.className = 'reaction-picker';
    
    // Add reaction options
    const reactions = ['👍', '❤️', '😄'];
    for (const emoji of reactions) {
        const button = document.createElement('button');
        button.textContent = emoji;
        button.onclick = async () => {
            await toggleReaction(messageId, emoji, 'add');
            picker.remove();
        };
        picker.appendChild(button);
    }
    
    // Position picker near the add button
    const rect = addButton.getBoundingClientRect();
    picker.style.position = 'absolute';
    picker.style.left = `${rect.left}px`;
    picker.style.top = `${rect.bottom + 4}px`;
    
    document.body.appendChild(picker);
    
    // Close picker when clicking outside
    const closeHandler = (e) => {
        if (!picker.contains(e.target) && e.target !== addButton) {
            picker.remove();
            document.removeEventListener('click', closeHandler);
        }
    };
    document.addEventListener('click', closeHandler);
}

async function toggleReaction(messageId, reaction, action) {
    try {
        const response = await fetch('/reaction', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                messageId,
                reaction,
                action
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Reload messages to show updated reactions
        await loadMessages();
    } catch (error) {
        console.error('Error toggling reaction:', error);
    }
}

async function sendMessage(content, type = 'message') {
    try {
        // Ensure content is a string and trim it
        content = String(content || '').trim();
        console.log('sendMessage called with content:', content, 'Length:', content.length);
        console.log('Content type:', typeof content);
        
        if (!content) {
            console.error('Empty message content in sendMessage');
            return;
        }

        // Create a temporary message object
        const tempMessage = {
            content: content,
            author: currentUsername,
            createdAt: new Date().toISOString(),
            id: 'pending-' + Date.now(),
            verified: false,
            pending: true
        };

        // Immediately add message to UI
        const messagesContainer = document.getElementById('messages-container');
        messagesContainer.appendChild(createMessageElement(tempMessage));
        
        // Scroll to bottom
        const messagesDiv = document.getElementById('messages');
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

        // Create request body and log it
        const requestBody = {
            content: content,
            username: currentUsername
        };
        console.log('Request body before stringify:', requestBody);
        const stringifiedBody = JSON.stringify(requestBody);
        console.log('Stringified request body:', stringifiedBody);
        
        const response = await fetch('/messages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: stringifiedBody
        });
        
        // Log response status
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Server error response:', errorText);
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }
        
        const result = await response.json();
        
        // Update the pending message with the real data
        const pendingMessage = document.querySelector(`[data-message-id="${tempMessage.id}"]`);
        if (pendingMessage && result.data) {
            // Update message ID and data
            pendingMessage.dataset.messageId = result.data.id || tempMessage.id;
            
            // Update the timestamp
            const timestamp = pendingMessage.querySelector('.timestamp');
            if (timestamp && result.data.createdAt) {
                try {
                    const messageDate = new Date(result.data.createdAt);
                    const options = { hour: '2-digit', minute: '2-digit' };
                    timestamp.textContent = messageDate.toLocaleTimeString([], options);
                    timestamp.title = messageDate.toLocaleString();
                    timestamp.classList.remove('pending');
                } catch (error) {
                    console.error('Error updating timestamp:', error);
                    timestamp.textContent = 'Unknown time';
                    timestamp.title = 'Error parsing date';
                }
            }
            
            // Add verification status if needed
            if (messageVerificationEnabled) {
                const leftSection = pendingMessage.querySelector('.header-left');
                const verificationStatus = document.createElement('span');
                verificationStatus.className = 'verification-status';
                
                if (result.data.verified && result.data.verified.toLowerCase() === 'true') {
                    verificationStatus.className += ' verified';
                    verificationStatus.title = 'Message verified';
                    verificationStatus.innerHTML = '&#10003;';
                } else {
                    verificationStatus.className += ' unverified';
                    verificationStatus.title = 'Message not verified';
                    verificationStatus.innerHTML = '&#33;';
                }
                leftSection.insertBefore(verificationStatus, leftSection.firstChild);
            }
        }
        
        return result;
    } catch (error) {
        console.error('Error sending message:', error);
        // Update pending message to show error
        const pendingMessage = document.querySelector(`[data-message-id="${tempMessage.id}"]`);
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
            const errorData = await response.json();
            alert(errorData.error?.message || 'Failed to change username. Please try again.');
            return false;
        }

        // Update local state
        currentUsername = newUsername;
        
        // Update all UI elements
        updateUsernameDisplay(newUsername);
        
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
                } else {
                    // Update display after successful change
                    if (usernameDisplay) {
                        usernameDisplay.textContent = newUsername;
                    }
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
    const charCounter = document.getElementById('js-char-counter');
    
    if (messageForm && messageInput) {
        const MAX_CHARS = 2000;
        
        // Update character count on input
        const updateCharCount = () => {
            const count = messageInput.value.length;
            charCounter.textContent = `${count}/${MAX_CHARS}`;
            
            // Reset classes
            charCounter.classList.remove('warning', 'danger');
            
            // Add appropriate class based on count
            if (count > MAX_CHARS * 0.9) { // Over 90%
                charCounter.classList.add('danger');
            } else if (count > MAX_CHARS * 0.75) { // Over 75%
                charCounter.classList.add('warning');
            }
        };

        // Add input event listener for live character counting
        messageInput.addEventListener('input', updateCharCount);
        
        // Function to validate and send message
        const validateAndSendMessage = async (content) => {
            if (content.length === 0) {
                console.log('Empty content detected, preventing submission');
                messageInput.classList.add('error');
                setTimeout(() => messageInput.classList.remove('error'), 2000);
                return false;
            }
            
            if (content.length > MAX_CHARS) {
                console.log('Content too long, preventing submission');
                messageInput.classList.add('error');
                setTimeout(() => messageInput.classList.remove('error'), 2000);
                return false;
            }

            // Clear input immediately
            const originalContent = content;
            messageInput.value = '';
            
            try {
                await sendMessage(originalContent);
                updateCharCount();
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

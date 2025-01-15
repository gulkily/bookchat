// BookChat JavaScript (2025-01-08T12:20:30-05:00)

// HTML escaping function
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

let currentUsername = 'anonymous';
let messageVerificationEnabled = false;

// Initialize everything
document.addEventListener('DOMContentLoaded', async () => {
    await verifyUsername();
    setupMessageInput();
    setupUsernameUI();
    await loadMessages();
    await loadPinnedMessages();
});

async function verifyUsername() {
    try {
        const response = await fetch('/verify_username');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        currentUsername = data.username;
        
        // Update localStorage with the verified username
        localStorage.setItem('username', currentUsername);
        
        // Update UI if it exists
        const usernameDisplay = document.getElementById('current-username');
        if (usernameDisplay) {
            usernameDisplay.textContent = `Current username: ${currentUsername}`;
        }
        
        return data.status === 'verified';
    } catch (error) {
        console.error('Error verifying username:', error);
        // Fall back to stored username or anonymous
        currentUsername = localStorage.getItem('username') || 'anonymous';
        return false;
    }
}

async function loadMessages() {
    try {
        const response = await fetch('/api/messages');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        const messages = data.messages || [];
        currentUsername = data.currentUsername || 'anonymous';
        messageVerificationEnabled = data.messageVerificationEnabled || false;
        
        const messagesContainer = document.getElementById('messages-container');
        messagesContainer.innerHTML = '';
        
        // Add messages to container
        messages.forEach(message => {
            messagesContainer.appendChild(createMessageElement(message));
        });
        
        // Scroll to bottom
        const messagesDiv = document.getElementById('messages');
        if (messagesDiv) {
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        // Update username display
        const usernameDisplay = document.getElementById('current-username');
        if (usernameDisplay) {
            usernameDisplay.textContent = `Current username: ${currentUsername}`;
        }
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
    authorSpan.textContent = escapeHtml(message.author || 'anonymous');
    leftSection.appendChild(authorSpan);
    
    // Add verification status if enabled
    if (messageVerificationEnabled) {
        const verifiedSpan = document.createElement('span');
        verifiedSpan.className = `verification-status ${message.verified && message.verified.toLowerCase() === 'true' ? 'verified' : 'unverified'}`;
        verifiedSpan.title = message.verified && message.verified.toLowerCase() === 'true' ? 'Message signature verified' : 'Message not verified';
        verifiedSpan.textContent = message.verified && message.verified.toLowerCase() === 'true' ? '&#10003;' : '&#33;';
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
        const messageDate = new Date(message.createdAt);
        timestampSpan.textContent = messageDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        timestampSpan.title = messageDate.toLocaleString();
    }
    rightSection.appendChild(timestampSpan);
    
    // Add commit hash with GitHub link if available
    if (message.commit_hash && message.repo_name) {
        const commitSpan = document.createElement('span');
        commitSpan.className = 'commit-hash';
        const commitLink = document.createElement('a');
        commitLink.href = `https://github.com/${message.repo_name}/commit/${message.commit_hash}`;
        commitLink.target = '_blank';
        commitLink.textContent = message.commit_hash;
        commitLink.title = 'View commit on GitHub';
        commitSpan.appendChild(commitLink);
        rightSection.appendChild(commitSpan);
    }
    
    // Add source file link if available and verification is enabled and not pending
    if (message.file && messageVerificationEnabled && !message.pending) {
        const sourceLink = document.createElement('a');
        sourceLink.className = 'source-link';
        sourceLink.href = `/messages/${message.file.split('/').pop()}`; // Get just the filename
        sourceLink.textContent = '&#128273;';
        sourceLink.title = 'View message source file';
        sourceLink.target = '_blank'; // Open in new tab
        rightSection.appendChild(sourceLink);
    }
    
    messageHeader.appendChild(leftSection);
    messageHeader.appendChild(rightSection);
    messageDiv.appendChild(messageHeader);
    
    // Add message content
    const content = document.createElement('div');
    content.className = 'content';
    content.textContent = escapeHtml(message.content);
    messageDiv.appendChild(content);
    
    return messageDiv;
}

async function sendMessage(content, type = 'message') {
    try {
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
        const messageElement = createMessageElement(tempMessage);
        messagesContainer.appendChild(messageElement);
        
        // Scroll to bottom
        const messagesDiv = document.getElementById('messages');
        if (messagesDiv) {
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        // Send to server
        const response = await fetch('/api/messages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                content: content,
                type: type
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        // Remove the temporary message
        messageElement.remove();
        
        // Add the real message from the server
        messagesContainer.appendChild(createMessageElement(result));
        
        // Scroll to bottom again
        if (messagesDiv) {
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        return result;
    } catch (error) {
        console.error('Error sending message:', error);
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
            usernameDisplay.textContent = newUsername;
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
    
    if (messageForm && messageInput) {
        // Handle form submit (for button click)
        messageForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const content = messageInput.value.trim();
            if (content) {
                // Clear input immediately
                messageInput.value = '';
                
                try {
                    await sendMessage(content);
                } catch (error) {
                    console.error('Failed to send message:', error);
                    alert('Failed to send message. Please try again.');
                    // Restore the message if sending failed
                    messageInput.value = content;
                }
            }
        });
        
        // Handle Enter key press (Shift+Enter for new line)
        messageInput.addEventListener('keydown', async (e) => {
            if (e.key === 'Enter') {
                if (e.shiftKey) {
                    // Allow Shift+Enter to create a new line
                    return;
                }
                e.preventDefault();
                const content = messageInput.value.trim();
                if (content) {
                    // Clear input immediately
                    messageInput.value = '';
                    
                    try {
                        await sendMessage(content);
                    } catch (error) {
                        console.error('Failed to send message:', error);
                        alert('Failed to send message. Please try again.');
                        // Restore the message if sending failed
                        messageInput.value = content;
                    }
                }
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

// Pin/unpin message
async function toggleMessagePin(messageId, isPinned) {
    try {
        const response = await fetch(`/api/messages/${messageId}/pin`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: isPinned ? 'unpin' : 'pin'
            })
        });

        if (response.ok) {
            // Refresh messages to show updated pin status
            await loadMessages();
            await loadPinnedMessages();
        } else {
            console.error('Failed to toggle message pin');
        }
    } catch (error) {
        console.error('Error toggling message pin:', error);
    }
}

async function loadPinnedMessages() {
    try {
        const response = await fetch('/api/messages/pinned');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        const pinnedMessages = data.messages || [];
        
        const pinnedSection = document.getElementById('pinned-messages');
        if (!pinnedSection) {
            console.warn('Pinned messages section not found in DOM');
            return;
        }
        
        pinnedSection.innerHTML = '';
        
        if (pinnedMessages.length > 0) {
            pinnedSection.style.display = 'block';
            const header = document.createElement('h3');
            header.textContent = 'Pinned Messages';
            pinnedSection.appendChild(header);
            
            pinnedMessages.forEach(message => {
                const messageElement = createMessageElement(message, true);
                pinnedSection.appendChild(messageElement);
            });
        } else {
            pinnedSection.style.display = 'none';
        }
    } catch (error) {
        console.error('Error loading pinned messages:', error);
    }
}

// Create message element
function createMessageElement(message, isPinned = false) {
    const div = document.createElement('div');
    div.className = `message ${message.is_pinned ? 'pinned' : ''}`;
    div.setAttribute('data-message-id', message.id);

    // Add pin/unpin button
    const pinButton = document.createElement('button');
    pinButton.className = 'pin-button';
    pinButton.innerHTML = message.is_pinned ? '&#128204;' : '&#128203;';
    pinButton.title = message.is_pinned ? 'Unpin message' : 'Pin message';
    pinButton.onclick = (e) => {
        e.preventDefault();
        toggleMessagePin(message.id, message.is_pinned);
    };

    // Add message content
    const content = document.createElement('div');
    content.className = 'message-content';
    content.innerHTML = `
        <span class="username">${escapeHtml(message.user)}</span>
        <span class="timestamp">${new Date(message.timestamp).toLocaleString()}</span>
        <div class="text">${escapeHtml(message.content)}</div>
    `;

    if (message.is_pinned) {
        const pinnedBy = document.createElement('div');
        pinnedBy.className = 'pinned-by';
        pinnedBy.textContent = `Pinned by ${message.pinned_by}`;
        content.appendChild(pinnedBy);
    }

    div.appendChild(pinButton);
    div.appendChild(content);
    return div;
}

// Initialize chat
async function initChat() {
    await loadMessages();
    await loadPinnedMessages();
    setupMessageInput();
    setupKeyboardShortcuts();
}

// Setup keyboard shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + P to pin/unpin selected message
        if ((e.ctrlKey || e.metaKey) && e.key === 'p' && !e.shiftKey) {
            e.preventDefault();
            const selectedMessage = document.querySelector('.message.selected');
            if (selectedMessage) {
                const messageId = selectedMessage.getAttribute('data-message-id');
                const isPinned = selectedMessage.classList.contains('pinned');
                toggleMessagePin(messageId, isPinned);
            }
        }
    });
}

// Username validation regex - only allow alphanumeric and underscore, 3-20 chars
const USERNAME_REGEX = /^[a-zA-Z0-9_]{3,20}$/;

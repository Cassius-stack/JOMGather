/**
 * JOMGather Chat System with Socket.IO
 * Real-time messaging with SQLite persistence
 */

// ============================================
// SOCKET.IO CONNECTION
// ============================================

// Connect to the Socket.IO server
const socket = io();

// Get user ID from URL parameter (for testing: ?user=1 or ?user=2)
// In production, this would come from the session
const urlParams = new URLSearchParams(window.location.search);
const CURRENT_USER_ID = parseInt(urlParams.get('user')) || 1;

// Default contact based on who we're logged in as
// User 1 (Jeremy) defaults to chatting with User 2 (Mdm Lim)
// User 2 (Mdm Lim) defaults to chatting with User 1 (Jeremy)
let currentContactId = CURRENT_USER_ID === 1 ? 2 : 1;

// Track unread message counts per contact
const unreadCounts = {};

// DOM Elements
const contactList = document.getElementById('contact-list');
const chatContactName = document.getElementById('chat-contact-name');
const chatContactStatus = document.getElementById('chat-contact-status');
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');

// ============================================
// SOCKET.IO EVENT LISTENERS
// ============================================

/**
 * When we connect to the server
 */
socket.on('connect', () => {
    console.log('[Socket.IO] Connected to server as user', CURRENT_USER_ID);
    // Register ourselves with the server
    socket.emit('register_user', { user_id: CURRENT_USER_ID });
    // Join the current chat room
    socket.emit('join_chat', { user_id: CURRENT_USER_ID, contact_id: currentContactId });
});
// Track processed message IDs to avoid duplicates
const processedMessageIds = new Set();

/**
 * When we receive a new message (real-time!)
 * This is the magic - messages appear instantly without refresh
 */
socket.on('new_message', (data) => {
    console.log('[Socket.IO] New message received:', data);

    // Prevent duplicate processing (message may arrive from both chat room and personal room)
    if (processedMessageIds.has(data.id)) {
        console.log('[Socket.IO] Skipping duplicate message:', data.id);
        return;
    }
    processedMessageIds.add(data.id);

    // Determine if this is a sent or received message for us
    const messageType = data.sender_id === CURRENT_USER_ID ? 'sent' : 'received';
    const otherUserId = data.sender_id === CURRENT_USER_ID ? data.receiver_id : data.sender_id;

    // Only add to chat if it's for the current conversation
    if (otherUserId === currentContactId) {
        appendMessage({
            id: data.id,
            type: messageType,
            text: data.text
        });
    } else if (messageType === 'received') {
        // Message from a different contact - increment unread count
        unreadCounts[otherUserId] = (unreadCounts[otherUserId] || 0) + 1;
        updateUnreadBadge(otherUserId);
    }

    // Always update the contact preview
    updateContactPreview(otherUserId, data.text, messageType);
});

/**
 * When another user is typing
 */
socket.on('user_typing', (data) => {
    console.log('[Socket.IO] User typing:', data);
    if (data.user_id === currentContactId) {
        if (data.is_typing) {
            showTypingIndicator();
        } else {
            hideTypingIndicator();
        }
    }
});

/**
 * When a user comes online
 */
socket.on('user_online', (data) => {
    console.log('[Socket.IO] User online:', data.user_id);
    const contactItem = document.querySelector(`[data-contact-id="${data.user_id}"]`);
    if (contactItem) {
        contactItem.dataset.contactStatus = 'Active now';
        if (data.user_id === currentContactId) {
            chatContactStatus.textContent = 'Active now';
            chatContactStatus.style.color = '#22c55e';
        }
    }
});

/**
 * When a user goes offline
 */
socket.on('user_offline', (data) => {
    console.log('[Socket.IO] User offline:', data.user_id);
    const contactItem = document.querySelector(`[data-contact-id="${data.user_id}"]`);
    if (contactItem) {
        contactItem.dataset.contactStatus = 'Offline';
        if (data.user_id === currentContactId) {
            chatContactStatus.textContent = 'Offline';
            chatContactStatus.style.color = '#888';
        }
    }
});

/**
 * When a message is edited (real-time sync)
 */
socket.on('message_edited', (data) => {
    console.log('[Socket.IO] Message edited:', data);

    // Convert message_id to string for DOM selector (data attributes are strings)
    const messageIdStr = String(data.message_id);

    // Update the message bubble if currently viewing this chat
    const messageDiv = document.querySelector(`[data-message-id="${messageIdStr}"]`);
    if (messageDiv) {
        const bubble = messageDiv.querySelector('.bubble');
        const pElement = bubble.querySelector('p');
        if (pElement) {
            pElement.textContent = data.new_content;
        }
        // Add edited indicator if not present
        if (!bubble.querySelector('.edited-indicator')) {
            bubble.innerHTML += '<span class="edited-indicator">(edited)</span>';
        }
    }

    // Update inbox preview - determine which contact to update
    const otherUserId = data.sender_id === CURRENT_USER_ID ? data.receiver_id : data.sender_id;
    const isSentByMe = data.sender_id === CURRENT_USER_ID;
    updateContactPreview(otherUserId, data.new_content, isSentByMe ? 'sent' : 'received');
});

/**
 * When a message is deleted (real-time sync)
 */
socket.on('message_deleted', (data) => {
    console.log('[Socket.IO] Message deleted:', data);

    // Convert message_id to string for DOM selector (data attributes are strings)
    const messageIdStr = String(data.message_id);

    // Remove the message bubble if currently viewing this chat
    const messageDiv = document.querySelector(`[data-message-id="${messageIdStr}"]`);
    if (messageDiv) {
        messageDiv.style.transition = 'opacity 0.3s, transform 0.3s';
        messageDiv.style.opacity = '0';
        setTimeout(() => {
            messageDiv.remove();

            // After removal, update inbox preview with actual last message
            updateInboxAfterDelete(data.sender_id, data.receiver_id);
        }, 300);
    } else {
        // Message not visible (not viewing this chat), still update inbox
        updateInboxAfterDelete(data.sender_id, data.receiver_id);
    }
});

/**
 * Update inbox preview after a message is deleted
 */
function updateInboxAfterDelete(senderId, receiverId) {
    const otherUserId = senderId === CURRENT_USER_ID ? receiverId : senderId;

    // Only update if viewing this contact's chat
    if (otherUserId === currentContactId) {
        const remainingMessages = document.querySelectorAll('#chat-messages .message');
        if (remainingMessages.length > 0) {
            const lastMessage = remainingMessages[remainingMessages.length - 1];
            if (lastMessage) {
                const text = lastMessage.querySelector('.bubble p')?.textContent || '';
                const isSent = lastMessage.classList.contains('sent');
                updateContactPreview(otherUserId, text, isSent ? 'sent' : 'received');
            }
        } else {
            updateContactPreview(otherUserId, 'No messages yet', '');
        }
    }
}

// ============================================
// HELPER FUNCTIONS
// ============================================

/**
 * Append a single message to the chat (for real-time updates)
 */
function appendMessage(msg) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${msg.type}`;
    if (msg.id) messageDiv.dataset.messageId = msg.id;

    // Add action buttons for sent messages
    const actionsHtml = msg.type === 'sent' ? `
        <div class="message-actions">
            <button class="message-action-btn edit" title="Edit message" onclick="startEditMessage(this)">
                <i class="bi bi-pencil"></i>
            </button>
            <button class="message-action-btn delete" title="Delete message" onclick="showDeleteModal(this)">
                <i class="bi bi-trash"></i>
            </button>
        </div>
    ` : '';

    const editedIndicator = msg.edited ? '<span class="edited-indicator">(edited)</span>' : '';

    messageDiv.innerHTML = `
        ${actionsHtml}
        <div class="bubble">
            <p>${msg.text}</p>
            ${editedIndicator}
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Update the preview text for a contact in the sidebar
 */
function updateContactPreview(contactId, text, type) {
    const contactItem = document.querySelector(`[data-contact-id="${contactId}"]`);
    if (contactItem) {
        const preview = contactItem.querySelector('.preview');
        if (preview) {
            const prefix = type === 'sent' ? 'You: ' : '';
            preview.textContent = `${prefix}${text.substring(0, 25)}${text.length > 25 ? '...' : ''}`;
        }
    }
}

/**
 * Update the unread badge for a contact
 * Shows count 1-9, or "9+" for 10+
 */
function updateUnreadBadge(contactId) {
    const contactItem = document.querySelector(`[data-contact-id="${contactId}"]`);
    if (!contactItem) return;

    const count = unreadCounts[contactId] || 0;
    let badge = contactItem.querySelector('.unread-badge');

    if (count > 0) {
        // Create badge if it doesn't exist
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'unread-badge';
            contactItem.appendChild(badge);
        }
        // Display count (max "9+")
        badge.textContent = count > 9 ? '9+' : count;
    } else if (badge) {
        // Remove badge if count is 0
        badge.remove();
    }
}

/**
 * Clear unread badge for a contact
 */
function clearUnreadBadge(contactId) {
    unreadCounts[contactId] = 0;
    updateUnreadBadge(contactId);
}

/**
 * Show typing indicator
 */
function showTypingIndicator() {
    // Remove existing indicator first
    let indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }

    // Create and append at the end
    indicator = document.createElement('div');
    indicator.id = 'typing-indicator';
    indicator.className = 'typing-indicator';
    indicator.innerHTML = '<span></span><span></span><span></span>';
    chatMessages.appendChild(indicator);

    // Scroll to bottom to show the indicator
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Hide typing indicator
 */
function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
}

/**
 * Render all messages in the chat container
 */
function renderMessages(messages) {
    chatMessages.innerHTML = '';

    messages.forEach(msg => {
        if (msg.type === 'timestamp') {
            chatMessages.innerHTML += `<div class="timestamp">${msg.text}</div>`;
        } else if (msg.type === 'cyber-challenge') {
            chatMessages.innerHTML += `
                <div class="cyber-challenge-card">
                    <h3>Cyber Challenge!</h3>
                    <p>Can you detect if this scenario is safe or a scam?</p>
                    <div class="reward-info">
                        <span class="reward-label">Rewards:</span>
                        <div class="reward-value">
                            <img src="/static/images/credit.svg" class="credit-icon-small2">
                            <span>${msg.reward || 15}</span>
                        </div>
                    </div>
                    <button class="btn-view">View</button>
                </div>
            `;
        } else {
            // Add action buttons for sent messages
            const actionsHtml = msg.type === 'sent' ? `
                <div class="message-actions">
                    <button class="message-action-btn edit" title="Edit message" onclick="startEditMessage(this)">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="message-action-btn delete" title="Delete message" onclick="showDeleteModal(this)">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            ` : '';

            const editedIndicator = msg.edited ? '<span class="edited-indicator">(edited)</span>' : '';

            chatMessages.innerHTML += `
                <div class="message ${msg.type}" data-message-id="${msg.id || ''}">
                    ${actionsHtml}
                    <div class="bubble">
                        <p>${msg.text}</p>
                        ${editedIndicator}
                    </div>
                </div>
            `;
        }
    });

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ============================================
// EDIT & DELETE FUNCTIONS (CRUD)
// ============================================

/**
 * Start editing a message - shows input field
 */
function startEditMessage(button) {
    const messageDiv = button.closest('.message');
    const bubble = messageDiv.querySelector('.bubble');
    const currentText = bubble.querySelector('p').textContent;
    const messageId = messageDiv.dataset.messageId;

    // Hide the bubble and show edit input
    bubble.style.display = 'none';
    messageDiv.querySelector('.message-actions').style.display = 'none';

    // Create edit UI
    const editContainer = document.createElement('div');
    editContainer.className = 'edit-container';
    editContainer.innerHTML = `
        <input type="text" class="edit-input" value="${currentText}">
        <div class="edit-actions">
            <button class="save-btn" onclick="saveEditMessage(this, '${messageId}')">Save</button>
            <button class="cancel-btn" onclick="cancelEditMessage(this)">Cancel</button>
        </div>
    `;
    messageDiv.appendChild(editContainer);

    // Focus the input and select all text
    const input = editContainer.querySelector('.edit-input');
    input.focus();
    input.select();

    // Save on Enter, cancel on Escape
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            saveEditMessage(editContainer.querySelector('.save-btn'), messageId);
        } else if (e.key === 'Escape') {
            cancelEditMessage(editContainer.querySelector('.cancel-btn'));
        }
    });
}

/**
 * Save the edited message
 */
function saveEditMessage(button, messageId) {
    const messageDiv = button.closest('.message');
    const editContainer = messageDiv.querySelector('.edit-container');
    const newText = editContainer.querySelector('.edit-input').value.trim();

    if (!newText) {
        alert('Message cannot be empty');
        return;
    }

    // Emit edit event via Socket.IO
    socket.emit('edit_message', {
        message_id: messageId,
        user_id: CURRENT_USER_ID,
        new_content: newText
    });

    // Update UI immediately (optimistic update)
    const bubble = messageDiv.querySelector('.bubble');
    bubble.querySelector('p').textContent = newText;

    // Add edited indicator if not already there
    if (!bubble.querySelector('.edited-indicator')) {
        bubble.innerHTML += '<span class="edited-indicator">(edited)</span>';
    }

    // Remove edit container and show bubble
    editContainer.remove();
    bubble.style.display = '';
    messageDiv.querySelector('.message-actions').style.display = '';
}

/**
 * Cancel editing and restore original view
 */
function cancelEditMessage(button) {
    const messageDiv = button.closest('.message');
    const editContainer = messageDiv.querySelector('.edit-container');
    const bubble = messageDiv.querySelector('.bubble');

    editContainer.remove();
    bubble.style.display = '';
    messageDiv.querySelector('.message-actions').style.display = '';
}

/**
 * Show delete confirmation modal
 */
function showDeleteModal(button) {
    const messageDiv = button.closest('.message');
    const messageId = messageDiv.dataset.messageId;
    const messageText = messageDiv.querySelector('.bubble p').textContent;

    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'delete-modal-overlay';
    overlay.innerHTML = `
        <div class="delete-modal">
            <h4>Delete Message?</h4>
            <p>"${messageText.substring(0, 50)}${messageText.length > 50 ? '...' : ''}"</p>
            <div class="delete-modal-actions">
                <button class="confirm-delete">Delete</button>
                <button class="cancel-delete">Cancel</button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    // Handle confirm delete
    overlay.querySelector('.confirm-delete').addEventListener('click', () => {
        deleteMessage(messageId, messageDiv);
        overlay.remove();
    });

    // Handle cancel
    overlay.querySelector('.cancel-delete').addEventListener('click', () => {
        overlay.remove();
    });

    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.remove();
        }
    });
}

/**
 * Delete a message
 */
function deleteMessage(messageId, messageDiv) {
    console.log('[DEBUG] deleteMessage called with:', {
        messageId: messageId,
        messageIdType: typeof messageId,
        user_id: CURRENT_USER_ID
    });

    // Check if messageId is valid
    if (!messageId) {
        console.error('[DEBUG] No messageId provided!');
        return;
    }

    // Emit delete event via Socket.IO
    console.log('[DEBUG] Emitting delete_message event...');
    socket.emit('delete_message', {
        message_id: messageId,
        user_id: CURRENT_USER_ID
    });
    console.log('[DEBUG] delete_message emitted');

    // Remove from UI with fade animation
    messageDiv.style.transition = 'opacity 0.3s, transform 0.3s';
    messageDiv.style.opacity = '0';
    messageDiv.style.transform = 'translateX(20px)';

    setTimeout(() => {
        messageDiv.remove();
    }, 300);
}

/**
 * Load messages from the server (initial load)
 */
async function loadMessages(contactId) {
    try {
        const response = await fetch(`/social/api/messages/${contactId}?user=${CURRENT_USER_ID}`);
        const messages = await response.json();
        renderMessages(messages);
        return messages;
    } catch (error) {
        console.error('Error loading messages:', error);
        renderMessages([]);
        return [];
    }
}

/**
 * Load contacts from API and render the contact list
 */
async function loadContacts() {
    try {
        const response = await fetch(`/social/api/contacts?user=${CURRENT_USER_ID}`);
        const contacts = await response.json();

        // Clear loading message
        contactList.innerHTML = '';

        if (contacts.length === 0) {
            contactList.innerHTML = '<li style="padding: 20px; text-align: center; color: #888;">No contacts found</li>';
            return;
        }

        // Create contact items
        contacts.forEach((contact, index) => {
            const isActive = contact.id === currentContactId;
            const li = document.createElement('li');
            li.className = `contact-item${isActive ? ' active' : ''}`;
            li.dataset.contactId = contact.id;
            li.dataset.contactName = contact.name;
            li.dataset.contactStatus = contact.status;

            li.innerHTML = `
                <div class="avatar">
                    <i class="bi bi-person-fill"></i>
                </div>
                <div class="contact-info">
                    <span class="name">${contact.name}</span>
                    <span class="preview">${contact.lastMessage || 'No messages yet'}</span>
                </div>
            `;

            // Add click handler
            li.addEventListener('click', () => {
                switchContact(contact.id, contact.name, contact.status);
            });

            contactList.appendChild(li);

            // Set the first contact as current if we don't have one set
            if (index === 0 && !currentContactId) {
                currentContactId = contact.id;
            }
        });

        // Update current contact ID to first contact if current doesn't exist
        const currentExists = contacts.some(c => c.id === currentContactId);
        if (!currentExists && contacts.length > 0) {
            currentContactId = contacts[0].id;
        }

        // Update header with first contact
        const activeContact = contacts.find(c => c.id === currentContactId);
        if (activeContact) {
            chatContactName.textContent = activeContact.name;
            chatContactStatus.textContent = activeContact.status;
            chatContactStatus.style.color = activeContact.status === 'Active now' ? '#22c55e' : '#888';
        }

    } catch (error) {
        console.error('Error loading contacts:', error);
        contactList.innerHTML = '<li style="padding: 20px; text-align: center; color: #f00;">Error loading contacts</li>';
    }
}

/**
 * Switch to a different contact
 */
function switchContact(contactId, contactName, contactStatus) {
    // Leave the old room
    socket.emit('leave_chat', { user_id: CURRENT_USER_ID, contact_id: currentContactId });

    currentContactId = contactId;

    // Join the new room
    socket.emit('join_chat', { user_id: CURRENT_USER_ID, contact_id: contactId });

    // Clear unread badge for this contact
    clearUnreadBadge(contactId);

    // Update header
    chatContactName.textContent = contactName;
    chatContactStatus.textContent = contactStatus || 'Active now';

    // Update status color
    if (contactStatus === "Active now") {
        chatContactStatus.style.color = "#22c55e";
    } else {
        chatContactStatus.style.color = "#888";
    }

    // Update active state in contact list
    document.querySelectorAll('.contact-item').forEach(item => {
        item.classList.remove('active');
    });
    const activeItem = document.querySelector(`[data-contact-id="${contactId}"]`);
    if (activeItem) {
        activeItem.classList.add('active');
    }

    // Load messages from server
    loadMessages(contactId);
}

/**
 * Send a new message using Socket.IO
 */
function sendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;

    // Send via Socket.IO (real-time!)
    socket.emit('send_message', {
        sender_id: CURRENT_USER_ID,
        receiver_id: currentContactId,
        content: text
    });

    // Clear input
    messageInput.value = '';
}

// ============================================
// TYPING INDICATOR
// ============================================

let typingTimeout;

function handleTyping() {
    // Emit typing event
    socket.emit('typing', {
        user_id: CURRENT_USER_ID,
        receiver_id: currentContactId,
        is_typing: true
    });

    // Stop typing after 2 seconds of no input
    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(() => {
        socket.emit('typing', {
            user_id: CURRENT_USER_ID,
            receiver_id: currentContactId,
            is_typing: false
        });
    }, 2000);
}

// ============================================
// EVENT LISTENERS
// ============================================

document.addEventListener('DOMContentLoaded', async () => {
    // Load contacts from API (dynamic list)
    await loadContacts();

    // Load messages for the current contact
    if (currentContactId) {
        loadMessages(currentContactId);
    }

    // Send button
    sendBtn.addEventListener('click', sendMessage);

    // Enter key to send
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Typing indicator
    messageInput.addEventListener('input', handleTyping);

    // Search filter
    const searchInput = document.getElementById('contact-search');
    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase().trim();

        document.querySelectorAll('.contact-item').forEach(item => {
            const name = item.dataset.contactName.toLowerCase();
            if (name.includes(searchTerm)) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    });
});

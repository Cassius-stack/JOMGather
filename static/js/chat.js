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

// ============================================
// HELPER FUNCTIONS
// ============================================

/**
 * Append a single message to the chat (for real-time updates)
 */
function appendMessage(msg) {
    const messageHtml = `
        <div class="message ${msg.type}">
            <div class="bubble">
                <p>${msg.text}</p>
            </div>
        </div>
    `;
    chatMessages.innerHTML += messageHtml;
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
            chatMessages.innerHTML += `
                <div class="message ${msg.type}">
                    <div class="bubble">
                        <p>${msg.text}</p>
                    </div>
                </div>
            `;
        }
    });

    chatMessages.scrollTop = chatMessages.scrollHeight;
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

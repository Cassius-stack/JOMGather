/**
 * JOMGather Chat System with Socket.IO
 * Real-time messaging with SQLite persistence
 */

// ============================================
// SOCKET.IO CONNECTION
// ============================================

// Connect to the Socket.IO server (explicitly use current host for cross-device support)
const socket = io(window.location.origin, {
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000
});

console.log('[Socket.IO] Connecting to:', window.location.origin);

// CURRENT_USER_ID is injected globally in social_hub.html
// Ensure it exists
if (typeof CURRENT_USER_ID === 'undefined') {
    console.error("Critical Error: CURRENT_USER_ID is missing. Redirecting to login...");
    window.location.href = '/auth/login';
}

// Default contact will be determined by loadContacts()
let currentContactId = null;

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
    console.log('[Socket.IO] ✅ Connected to server as user', CURRENT_USER_ID, 'Socket ID:', socket.id);
    // Register ourselves with the server
    socket.emit('register_user', { user_id: CURRENT_USER_ID });
    // Join the current chat room
    socket.emit('join_chat', { user_id: CURRENT_USER_ID, contact_id: currentContactId });
});

/**
 * Connection error handling
 */
socket.on('connect_error', (error) => {
    console.error('[Socket.IO] ❌ Connection error:', error);
});

socket.on('disconnect', (reason) => {
    console.log('[Socket.IO] ⚠️ Disconnected:', reason);
});

/**
 * When we receive a validation error from the server
 * Display user-friendly error messages
 */
socket.on('validation_error', (data) => {
    console.log('[Socket.IO] Validation error:', data);

    // Show error message to user
    if (data.error) {
        // Create a toast notification
        showValidationError(data.error);
    }
});

/**
 * Display validation error as a toast notification
 */
function showValidationError(message) {
    // Remove existing error toast if any
    const existing = document.querySelector('.validation-toast');
    if (existing) existing.remove();

    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'validation-toast';
    toast.innerHTML = `
        <i class="bi bi-exclamation-circle"></i>
        <span>${message}</span>
    `;

    // Add styles
    toast.style.cssText = `
        position: fixed;
        bottom: 100px;
        left: 50%;
        transform: translateX(-50%);
        background: #dc3545;
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        font-size: 14px;
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        animation: slideUp 0.3s ease;
    `;

    document.body.appendChild(toast);

    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Track processed message IDs to avoid duplicates
const processedMessageIds = new Set();

/**
 * When we receive a new message (real-time!)
 * This is the magic - messages appear instantly without refresh
 */
socket.on('new_message', (data) => {
    console.log('[Socket.IO] New message received:', data);

    // If I am the receiver and the chat is open, mark it as read immediately
    if (data.receiver_id === CURRENT_USER_ID && data.sender_id === currentContactId) {
        socket.emit('mark_read', { user_id: CURRENT_USER_ID, sender_id: currentContactId });
    }

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
        // Check if this is a cyber challenge
        if (data.is_cyber_challenge || data.text === '!cyber') {
            appendCyberChallenge(data.id, data.challenge_id, data.scenario_id);
        } else {
            appendMessage({
                id: data.id,
                type: messageType,
                text: data.text,
                image_url: data.image_url
            });
        }
    } else if (messageType === 'received') {
        // Message from a different contact - increment unread count
        unreadCounts[otherUserId] = (unreadCounts[otherUserId] || 0) + 1;
        updateUnreadBadge(otherUserId);
    }

    // Always update the contact preview
    let previewText = data.text;
    if (data.is_cyber_challenge) {
        previewText = '🎮 Cyber Challenge!';
    } else if (!data.text && data.image_url) {
        previewText = '📷 Photo';
    }

    updateContactPreview(otherUserId, previewText, messageType);

    // Move this contact to top of the list
    moveContactToTop(otherUserId);
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
 * When messages are read by the recipient
 */
socket.on('messages_read', (data) => {
    console.log('[Socket.IO] Messages read:', data);

    // If the person reading is the person I'm chatting with
    if (data.reader_id === currentContactId) {
        // Find all my sent messages and change ticks to read
        const mySentMessages = document.querySelectorAll('.message.sent .message-tick i');
        mySentMessages.forEach(tick => {
            tick.className = 'bi bi-check-all'; // Double tick
            tick.parentElement.classList.add('read');
        });
    }
});

/**
 * When a partner submits their cyber challenge answer (waiting state)
 */
socket.on('cyber_answer_submitted', (data) => {
    console.log('[Socket.IO] Cyber answer submitted:', data);

    // If the answer came from someone else, update our waiting modal
    if (data.user_id !== CURRENT_USER_ID) {
        // The other user has answered - but we might still be waiting
        const partnerStatus = document.getElementById(`partner-status-${data.challenge_id}`);
        if (partnerStatus) {
            partnerStatus.querySelector('.status-waiting')?.classList.remove('status-waiting');
            partnerStatus.querySelector('.participant-info span:last-child')?.classList.add('status-completed');
            if (partnerStatus.querySelector('.participant-info span:last-child')) {
                partnerStatus.querySelector('.participant-info span:last-child').textContent = 'Completed challenge';
            }
        }
    }
});

// Track processed challenge completions to avoid duplicates
const processedChallengeCompletions = new Set();

/**
 * When both users have answered the cyber challenge - show results
 */
socket.on('cyber_challenge_complete', (data) => {
    console.log('[Socket.IO] Cyber challenge complete:', data);

    const challengeId = data.challenge_id;

    // Deduplicate - skip if already processed
    if (processedChallengeCompletions.has(challengeId)) {
        console.log('[Socket.IO] Skipping duplicate challenge complete:', challengeId);
        return;
    }
    processedChallengeCompletions.add(challengeId);

    // Also skip if state already marked completed
    if (currentChallengeState[challengeId]?.completed) {
        console.log('[Socket.IO] Challenge already marked complete:', challengeId);
        return;
    }

    // Store the results
    const scenario = cyberScenarios.find(s => s.id === data.scenario_id);
    const correctAnswer = scenario?.answer || 'scam';

    // Determine results for display
    const user1Correct = data.user1_answer === correctAnswer;
    const user2Correct = data.user2_answer === correctAnswer;
    const bothCorrect = user1Correct && user2Correct;

    // Figure out which user we are
    const amUser1 = data.user1_id === CURRENT_USER_ID;
    const myCorrect = amUser1 ? user1Correct : user2Correct;
    const partnerCorrect = amUser1 ? user2Correct : user1Correct;

    // Store complete results for display
    currentChallengeState[challengeId] = {
        ...currentChallengeState[challengeId],
        completed: true,
        scenario: scenario,
        scenarioId: data.scenario_id,
        myCorrect: myCorrect,
        partnerCorrect: partnerCorrect,
        bothCorrect: bothCorrect,
        user1_id: data.user1_id,
        user2_id: data.user2_id
    };

    // Close any open waiting modal for this challenge
    const existingModal = document.getElementById(`cyber-modal-${challengeId}`);
    if (existingModal) {
        existingModal.remove();
    }

    // Append "Results are out!" card to the chat
    appendResultsCard(challengeId, data.scenario_id);
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
    const showEdit = !msg.image_url;
    const actionsHtml = `
        <div class="message-actions">
            ${msg.type === 'sent' ? `
                ${showEdit ? `
                <button class="message-action-btn edit" title="Edit message" onclick="startEditMessage(this)">
                    <i class="bi bi-pencil"></i>
                </button>
                ` : ''}
                <button class="message-action-btn delete" title="Delete message" onclick="showDeleteModal(this)">
                    <i class="bi bi-trash"></i>
                </button>
            ` : ''}
            <button class="react-btn" onclick="toggleReactionPicker(this)" title="Add reaction">😊</button>
        </div>
    `;

    const editedIndicator = msg.edited ? '<span class="edited-indicator">(edited)</span>' : '';

    // Image HTML
    const imageHtml = msg.image_url ? `
        <div class="message-image" style="margin-bottom: 5px;">
            <img src="${msg.image_url}" alt="Attachment" style="max-width: 200px; border-radius: 8px; cursor: pointer;" onclick="window.open(this.src, '_blank')">
        </div>
    ` : '';

    messageDiv.innerHTML = `
        ${actionsHtml}
        <div class="message-content">
            <div class="bubble">
                ${imageHtml}
                ${msg.text ? `<p style="margin: 0;">${msg.text}</p>` : ''}
                ${editedIndicator}
                ${msg.type === 'sent' ? `<span class="message-tick ${msg.read ? 'read' : ''}"><i class="bi bi-check${msg.read ? '-all' : ''}"></i></span>` : ''}
            </div>
            <div class="msg-reactions-chat"></div>
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

            // Handle Slice of Life HTML cards in preview
            let display_text = text;
            if (text && text.includes('Slice of Life Invite')) {
                display_text = '🎨 Slice of Life Invite';
            }

            preview.textContent = `${prefix}${display_text.substring(0, 25)}${display_text.length > 25 ? '...' : ''}`;
        }
    }
}

/**
 * Move a contact to the top of the contact list (for new messages)
 */
function moveContactToTop(contactId) {
    const contactItem = document.querySelector(`[data-contact-id="${contactId}"]`);
    if (contactItem && contactList.firstChild !== contactItem) {
        contactList.insertBefore(contactItem, contactList.firstChild);
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
        } else if (msg.text === '!cyber' || msg.type === 'cyber-challenge') {
            // This is a cyber challenge - render as a challenge card
            // Use a random scenario for display (scenario was stored in DB but we use local for now)
            const scenario = cyberScenarios[Math.floor(Math.random() * cyberScenarios.length)];
            const effectiveChallengeId = msg.challenge_id || `msg_${msg.id}`;
            const effectiveScenarioId = msg.scenario_id || scenario.id;

            chatMessages.innerHTML += `
                <div class="cyber-challenge-card" data-message-id="${msg.id}" data-challenge-id="${effectiveChallengeId}" data-scenario-id="${effectiveScenarioId}" id="cyber-card-${effectiveChallengeId}">
                    <h3>🎮 Cyber Challenge!</h3>
                    <p>Can you detect if this scenario is safe or a scam?</p>
                    <div class="reward-info">
                        <span class="reward-label">Rewards:</span>
                        <div class="reward-value">
                            <img src="/static/images/credit.svg" class="credit-icon-small2" onerror="this.style.display='none'">
                            <span>15</span>
                        </div>
                    </div>
                    <button class="btn-view" onclick="showCyberChallengeModal('${effectiveChallengeId}', ${effectiveScenarioId})">View</button>
                </div>
            `;

            // Async check if this challenge is completed and update the card
            checkAndUpdateChallengeCard(effectiveChallengeId, effectiveScenarioId);
        } else {
            // Add action buttons for messages
            const showEdit = !msg.image_url;
            const actionsHtml = `
                <div class="message-actions">
                    ${msg.type === 'sent' ? `
                        ${showEdit ? `
                        <button class="message-action-btn edit" title="Edit message" onclick="startEditMessage(this)">
                            <i class="bi bi-pencil"></i>
                        </button>
                        ` : ''}
                        <button class="message-action-btn delete" title="Delete message" onclick="showDeleteModal(this)">
                            <i class="bi bi-trash"></i>
                        </button>
                    ` : ''}
                    <button class="react-btn" onclick="toggleReactionPicker(this)" title="Add reaction">😊</button>
                </div>
            `;

            const editedIndicator = msg.edited ? '<span class="edited-indicator">(edited)</span>' : '';

            // Image HTML
            const imageHtml = msg.image_url ? `
                <div class="message-image" style="margin-bottom: 5px;">
                    <img src="${msg.image_url}" alt="Attachment" style="max-width: 200px; border-radius: 8px; cursor: pointer;" onclick="window.open(this.src, '_blank')">
                </div>
            ` : '';

            chatMessages.innerHTML += `
                <div class="message ${msg.type}" data-message-id="${msg.id || ''}">
                    ${actionsHtml}
                    <div class="message-content">
                        <div class="bubble">
                            ${imageHtml}
                            ${msg.text ? `<p style="margin: 0;">${msg.text}</p>` : ''}
                            ${editedIndicator}
                            ${msg.type === 'sent' ? `<span class="message-tick ${msg.read ? 'read' : ''}"><i class="bi bi-check${msg.read ? '-all' : ''}"></i></span>` : ''}
                        </div>
                        <div class="msg-reactions-chat"></div>
                    </div>
                </div>
            `;
        }
    });

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Check challenge status and update card if completed
 */
async function checkAndUpdateChallengeCard(challengeId, scenarioId) {
    try {
        const response = await fetch(`/social/api/cyber-challenge/${challengeId}?user=${CURRENT_USER_ID}`);
        const data = await response.json();

        if (data.found && data.status === 'completed') {
            // Use scenario_id from database, not the random one
            const dbScenarioId = data.scenario_id || scenarioId;

            // Challenge is completed - replace card with results card
            const card = document.getElementById(`cyber-card-${challengeId}`);
            if (card) {
                card.outerHTML = `<div class="cyber-results-card" data-challenge-id="${challengeId}" data-scenario-id="${dbScenarioId}"><h3>🎮 Cyber Challenge!</h3><p>Results for the challenge are out!</p><button class="btn-view" onclick="showCyberChallengeModal('${challengeId}', ${dbScenarioId})">View Results</button></div>`;

                // Store the state for the results modal
                const scenario = cyberScenarios.find(s => s.id === dbScenarioId);
                const correctAnswer = scenario?.answer || 'scam';
                const amUser1 = data.user1_id === CURRENT_USER_ID;
                const user1Correct = data.user1_answer === correctAnswer;
                const user2Correct = data.user2_answer === correctAnswer;

                currentChallengeState[challengeId] = {
                    completed: true,
                    scenario: scenario,
                    scenarioId: dbScenarioId,
                    correctAnswer: correctAnswer,
                    myCorrect: amUser1 ? user1Correct : user2Correct,
                    partnerCorrect: amUser1 ? user2Correct : user1Correct,
                    bothCorrect: user1Correct && user2Correct,
                    user1_id: data.user1_id,
                    user2_id: data.user2_id
                };
            }
        }
    } catch (error) {
        // Silently fail - keep showing the challenge card
        console.log('Could not fetch challenge status for card update:', error);
    }
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
    const pElement = bubble.querySelector('p');
    const currentText = pElement ? pElement.textContent : '';
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
    const pElement = messageDiv.querySelector('.bubble p');
    const messageText = pElement ? pElement.textContent : 'Photo attachment';

    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'delete-modal-overlay';
    overlay.innerHTML = `
        <div class="delete-modal">
            <h4><i class="bi bi-exclamation-triangle"></i> Delete Message?</h4>
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

// ============================================
// REACTION FUNCTIONS
// ============================================

const chatEmojis = ['👍', '❤️', '🎉'];

/**
 * Toggle reaction emoji picker for a message
 */
function toggleReactionPicker(button) {
    // Close any existing emoji picker
    const existingPicker = document.querySelector('.emoji-picker-chat');
    if (existingPicker) {
        existingPicker.remove();
    }

    const messageDiv = button.closest('.message');
    const messageId = messageDiv.dataset.messageId;

    // Create emoji picker
    const picker = document.createElement('div');
    picker.className = 'emoji-picker-chat';
    picker.innerHTML = chatEmojis.map(e =>
        `<button onclick="addReactionToMessage('${messageId}', '${e}', this)">${e}</button>`
    ).join('');

    // Position it near the button
    button.parentElement.appendChild(picker);

    // Close picker when clicking outside
    document.addEventListener('click', function closePicker(e) {
        if (!picker.contains(e.target) && e.target !== button) {
            picker.remove();
            document.removeEventListener('click', closePicker);
        }
    });
}

/**
 * Add a reaction emoji to a message (visual only for now)
 */
function addReactionToMessage(messageId, emoji, button) {
    const picker = button.closest('.emoji-picker-chat');
    const messageDiv = document.querySelector(`[data-message-id="${messageId}"]`);

    if (messageDiv) {
        // Check if reactions container exists
        let reactionsDiv = messageDiv.querySelector('.msg-reactions-chat');
        if (!reactionsDiv) {
            reactionsDiv = document.createElement('div');
            reactionsDiv.className = 'msg-reactions-chat';
            messageDiv.querySelector('.bubble').after(reactionsDiv);
        }

        // Check if this emoji already exists
        let badge = reactionsDiv.querySelector(`[data-emoji="${emoji}"]`);
        if (badge) {
            // Increment count
            const count = parseInt(badge.dataset.count || 1) + 1;
            badge.dataset.count = count;
            badge.textContent = `${emoji} ${count}`;
        } else {
            // Add new reaction badge
            badge = document.createElement('span');
            badge.className = 'reaction-badge-chat';
            badge.dataset.emoji = emoji;
            badge.dataset.count = 1;
            badge.textContent = `${emoji} 1`;
            badge.onclick = () => addReactionToMessage(messageId, emoji, badge);
            reactionsDiv.appendChild(badge);
        }
    }

    // Remove picker
    if (picker) picker.remove();
}

// ============================================
// CYBER CHALLENGE FUNCTIONS
// ============================================

// Sample cyber challenge scenarios
const cyberScenarios = [
    {
        id: 1,
        title: "URGENT: Action needed immediately",
        sender: "SingTel Support",
        email: "singtel.offical@mail.com",
        content: "Dear User,\n\nYour account has been scheduled for deletion in 6 hours. Please click on the button below and make the changes immediately.",
        buttonText: "Click here now",
        footer: "Government of Singapore\nAutomated message. Please do not reply.",
        answer: "scam",
        explanation: "This is a SCAM! Red flags: Urgent pressure tactics, suspicious email (offical vs official), vague threats, and asking you to click unknown links."
    },
    {
        id: 2,
        title: "Your Package Delivery",
        sender: "DHL Express",
        email: "noreply@dhl.com",
        content: "Dear Customer,\n\nYour package #SG847291 is waiting for customs clearance. Pay $2.50 fee to release it.",
        buttonText: "Pay Now",
        footer: "DHL Express Singapore",
        answer: "scam",
        explanation: "This is a SCAM! Real delivery companies don't ask for payments via random emails. Always check tracking on official websites."
    },
    {
        id: 3,
        title: "2FA Verification Code",
        sender: "Google",
        email: "noreply@google.com",
        content: "Your Google verification code is: 847291\n\nDon't share this code with anyone. Google will never call you to ask for this code.",
        buttonText: null,
        footer: "You received this email because you requested a sign-in code.",
        answer: "safe",
        explanation: "This is SAFE! It's a standard 2FA code you requested. Note: Never share this code with anyone who calls or messages you."
    }
];

/**
 * Append a cyber challenge card to the chat
 * @param {number} messageId - The message ID
 * @param {number} challengeId - The challenge ID from server (may be null if table doesn't exist)
 * @param {number} scenarioId - The scenario ID from server
 */
function appendCyberChallenge(messageId, challengeId, scenarioId) {
    const scenario = cyberScenarios.find(s => s.id === scenarioId) || cyberScenarios[0];

    // Use messageId as fallback if challengeId is null (table doesn't exist yet)
    const effectiveChallengeId = challengeId || `msg_${messageId}`;
    const effectiveScenarioId = scenarioId || scenario.id;

    const challengeHtml = `
        <div class="cyber-challenge-card" data-message-id="${messageId}" data-challenge-id="${effectiveChallengeId}" data-scenario-id="${effectiveScenarioId}">
            <h3>🎮 Cyber Challenge!</h3>
            <p>Can you detect if this scenario is safe or a scam?</p>
            <div class="reward-info">
                <span class="reward-label">Rewards:</span>
                <div class="reward-value">
                    <img src="/static/images/credit.svg" class="credit-icon-small2" onerror="this.style.display='none'">
                    <span>15</span>
                </div>
            </div>
            <button class="btn-view" onclick="showCyberChallengeModal('${effectiveChallengeId}', ${effectiveScenarioId})">View</button>
        </div>
    `;

    chatMessages.innerHTML += challengeHtml;
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Show the cyber challenge modal with scenario
 * @param {string|number} challengeId - The challenge ID from server
 * @param {number} scenarioId - The scenario ID
 */
async function showCyberChallengeModal(challengeId, scenarioId) {
    const scenario = cyberScenarios.find(s => s.id === scenarioId);
    if (!scenario) return;

    // Check if user has already answered (from in-memory state first)
    const existingState = currentChallengeState[challengeId];
    if (existingState && existingState.myAnswer) {
        // Check if challenge is completed (both answered)
        if (existingState.completed) {
            showResultsModal(challengeId);
        } else {
            showWaitingModal(challengeId, scenarioId);
        }
        return;
    }

    // Fetch challenge status from database
    try {
        const response = await fetch(`/social/api/cyber-challenge/${challengeId}?user=${CURRENT_USER_ID}`);
        const data = await response.json();

        if (data.found && data.my_answer) {
            // User already answered - store in local state and show appropriate modal
            currentChallengeState[challengeId] = {
                myAnswer: data.my_answer,
                scenarioId: data.scenario_id,
                correctAnswer: scenario.answer,
                completed: data.status === 'completed',
                user1_id: data.user1_id,
                user2_id: data.user2_id
            };

            if (data.status === 'completed') {
                // Both users answered - show results
                const amUser1 = data.user1_id === CURRENT_USER_ID;
                const user1Correct = data.user1_answer === scenario.answer;
                const user2Correct = data.user2_answer === scenario.answer;

                currentChallengeState[challengeId].myCorrect = amUser1 ? user1Correct : user2Correct;
                currentChallengeState[challengeId].partnerCorrect = amUser1 ? user2Correct : user1Correct;
                currentChallengeState[challengeId].bothCorrect = user1Correct && user2Correct;
                currentChallengeState[challengeId].scenario = scenario;

                showResultsModal(challengeId);
            } else {
                // Still waiting for partner
                showWaitingModal(challengeId, scenarioId);
            }
            return;
        }
    } catch (error) {
        console.log('Could not fetch challenge status:', error);
        // Continue to show the challenge - might be a new challenge or DB issue
    }

    const buttonHtml = scenario.buttonText ?
        `<div class="fake-button">${scenario.buttonText}</div>` : '';

    const overlay = document.createElement('div');
    overlay.className = 'cyber-modal-overlay';
    overlay.id = `cyber-modal-${challengeId}`;
    overlay.innerHTML = `
        <div class="cyber-modal">
            <h2>Is this safe or a scam?</h2>
            
            <div class="scenario-card">
                <div class="scenario-header">
                    <strong>${scenario.title}</strong>
                </div>
                <div class="scenario-sender">
                    <div class="sender-avatar">
                        <i class="bi bi-person-circle"></i>
                    </div>
                    <div class="sender-info">
                        <strong>${scenario.sender}</strong><br>
                        <span class="sender-email">From: ${scenario.email}<br>To: you@mail.com</span>
                    </div>
                </div>
                <div class="scenario-content">
                    <p>${scenario.content.replace(/\n/g, '<br>')}</p>
                    ${buttonHtml}
                </div>
                <div class="scenario-footer">
                    <em>${scenario.footer.replace(/\n/g, '<br>')}</em>
                </div>
            </div>
            
            <div class="cyber-buttons">
                <button class="cyber-btn safe" onclick="submitCyberAnswer('safe', '${challengeId}', ${scenarioId}, this)">
                    <i class="bi bi-hand-thumbs-up"></i> Safe
                </button>
                <button class="cyber-btn scam" onclick="submitCyberAnswer('scam', '${challengeId}', ${scenarioId}, this)">
                    <i class="bi bi-hand-thumbs-down"></i> Scam
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.remove();
        }
    });
}

/**
 * Show waiting modal for a challenge the user has already answered
 */
function showWaitingModal(challengeId, scenarioId) {
    const partnerName = document.getElementById('chat-contact-name')?.textContent || 'Partner';

    const overlay = document.createElement('div');
    overlay.className = 'cyber-modal-overlay';
    overlay.id = `cyber-modal-${challengeId}`;
    overlay.innerHTML = `
        <div class="cyber-modal">
            <h2>Your response has been submitted.</h2>
            <div class="participant-list">
                <div class="participant-item">
                    <div class="participant-avatar">
                        <i class="bi bi-person-circle"></i>
                    </div>
                    <div class="participant-info">
                        <strong>You</strong>
                        <span class="status-completed">Completed challenge</span>
                    </div>
                </div>
                <div class="participant-item" id="partner-status-${challengeId}">
                    <div class="participant-avatar">
                        <i class="bi bi-person-circle"></i>
                    </div>
                    <div class="participant-info">
                        <strong>${partnerName}</strong>
                        <span class="status-waiting">Awaiting response...</span>
                    </div>
                </div>
            </div>
            <button class="cyber-btn close" onclick="this.closest('.cyber-modal-overlay').remove()">
                Go back
            </button>
        </div>
    `;

    document.body.appendChild(overlay);

    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.remove();
        }
    });
}

// Track current challenge state
let currentChallengeState = {};

/**
 * Submit cyber challenge answer to server
 * @param {string} answer - 'safe' or 'scam'
 * @param {number} challengeId - The challenge ID
 * @param {number} scenarioId - The scenario ID
 * @param {HTMLButtonElement} button - The clicked button
 */
function submitCyberAnswer(answer, challengeId, scenarioId, button) {
    const scenario = cyberScenarios.find(s => s.id === scenarioId);
    if (!scenario) return;

    // Store our answer locally
    currentChallengeState[challengeId] = {
        myAnswer: answer,
        scenarioId: scenarioId,
        correctAnswer: scenario.answer
    };

    // Emit to server
    socket.emit('submit_cyber_answer', {
        challenge_id: challengeId,
        user_id: CURRENT_USER_ID,
        answer: answer
    });

    // Replace entire modal content with waiting status
    const modal = button.closest('.cyber-modal');

    // Get partner name from current chat header
    const partnerName = document.getElementById('chat-contact-name')?.textContent || 'Partner';

    modal.innerHTML = `
        <h2>Your response has been submitted.</h2>
        <div class="participant-list">
            <div class="participant-item">
                <div class="participant-avatar">
                    <i class="bi bi-person-circle"></i>
                </div>
                <div class="participant-info">
                    <strong>You</strong>
                    <span class="status-completed">Completed challenge</span>
                </div>
            </div>
            <div class="participant-item" id="partner-status-${challengeId}">
                <div class="participant-avatar">
                    <i class="bi bi-person-circle"></i>
                </div>
                <div class="participant-info">
                    <strong>${partnerName}</strong>
                    <span class="status-waiting">Awaiting response...</span>
                </div>
            </div>
        </div>
        <button class="cyber-btn close" onclick="this.closest('.cyber-modal-overlay').remove()">
            Go back
        </button>
    `;
}

/**
 * Append a "Results are out!" card to the chat
 * @param {number} challengeId - The challenge ID
 * @param {number} scenarioId - The scenario ID
 */
function appendResultsCard(challengeId, scenarioId) {
    const resultsHtml = `
        <div class="cyber-results-card" data-challenge-id="${challengeId}" data-scenario-id="${scenarioId}">
            <h3>🎮 Cyber Challenge!</h3>
            <p>Results for the challenge are out!</p>
            <button class="btn-view" onclick="showResultsModal('${challengeId}')">View Results</button>
        </div>
    `;

    chatMessages.innerHTML += resultsHtml;
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Show the results modal with both users' outcomes
 * @param {number} challengeId - The challenge ID
 */
function showResultsModal(challengeId) {
    const state = currentChallengeState[challengeId];
    if (!state) {
        console.error('No state found for challenge', challengeId);
        return;
    }

    const scenario = state.scenario || cyberScenarios.find(s => s.id === state.scenarioId);
    const partnerName = document.getElementById('chat-contact-name')?.textContent || 'Partner';

    // Determine result state
    const myStatus = state.myCorrect ? 'Completed challenge successfully' : 'Failed challenge';
    const myStatusClass = state.myCorrect ? 'status-success' : 'status-failed';
    const partnerStatus = state.partnerCorrect ? 'Completed challenge successfully' : 'Failed challenge';
    const partnerStatusClass = state.partnerCorrect ? 'status-success' : 'status-failed';

    const headerText = state.bothCorrect ? 'Challenge complete!' : 'Challenge failed...';
    const rewardHtml = state.bothCorrect ? `
        <div class="reward-earned-section">
            <span>+</span>
            <img src="/static/images/credit.svg" class="credit-icon-small2" onerror="this.style.display='none'">
            <span>15</span>
        </div>
    ` : '';

    const buttonText = state.bothCorrect ? 'Go back' : 'See explanation';
    const buttonAction = state.bothCorrect
        ? `this.closest('.cyber-modal-overlay').remove()`
        : `showExplanationModal('${challengeId}', ${state.scenarioId || scenario?.id})`;

    const overlay = document.createElement('div');
    overlay.className = 'cyber-modal-overlay';
    overlay.innerHTML = `
        <div class="cyber-modal results-modal">
            <h2>${headerText}</h2>
            
            <div class="participant-list">
                <div class="participant-item">
                    <div class="participant-avatar">
                        <i class="bi bi-person-circle"></i>
                    </div>
                    <div class="participant-info">
                        <strong>You</strong>
                        <span class="${myStatusClass}">${myStatus}</span>
                    </div>
                </div>
                <div class="participant-item">
                    <div class="participant-avatar">
                        <i class="bi bi-person-circle"></i>
                    </div>
                    <div class="participant-info">
                        <strong>${partnerName}</strong>
                        <span class="${partnerStatusClass}">${partnerStatus}</span>
                    </div>
                </div>
            </div>
            
            <div class="results-footer">
                <button class="cyber-btn close" onclick="${buttonAction}">
                    ${buttonText}
                </button>
                ${rewardHtml}
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.remove();
        }
    });
}

/**
 * Show explanation modal for failed challenges
 * @param {number} challengeId - The challenge ID
 * @param {number} scenarioId - The scenario ID
 */
function showExplanationModal(challengeId, scenarioId) {
    // Close previous modal
    document.querySelector('.cyber-modal-overlay')?.remove();

    const scenario = cyberScenarios.find(s => s.id === scenarioId);
    if (!scenario) return;

    const buttonHtml = scenario.buttonText ?
        `<div class="fake-button">${scenario.buttonText}</div>` : '';

    // Create explanation text based on the scenario
    const explanationNote = scenario.answer === 'scam'
        ? '<div class="explanation-callout"><strong>Always check for sender e-mail address.</strong></div>'
        : '<div class="explanation-callout"><strong>This is a legitimate message.</strong></div>';

    const overlay = document.createElement('div');
    overlay.className = 'cyber-modal-overlay';
    overlay.innerHTML = `
        <div class="cyber-modal explanation-modal">
            <h2>Explanation</h2>
            
            <div class="scenario-card with-annotation">
                <div class="scenario-header">
                    <strong>${scenario.title}</strong>
                </div>
                <div class="scenario-sender">
                    <div class="sender-avatar">
                        <i class="bi bi-person-circle"></i>
                    </div>
                    <div class="sender-info">
                        <strong>${scenario.sender}</strong><br>
                        <span class="sender-email ${scenario.answer === 'scam' ? 'highlight-suspicious' : ''}">From: ${scenario.email}<br>To: you@mail.com</span>
                        ${scenario.answer === 'scam' ? '<span class="red-flag-note">Always check for sender e-mail address.</span>' : ''}
                    </div>
                </div>
                <div class="scenario-content">
                    <p>${scenario.content.replace(/\n/g, '<br>')}</p>
                    ${buttonHtml}
                </div>
                <div class="scenario-footer">
                    <em>${scenario.footer.replace(/\n/g, '<br>')}</em>
                </div>
            </div>
            
            <button class="cyber-btn close" onclick="this.closest('.cyber-modal-overlay').remove()">
                Got it
            </button>
        </div>
    `;

    document.body.appendChild(overlay);

    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.remove();
        }
    });
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
                ${contact.unreadCount > 0 ? `<span class="unread-badge">${contact.unreadCount > 9 ? '9+' : contact.unreadCount}</span>` : ''}
            `;

            // Add click handler
            li.addEventListener('click', () => {
                switchContact(contact.id, contact.name, contact.status);
            });

            contactList.appendChild(li);
        });

        // Auto-select the first contact if none selected
        if (contacts.length > 0 && !currentContactId) {
            const firstContact = contacts[0];
            currentContactId = firstContact.id;

            // Mark first contact as active in UI
            const firstItem = document.querySelector(`[data-contact-id="${firstContact.id}"]`);
            if (firstItem) {
                firstItem.classList.add('active');
            }

            // Update header
            chatContactName.textContent = firstContact.name;
            chatContactStatus.textContent = firstContact.status;
            chatContactStatus.style.color = firstContact.status === 'Active now' ? '#22c55e' : '#888';

            // Join the chat room and load messages
            socket.emit('join_chat', { user_id: CURRENT_USER_ID, contact_id: firstContact.id });
            loadMessages(firstContact.id);

            // Mark messages as read and clear badge
            socket.emit('mark_read', { user_id: CURRENT_USER_ID, sender_id: firstContact.id });
            clearUnreadBadge(firstContact.id);
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

    // Clear unread badge for this contact and mark messages as read
    clearUnreadBadge(contactId);
    socket.emit('mark_read', { user_id: CURRENT_USER_ID, sender_id: contactId });

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
// Store the selected file
let selectedImageFile = null;

/**
 * Send a new message using Socket.IO
 */
async function sendMessage() {
    const text = messageInput.value.trim();

    // Check for !cyber command (Dev tool for testing scenarios)
    if (text.toLowerCase() === '!cyber') {
        // Determine a valid random scenario
        const randomScenario = typeof cyberScenarios !== 'undefined' && cyberScenarios.length > 0
            ? cyberScenarios[Math.floor(Math.random() * cyberScenarios.length)]
            : { id: 1 }; // Fallback

        socket.emit('send_message', {
            sender_id: CURRENT_USER_ID,
            receiver_id: currentContactId,
            content: text,
            is_cyber_challenge: true,
            scenario_id: randomScenario.id
        });
        messageInput.value = '';
        return;
    }

    if (!text && !selectedImageFile) return;
    if (!currentContactId) return;

    let imageUrl = null;

    // Upload image if selected
    if (selectedImageFile) {
        // Show uploading state
        const sendBtn = document.getElementById('send-btn');
        const originalIcon = sendBtn.innerHTML;
        sendBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
        sendBtn.disabled = true;

        try {
            const formData = new FormData();
            formData.append('file', selectedImageFile);

            const response = await fetch('/social/api/upload_image', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('Upload failed');

            const data = await response.json();
            imageUrl = data.url;

        } catch (error) {
            console.error('Error uploading image:', error);
            alert('Failed to upload image. Please try again.');
            sendBtn.innerHTML = originalIcon;
            sendBtn.disabled = false;
            return;
        } finally {
            sendBtn.innerHTML = originalIcon;
            sendBtn.disabled = false;
        }
    }

    const payload = {
        sender_id: CURRENT_USER_ID,
        receiver_id: currentContactId,
        content: text,
        image_url: imageUrl
    };

    socket.emit('send_message', payload);

    messageInput.value = '';

    // Clear image selection
    selectedImageFile = null;
    document.getElementById('image-preview-container').style.display = 'none';
    document.getElementById('image-preview').src = '';
    document.getElementById('image-input').value = ''; // Reset file input
}

// --- Image Upload Event Listeners ---
document.addEventListener('DOMContentLoaded', () => {
    const clipBtn = document.getElementById('clip-btn');
    const imageInput = document.getElementById('image-input');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const imagePreview = document.getElementById('image-preview');
    const removeImageBtn = document.getElementById('remove-image-btn');

    if (clipBtn && imageInput) {
        clipBtn.addEventListener('click', () => {
            imageInput.click();
        });

        imageInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                selectedImageFile = e.target.files[0];

                // Show preview
                const reader = new FileReader();
                reader.onload = (e) => {
                    imagePreview.src = e.target.result;
                    imagePreviewContainer.style.display = 'flex';
                };
                reader.readAsDataURL(selectedImageFile);
            }
        });

        removeImageBtn.addEventListener('click', () => {
            selectedImageFile = null;
            imageInput.value = '';
            imagePreviewContainer.style.display = 'none';
            imagePreview.src = '';
        });
    }
});

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
// --- Emoji Picker Logic ---
document.addEventListener('DOMContentLoaded', () => {
    const emojiBtn = document.getElementById('emoji-btn');
    const emojiPicker = document.getElementById('emoji-picker');
    const messageInput = document.getElementById('message-input');
    const emojiGrid = document.querySelector('.emoji-grid');

    if (emojiBtn && emojiPicker && messageInput && emojiGrid) {
        // Toggle visibility on button click
        emojiBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            emojiPicker.style.display = emojiPicker.style.display === 'block' ? 'none' : 'block';
        });

        // Hide when clicking outside
        document.addEventListener('click', (e) => {
            if (!emojiPicker.contains(e.target) && e.target !== emojiBtn) {
                emojiPicker.style.display = 'none';
            }
        });

        // Use event delegation for emoji clicks
        emojiGrid.addEventListener('click', (e) => {
            if (e.target.tagName === 'SPAN') {
                const emoji = e.target.textContent;

                // Insert emoji at cursor position or end
                const start = messageInput.selectionStart;
                const end = messageInput.selectionEnd;
                const text = messageInput.value;
                const before = text.substring(0, start);
                const after = text.substring(end, text.length);

                messageInput.value = before + emoji + after;

                // Move cursor to after emoji
                const newPos = start + emoji.length;
                messageInput.setSelectionRange(newPos, newPos);
                messageInput.focus();

                // Optional: Close picker after selection
                // emojiPicker.style.display = 'none';
            }
        });
    }
});

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
        // Check if this is a cyber challenge
        if (data.is_cyber_challenge || data.text === '!cyber') {
            appendCyberChallenge(data.id, data.challenge_id, data.scenario_id);
        } else {
            appendMessage({
                id: data.id,
                type: messageType,
                text: data.text
            });
        }
    } else if (messageType === 'received') {
        // Message from a different contact - increment unread count
        unreadCounts[otherUserId] = (unreadCounts[otherUserId] || 0) + 1;
        updateUnreadBadge(otherUserId);
    }

    // Always update the contact preview
    const previewText = data.is_cyber_challenge ? '🎮 Cyber Challenge!' : data.text;
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

/**
 * When both users have answered the cyber challenge - show results
 */
socket.on('cyber_challenge_complete', (data) => {
    console.log('[Socket.IO] Cyber challenge complete:', data);

    // Store the results
    const challengeId = data.challenge_id;
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
 * @param {number} challengeId - The challenge ID from server
 * @param {number} scenarioId - The scenario ID
 */
function showCyberChallengeModal(challengeId, scenarioId) {
    const scenario = cyberScenarios.find(s => s.id === scenarioId);
    if (!scenario) return;

    // Check if user has already answered this challenge
    const existingState = currentChallengeState[challengeId];
    if (existingState && existingState.myAnswer) {
        // User already answered - show waiting modal or results
        showWaitingModal(challengeId, scenarioId);
        return;
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
                <button class="cyber-btn safe" onclick="submitCyberAnswer('safe', ${challengeId}, ${scenarioId}, this)">
                    <i class="bi bi-hand-thumbs-up"></i> Safe
                </button>
                <button class="cyber-btn scam" onclick="submitCyberAnswer('scam', ${challengeId}, ${scenarioId}, this)">
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
            <button class="btn-view" onclick="showResultsModal(${challengeId})">View Results</button>
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
        : `showExplanationModal(${challengeId}, ${state.scenarioId || scenario?.id})`;

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

            // Set the first contact as current if we don't have one set
            if (index === 0 && !currentContactId) {
                currentContactId = contact.id;
            }
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
            fetch(`/social/api/messages/${firstContact.id}/read`, { method: 'POST' });
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
    fetch(`/social/api/messages/${contactId}/read`, { method: 'POST' });

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

    // Check for !cyber command
    if (text.toLowerCase() === '!cyber') {
        // Pick a random scenario and send it with the challenge
        const randomScenario = cyberScenarios[Math.floor(Math.random() * cyberScenarios.length)];

        // Send cyber challenge as a special message type
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

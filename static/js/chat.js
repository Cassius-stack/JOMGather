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
const micBtn = document.getElementById('mic-btn');

// Voice Recording Elements
const voiceRecordingContainer = document.getElementById('voice-recording-container');
const voiceTimer = document.getElementById('voice-timer');
const voiceDeleteBtn = document.getElementById('voice-delete-btn');

// Voice Recording State
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let recordingStartTime = null;
let timerInterval = null;

// Track the date of the last rendered message to inject separators
let lastMessageDateStr = null;


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
    console.log('[Socket.IO] ⚠️ Disconnected:', reason, 'Socket ID was:', socket.id);
});

socket.on('reconnect', (attemptNumber) => {
    console.log('[Socket.IO] 🔄 Reconnected after', attemptNumber, 'attempts. New Socket ID:', socket.id);
});

socket.on('reconnect_attempt', (attemptNumber) => {
    console.log('[Socket.IO] 🔄 Reconnecting... attempt', attemptNumber);
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

/**
 * Generic toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `custom-toast ${type}`;

    let icon = 'bi-info-circle';
    let bgColor = '#1e3a5f'; // Navy (primary)

    if (type === 'success') {
        icon = 'bi-check-circle';
        bgColor = '#22c55e';
    } else if (type === 'error') {
        icon = 'bi-exclamation-triangle';
        bgColor = '#dc3545';
    } else if (type === 'warning') {
        icon = 'bi-exclamation-circle';
        bgColor = '#f59e0b';
    }

    toast.innerHTML = `
        <i class="bi ${icon}"></i>
        <span>${message}</span>
    `;

    toast.style.cssText = `
        position: fixed;
        bottom: 100px;
        left: 50%;
        transform: translateX(-50%);
        background: ${bgColor};
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

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}


// Track processed message IDs to avoid duplicates
const processedMessageIds = new Set();

/**
 * When we receive a new message (real-time!)
 * This is the magic - messages appear instantly without refresh
 */
socket.on('new_message', (data) => {
    console.log('[Socket.IO] New message received:', data);

    // Normalize data (backend might use 'text' or 'content')
    const messageContent = data.text || data.content || '';
    const senderId = String(data.sender_id || data.senderId);
    const receiverId = String(data.receiver_id || data.receiverId);
    const msgId = data.id || data.message_id;

    console.log(`[Socket.IO] Processing message ${msgId} from ${senderId} to ${receiverId}. Current UI Contact: ${currentContactId}`);

    // Security/Filtering: Only process if I am the sender or receiver
    const isForMe = senderId === String(CURRENT_USER_ID) || receiverId === String(CURRENT_USER_ID);
    if (!isForMe) {
        console.log('[Socket.IO] Skipping message: Not for me');
        return;
    }

    // Mark as read if relevant
    if (receiverId === String(CURRENT_USER_ID) && senderId === String(currentContactId)) {
        socket.emit('mark_read', { user_id: CURRENT_USER_ID, sender_id: currentContactId });
    }

    // Prevent duplicate processing
    if (processedMessageIds.has(msgId)) return;
    processedMessageIds.add(msgId);

    // Determine roles for UI
    const messageType = senderId === String(CURRENT_USER_ID) ? 'sent' : 'received';
    const otherUserId = senderId === String(CURRENT_USER_ID) ? receiverId : senderId;

    // Robust Challenge Detection
    const isCyber = data.is_cyber_challenge ||
        (messageContent.trim().toLowerCase() === '!cyber') ||
        data.challenge_id ||
        data.challengeId;

    console.log(`[Socket.IO] isCyber detected: ${isCyber}. content: "${messageContent}"`);

    // Visual Alert for automated challenges
    if (isCyber && (data.is_broadcast || data.isBroadcast) && messageType === 'received') {
        console.log('[Socket.IO] Displaying Toast for Cyber Challenge');
        if (typeof showToast === 'function') {
            showToast('🎮 New Daily Cyber Challenge received!', 'info');
        }
    }

    // Update Chat View if open
    if (String(otherUserId) === String(currentContactId)) {
        if (isCyber) {
            console.log(`[Socket.IO] Auto-reloading messages for contact ${currentContactId}`);
            setTimeout(() => {
                loadMessages(currentContactId);
            }, 500);
        } else {
            appendMessage({
                id: msgId,
                type: messageType,
                text: messageContent,
                image_url: data.image_url || data.imageUrl,
                sent_at: data.sent_at || data.sentAt
            });
        }
    } else if (messageType === 'received') {
        // Increment unread count for other contacts
        unreadCounts[otherUserId] = (unreadCounts[otherUserId] || 0) + 1;
        updateUnreadBadge(otherUserId);
    }

    // Always update sidebar
    let previewText = messageContent;
    if (isCyber) {
        previewText = '🎮 Cyber Challenge!';
    } else if (!messageContent && (data.image_url || data.imageUrl)) {
        previewText = '📷 Photo';
    } else if (messageContent.startsWith('{')) {
        try {
            const parsed = JSON.parse(messageContent);
            if (parsed.type === 'call') {
                previewText = parsed.call_type === 'video' ? '📹 Video call' : '📞 Voice call';
            }
        } catch (e) { }
    }

    console.log(`[Socket.IO] Sidebar update for ${otherUserId}: ${previewText}`);
    updateContactPreview(otherUserId, previewText, messageType, data.sent_at || data.sentAt);

    // EXCLUSION: Don't move the contact to the top for cyber challenges
    // This allows them to "appear" in the sidebar without overtaking human chats
    if (!isCyber) {
        moveContactToTop(otherUserId);
    }
});

/**
 * Force Refresh Event (Fallback for automated challenges)
 */
socket.on('FORCE_CHAT_REFRESH', (data) => {
    console.log('[Socket.IO] FORCE_CHAT_REFRESH received:', data);

    // Check if it involves me
    const isForMe = String(data.target_id) === String(CURRENT_USER_ID) ||
        String(data.sender_id) === String(CURRENT_USER_ID);

    if (isForMe) {
        const otherId = String(data.target_id) === String(CURRENT_USER_ID) ? String(data.sender_id) : String(data.target_id);

        // If this contact is currently open, reload messages
        if (otherId === String(currentContactId)) {
            console.log('[Socket.IO] Force refreshing current chat...');
            loadMessages(currentContactId);
        }
    }
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
        contactItem.dataset.contactStatus = 'Active';
        if (data.user_id === currentContactId) {
            chatContactStatus.textContent = 'Active';
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
 * Receive reaction updates from the other user in real-time
 */
socket.on('reaction_update', (data) => {
    console.log('[Socket.IO] Reaction update:', data);
    const messageDiv = document.querySelector(`[data-message-id="${data.message_id}"]`);
    if (!messageDiv) return;

    let reactionsDiv = messageDiv.querySelector('.msg-reactions-chat');

    if (data.action === 'add') {
        // Create reactions container if needed
        if (!reactionsDiv) {
            reactionsDiv = document.createElement('div');
            reactionsDiv.className = 'msg-reactions-chat';
            messageDiv.querySelector('.bubble').after(reactionsDiv);
        }

        let badge = reactionsDiv.querySelector(`[data-emoji="${data.emoji}"]`);
        if (badge) {
            // Update existing badge
            let reactors = JSON.parse(badge.dataset.reactors || '[]');
            const senderId = String(data.from_user_id);
            if (!reactors.includes(senderId)) {
                reactors.push(senderId);
                badge.dataset.reactors = JSON.stringify(reactors);
                badge.dataset.count = reactors.length;
                badge.textContent = `${data.emoji} ${reactors.length}`;
            }
        } else {
            // Create new badge
            badge = document.createElement('span');
            badge.className = 'reaction-badge-chat';
            badge.dataset.emoji = data.emoji;
            badge.dataset.count = 1;
            badge.dataset.reactors = JSON.stringify([String(data.from_user_id)]);
            badge.textContent = `${data.emoji} 1`;
            badge.onclick = () => addReactionToMessage(data.message_id, data.emoji, badge);
            reactionsDiv.appendChild(badge);
        }
    } else if (data.action === 'remove') {
        if (!reactionsDiv) return;
        let badge = reactionsDiv.querySelector(`[data-emoji="${data.emoji}"]`);
        if (!badge) return;

        let reactors = JSON.parse(badge.dataset.reactors || '[]');
        const senderId = String(data.from_user_id);
        reactors = reactors.filter(id => id !== senderId);

        if (reactors.length === 0) {
            badge.remove();
            if (reactionsDiv.children.length === 0) {
                reactionsDiv.remove();
            }
        } else {
            badge.dataset.reactors = JSON.stringify(reactors);
            badge.dataset.count = reactors.length;
            badge.textContent = `${data.emoji} ${reactors.length}`;
        }
    }
});

/**
 * Update inbox preview after a message is deleted
 */
function updateInboxAfterDelete(senderId, receiverId) {
    const otherUserId = senderId === CURRENT_USER_ID ? receiverId : senderId;

    // Only update if viewing this contact's chat
    if (String(otherUserId) === String(currentContactId)) {
        const remainingMessages = document.querySelectorAll('#chat-messages .message');
        if (remainingMessages.length > 0) {
            const lastMessage = remainingMessages[remainingMessages.length - 1];
            if (lastMessage) {
                // Determine Text
                let text = '';
                const textEl = lastMessage.querySelector('.message-text');
                if (textEl) {
                    text = textEl.textContent;
                } else if (lastMessage.querySelector('.voice-message-player')) {
                    text = 'Voice message';
                } else if (lastMessage.querySelector('.call-card')) {
                    text = 'Call record';
                } else {
                    text = 'Photo attachment';
                }

                const isSent = lastMessage.classList.contains('sent');
                const timestamp = lastMessage.dataset.sentAt;

                updateContactPreview(otherUserId, text, isSent ? 'sent' : 'received', timestamp);
            }
        } else {
            // Truly empty chat
            updateContactPreview(otherUserId, 'No messages yet', '', null);

            // Explicitly clear sidebar timestamp if needed (already handled by null in updateContactPreview)
            const contactItem = document.querySelector(`[data-contact-id="${otherUserId}"]`);
            if (contactItem) {
                const timeEl = contactItem.querySelector('.timestamp');
                if (timeEl) timeEl.textContent = '';
            }
        }
    }
}

// ============================================
// HELPER FUNCTIONS
// ============================================

/**
 * Generate HTML for a single message
 */
function getMessageHtml(msg) {
    if (msg.type === 'timestamp') {
        return `<div class="chat-date-separator"><span>${msg.text}</span></div>`;
    }

    if (msg.is_cyber_challenge || msg.type === 'cyber-challenge') {
        const scenario = cyberScenarios[Math.floor(Math.random() * cyberScenarios.length)];
        const effectiveChallengeId = msg.challenge_id || `msg_${msg.id}`;
        const effectiveScenarioId = msg.scenario_id || scenario.id;
        return `
            <div class="cyber-challenge-card" data-message-id="${msg.id || ''}" data-challenge-id="${effectiveChallengeId}" data-scenario-id="${effectiveScenarioId}" id="cyber-card-${effectiveChallengeId}">
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
    }

    // Check if this is a call or voice message
    let callData = null;
    let voiceData = null;
    try {
        if (msg.text && msg.text.startsWith('{')) {
            const parsed = JSON.parse(msg.text);
            if (parsed.type === 'call') {
                callData = parsed;
            } else if (parsed.type === 'voice') {
                voiceData = parsed;
            }
        }
    } catch (e) {
        // Not a JSON message, treat as regular text
    }

    const isSent = msg.type === 'sent';
    const showEdit = !msg.image_url && !voiceData && !callData;
    const actionsHtml = `
        <div class="message-actions">
            ${isSent ? `
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

    // Detect edited status using zero-width space marker
    const isEdited = msg.text && msg.text.endsWith('\u200b');
    const editedIndicator = isEdited ? '<span class="edited-indicator">(edited)</span>' : '';

    // Image HTML
    const imageHtml = msg.image_url ? `
        <div class="message-image">
            <img src="${msg.image_url}" alt="Attachment" onclick="window.open(this.src, '_blank')">
        </div>
    ` : '';

    let contentHtml = '';
    if (callData) {
        const isVideo = callData.call_type === 'video';
        const isMissed = callData.status === 'missed';
        const isFailed = callData.status === 'failed';
        const icon = isVideo
            ? (isMissed || isFailed ? 'bi-camera-video-off' : 'bi-camera-video')
            : (isMissed || isFailed ? 'bi-telephone-x' : 'bi-telephone');

        let title = isMissed
            ? `Missed ${callData.call_type} call`
            : `${callData.call_type.charAt(0).toUpperCase() + callData.call_type.slice(1)} call`;

        if (isFailed) {
            title = `Failed ${callData.call_type} call`;
        }

        let subtitle = '';
        if (isMissed) {
            subtitle = 'Tap to call back';
        } else if (isFailed) {
            subtitle = 'Could not establish connection';
        } else if (callData.duration > 0) {
            const mins = Math.floor(callData.duration / 60);
            const secs = callData.duration % 60;
            subtitle = mins > 0 ? `${mins} min ${secs} sec` : `${secs} sec`;
        }

        const safeName = (typeof currentContactName !== 'undefined' ? currentContactName : '').replace(/'/g, "\\'");
        const contactId = typeof currentContactId !== 'undefined' ? currentContactId : 0;

        contentHtml = `
            <div class="call-card ${isMissed ? 'missed' : 'completed'}" ${isMissed ? `onclick="startCall(${contactId}, '${safeName}', '${callData.call_type}')"` : ''}>
                <div class="call-icon ${isMissed ? 'missed' : ''}">
                    <i class="bi ${icon}"></i>
                </div>
                <div class="call-info">
                    <div class="call-title">${title}</div>
                    <div class="call-subtitle">${subtitle}</div>
                </div>
            </div>
        `;
    } else if (voiceData) {
        const durationDisplay = voiceData.duration ? (typeof voiceData.duration === 'string' ? voiceData.duration : formatDuration(voiceData.duration)) : '0:00';
        contentHtml = `
            <div class="voice-message-player">
                <button class="voice-play-btn" onclick="toggleVoicePlayback(this, '${voiceData.audio_url}')">
                    <i class="bi bi-play-fill"></i>
                </button>
                <div class="voice-progress-container">
                    <div class="voice-progress-bar" onclick="seekVoice(event, this)">
                        <div class="voice-progress-fill"></div>
                    </div>
                    <div class="voice-time">0:00 / ${durationDisplay}</div>
                </div>
                <audio src="${voiceData.audio_url}" ontimeupdate="updateVoiceProgress(this)" onended="resetVoicePlayer(this)"></audio>
            </div>
        `;
    } else {
        // Remove zero-width space for clean display in message text
        let displayText = msg.text || '';
        if (displayText.endsWith('\u200b')) {
            displayText = displayText.slice(0, -1);
        }

        // Special handling for Slice of Life invites sent by me
        // We disable the "Respond" button for the sender to prevent confusion/errors
        if (isSent && displayText.includes('Slice of Life Invite')) {
            displayText = displayText.replace(
                /<a href="[^"]*".*?>View & Respond<\/a>/,
                '<span style="display: block; width: 100%; background: #cbd5e1; color: #64748b; text-align: center; padding: 10px 0; border-radius: 8px; font-weight: 600; font-size: 0.9rem; cursor: not-allowed;">Invite Sent</span>'
            );
        }

        contentHtml = `<span class="message-text">${displayText}</span>`;
    }

    return `
        <div class="message ${msg.type} ${callData ? 'call-message' : ''}" data-message-id="${msg.id || ''}" data-sent-at="${msg.sent_at || ''}">
            <div class="message-content">
                <div class="bubble-with-actions">
                    <div class="bubble ${voiceData ? 'voice-message' : ''}">
                        ${imageHtml}
                        <div class="message-body">
                            ${contentHtml}
                            <div class="message-metadata">
                                ${editedIndicator}
                                <span class="message-time">${formatMessageTime(msg.sent_at || new Date())}</span>
                                ${isSent ? `<span class="message-tick ${msg.read ? 'read' : ''}"><i class="bi bi-check${msg.read ? '-all' : ''}"></i></span>` : ''}
                            </div>
                        </div>
                    </div>
                    ${actionsHtml}
                </div>
                <div class="msg-reactions-chat">${getReactionsHtml(msg.id, msg.reactions)}</div>
            </div>
        </div>
    `;
}

// Append a single message to the chat (for real-time updates)
function appendMessage(msg) {
    if (!chatMessages) return;

    // Check for day change for real-time messages
    const date = parseTimestamp(msg.sent_at || new Date());
    if (date) {
        const currentDateStr = date.toDateString();
        if (currentDateStr !== lastMessageDateStr) {
            const separatorHtml = `<div class="chat-date-separator"><span>${formatDateSeparator(msg.sent_at)}</span></div>`;
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = separatorHtml;
            chatMessages.appendChild(tempDiv.firstChild);
            lastMessageDateStr = currentDateStr;
        }
    }

    const messageHtml = getMessageHtml(msg);
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = messageHtml.trim();
    const messageElement = tempDiv.firstChild;

    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Async check for challenges
    if (msg.type === 'cyber-challenge' || msg.text === '!cyber') {
        const effectiveChallengeId = msg.challenge_id || `msg_${msg.id}`;
        const effectiveScenarioId = msg.scenario_id || (cyberScenarios[0].id);
        checkAndUpdateChallengeCard(effectiveChallengeId, effectiveScenarioId);
    }
}

/**
 * Format message text for the contact preview (sidebar)
 */
function getPreviewText(text) {
    if (!text) return 'No messages yet';

    // Handle Slice of Life HTML cards in preview
    if (text.includes('Slice of Life Invite')) {
        return '🎨 Slice of Life Invite';
    }

    if (text === '!cyber' || text === '🎮 Cyber Challenge!') {
        return '🎮 Cyber Challenge!';
    }

    try {
        if (text.startsWith('{')) {
            const parsed = JSON.parse(text);
            if (parsed.type === 'voice') {
                return '🎙️ Voice message';
            } else if (parsed.type === 'call') {
                return parsed.status === 'missed' ? '📞 Missed call' : '📞 Call';
            }
        }
    } catch (e) {
        // Not JSON, return as-is
    }

    return text;
}

/**
 * Parse a timestamp into a Date object, handling UTC formats robustly
 */
function parseTimestamp(timestamp) {
    if (!timestamp) return null;
    if (timestamp instanceof Date) return timestamp;

    let dateStr = String(timestamp).trim();

    // If it's a standard ISO format but missing a timezone, assume UTC
    if (dateStr.includes('T') && !dateStr.includes('Z') && !dateStr.includes('+')) {
        dateStr += 'Z';
    } else if (!dateStr.includes('T') && dateStr.includes(' ')) {
        // Convert "YYYY-MM-DD HH:mm:ss" to "YYYY-MM-DDTHH:mm:ss"
        dateStr = dateStr.replace(' ', 'T');
        if (!dateStr.includes('Z') && !dateStr.includes('+')) {
            dateStr += 'Z';
        }
    }

    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? null : date;
}

/**
 * Format timestamp for the sidebar (e.g., 08:20 PM)
 */
function formatSidebarTime(isoString) {
    const date = parseTimestamp(isoString);
    if (!date) return '';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });
}

/**
 * Format date separator (e.g., Today, Yesterday, or 11 December) + Time
 */
function formatDateSeparator(timestamp) {
    const date = parseTimestamp(timestamp);
    if (!date) return '';

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const targetDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());

    let datePart = '';
    if (targetDate.getTime() === today.getTime()) {
        datePart = 'Today';
    } else if (targetDate.getTime() === yesterday.getTime()) {
        datePart = 'Yesterday';
    } else {
        // e.g., "11 December"
        datePart = date.toLocaleDateString([], { day: 'numeric', month: 'long' });
    }

    const timePart = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });
    return `${datePart}, ${timePart}`;
}

/**
 * Update the preview text for a contact in the sidebar
 */
function updateContactPreview(contactId, text, type, timestamp = null) {
    const contactItem = document.querySelector(`[data-contact-id="${contactId}"]`);
    if (contactItem) {
        // Update Preview Text
        const preview = contactItem.querySelector('.preview');
        if (preview) {
            const prefix = type === 'sent' ? 'You: ' : '';
            const displayMessage = getPreviewText(text);
            preview.textContent = `${prefix}${displayMessage.substring(0, 25)}${displayMessage.length > 25 ? '...' : ''}`;
        }

        // Update Timestamp (if provided and not a cyber challenge)
        if (timestamp && text !== '!cyber' && text !== '🎮 Cyber Challenge!') {
            const timeEl = contactItem.querySelector('.timestamp');
            if (timeEl) {
                timeEl.textContent = formatSidebarTime(timestamp);
            }
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
    const previewRow = contactItem.querySelector('.preview-row');
    if (!previewRow) return;

    let badge = previewRow.querySelector('.unread-badge');

    if (count > 0) {
        // Create badge if it doesn't exist
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'unread-badge';
            previewRow.appendChild(badge);
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
    console.log('[Chat] Rendering', messages.length, 'messages');

    // Reset date tracking for a fresh render
    lastMessageDateStr = null;

    let fullHtml = '';
    const challengesToUpdate = [];

    messages.forEach((msg) => {
        try {
            // Check for day change
            const date = parseTimestamp(msg.sent_at);
            if (date) {
                const currentDateStr = date.toDateString();
                if (currentDateStr !== lastMessageDateStr) {
                    fullHtml += `<div class="chat-date-separator"><span>${formatDateSeparator(msg.sent_at)}</span></div>`;
                    lastMessageDateStr = currentDateStr;
                }
            }

            fullHtml += getMessageHtml(msg);

            // Collect challenges for post-render update
            if (msg.type === 'cyber-challenge' || msg.text === '!cyber') {
                challengesToUpdate.push({
                    id: msg.challenge_id || `msg_${msg.id}`,
                    scenarioId: msg.scenario_id
                });
            }
        } catch (e) {
            console.error('[Chat] Error generating message HTML', msg, e);
        }
    });

    chatMessages.innerHTML = fullHtml;

    // After setting HTML, trigger async challenge checks
    challengesToUpdate.forEach(c => {
        checkAndUpdateChallengeCard(c.id, c.scenarioId);
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
    const textElement = bubble.querySelector('.message-text');
    let currentText = textElement ? textElement.textContent : '';

    // Remove zero-width space marker if present
    if (currentText.endsWith('\u200b')) {
        currentText = currentText.slice(0, -1);
    }
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
        showToast('Message cannot be empty', 'error');
        return;
    }

    // Emit edit event via Socket.IO
    // Append zero-width space as a marker for "edited" status persistence
    const markedText = newText + '\u200b';

    socket.emit('edit_message', {
        message_id: messageId,
        user_id: CURRENT_USER_ID,
        new_content: markedText
    });

    // Update UI immediately (optimistic update)
    const bubble = messageDiv.querySelector('.bubble');
    const textElement = bubble.querySelector('.message-text');
    if (textElement) {
        textElement.textContent = newText;
    }

    // Add edited indicator if not already there, aligned inline with metadata
    if (!bubble.querySelector('.edited-indicator')) {
        const metadata = bubble.querySelector('.message-metadata');
        if (metadata) {
            metadata.insertAdjacentHTML('afterbegin', '<span class="edited-indicator">(edited)</span>');
        }
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

    let messageText = '';
    const textElement = messageDiv.querySelector('.message-text');

    if (textElement) {
        messageText = textElement.textContent;
    } else if (messageDiv.querySelector('.voice-message-player')) {
        messageText = 'Voice message';
    } else if (messageDiv.querySelector('.call-card')) {
        messageText = 'Call record';
    } else {
        messageText = 'Photo attachment';
    }

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

/**
 * Generate HTML for reaction badges from a reactions object
 */
function getReactionsHtml(messageId, reactions) {
    if (!reactions || Object.keys(reactions).length === 0) return '';

    let html = '';
    const myUserId = String(CURRENT_USER_ID);

    for (const [emoji, reactors] of Object.entries(reactions)) {
        const reactorIds = reactors.map(id => String(id));
        const hasMyReaction = reactorIds.includes(myUserId);
        const count = reactorIds.length;

        html += `
            <span class="reaction-badge-chat ${hasMyReaction ? 'my-reaction' : ''}" 
                  data-emoji="${emoji}" 
                  data-count="${count}" 
                  data-reactors='${JSON.stringify(reactorIds)}'
                  onclick="addReactionToMessage('${messageId}', '${emoji}', this)">
                ${emoji} ${count}
            </span>
        `;
    }
    return html;
}

// ============================================
// REACTION FUNCTIONS
// ============================================

const chatEmojis = ['👍', '❤️', '🎉', '🔥', '⭐', '✨'];

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
 * Add or remove a reaction emoji on a message (toggle + real-time relay)
 */
function addReactionToMessage(messageId, emoji, button) {
    const picker = button.closest('.emoji-picker-chat');
    const messageDiv = document.querySelector(`[data-message-id="${messageId}"]`);

    if (!messageDiv) {
        if (picker) picker.remove();
        return;
    }

    // Check if reactions container exists
    let reactionsDiv = messageDiv.querySelector('.msg-reactions-chat');
    if (!reactionsDiv) {
        reactionsDiv = document.createElement('div');
        reactionsDiv.className = 'msg-reactions-chat';
        messageDiv.querySelector('.bubble').after(reactionsDiv);
    }

    // Check if this emoji already exists
    let badge = reactionsDiv.querySelector(`[data-emoji="${emoji}"]`);
    const myUserId = String(CURRENT_USER_ID);

    if (badge) {
        // Parse who has reacted
        let reactors = JSON.parse(badge.dataset.reactors || '[]');
        const alreadyReacted = reactors.includes(myUserId);

        if (alreadyReacted) {
            // UNREACT: remove my user from the reactors
            reactors = reactors.filter(id => id !== myUserId);
            if (reactors.length === 0) {
                badge.remove();
                // Clean up empty container
                if (reactionsDiv.children.length === 0) {
                    reactionsDiv.remove();
                }
            } else {
                badge.dataset.reactors = JSON.stringify(reactors);
                badge.dataset.count = reactors.length;
                badge.textContent = `${emoji} ${reactors.length}`;
                badge.classList.remove('my-reaction');
            }
            // Emit unreact to server
            socket.emit('react_message', {
                from_user_id: CURRENT_USER_ID,
                to_user_id: currentContactId,
                message_id: messageId,
                emoji: emoji,
                action: 'remove'
            });
        } else {
            // ADD my reaction to existing badge
            reactors.push(myUserId);
            badge.dataset.reactors = JSON.stringify(reactors);
            badge.dataset.count = reactors.length;
            badge.textContent = `${emoji} ${reactors.length}`;
            badge.classList.add('my-reaction');
            // Emit react to server
            socket.emit('react_message', {
                from_user_id: CURRENT_USER_ID,
                to_user_id: currentContactId,
                message_id: messageId,
                emoji: emoji,
                action: 'add'
            });
        }
    } else {
        // Add new reaction badge
        badge = document.createElement('span');
        badge.className = 'reaction-badge-chat my-reaction';
        badge.dataset.emoji = emoji;
        badge.dataset.count = 1;
        badge.dataset.reactors = JSON.stringify([myUserId]);
        badge.textContent = `${emoji} 1`;
        badge.onclick = () => addReactionToMessage(messageId, emoji, badge);
        reactionsDiv.appendChild(badge);
        // Emit react to server
        socket.emit('react_message', {
            from_user_id: CURRENT_USER_ID,
            to_user_id: currentContactId,
            message_id: messageId,
            emoji: emoji,
            action: 'add'
        });
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
        // Reset lastMessageDateStr when loading messages for a new contact
        lastMessageDateStr = null;

        const response = await fetch(`/social/api/messages/${contactId}?user=${CURRENT_USER_ID}`);

        // Check if response is OK
        if (!response.ok) {
            console.error('Messages API error:', response.status, response.statusText);
            renderMessages([]);
            return [];
        }

        const messages = await response.json();

        // Handle error responses from backend
        if (messages.error) {
            console.error('Messages API returned error:', messages.error);
            renderMessages([]);
            return [];
        }

        // Validate that messages is an array
        if (!Array.isArray(messages)) {
            console.error('Invalid messages response - expected array:', messages);
            renderMessages([]);
            return [];
        }

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

        // Check if response is OK
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const contacts = await response.json();

        // Handle error responses from backend
        if (contacts.error) {
            throw new Error(contacts.error);
        }

        // Validate that contacts is an array
        if (!Array.isArray(contacts)) {
            console.error('Invalid contacts response:', contacts);
            throw new Error('Invalid response format - expected array');
        }

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
            li.dataset.contactType = contact.type;
            li.dataset.contactPhoto = contact.profile_photo_url || '';

            const avatarHtml = contact.profile_photo_url
                ? `<div class="avatar" style="overflow:hidden;"><img src="${contact.profile_photo_url}" alt="${contact.name}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;"></div>`
                : `<div class="avatar" style="background:#e0f2fe;color:#1e3a5f;font-weight:700;font-size:1rem;display:flex;align-items:center;justify-content:center;">${contact.name.charAt(0).toUpperCase()}</div>`;

            li.innerHTML = `
                ${avatarHtml}
                <div class="contact-info">
                    <div class="name-row">
                        <span class="name">${contact.name}</span>
                        <span class="timestamp">${formatSidebarTime(contact.lastMessageTime)}</span>
                    </div>
                    <div class="preview-row">
                        <span class="preview">${getPreviewText(contact.lastMessage)}</span>
                        ${contact.unreadCount > 0 ? `<span class="unread-badge">${contact.unreadCount > 9 ? '9+' : contact.unreadCount}</span>` : ''}
                    </div>
                </div>
            `;

            // Add click handler
            li.addEventListener('click', () => {
                switchContact(contact.id, contact.name, contact.status);
            });

            contactList.appendChild(li);
        });

        // Auto-select a specific contact if requested via URL param (set in social_hub.html)
        if (window.autoOpenChatId) {
            const target = contacts.find(c => c.id === window.autoOpenChatId);
            if (target) {
                switchContact(target.id, target.name, target.status);
                // Clear it so it doesn't trigger on every re-load
                window.autoOpenChatId = null;
                return;
            }
        }

        // Auto-select the first contact if none selected
        if (contacts.length > 0 && !currentContactId) {
            const firstContact = contacts[0];
            currentContactId = firstContact.id;
            window.currentContactId = firstContact.id;
            window.currentContactName = firstContact.name;

            // Mark first contact as active in UI
            const firstItem = document.querySelector(`[data-contact-id="${firstContact.id}"]`);
            if (firstItem) {
                firstItem.classList.add('active');
            }

            // Update header
            chatContactName.textContent = firstContact.name;
            chatContactStatus.textContent = firstContact.status;
            chatContactStatus.style.color = firstContact.status === 'Active' ? '#22c55e' : '#888';
            updateHeaderAvatar(firstContact.profile_photo_url, firstContact.name);

            // Update role in header
            const roleSpan = document.getElementById('chat-contact-role');
            const separator = document.getElementById('chat-header-separator');
            if (roleSpan) {
                const type = firstContact.type || 'youth';
                roleSpan.textContent = type === 'youth' ? 'Youth' : (type.charAt(0).toUpperCase() + type.slice(1));
                roleSpan.style.display = 'inline';
                if (separator) separator.style.display = 'inline';
            }

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
 * Update the large avatar in the chat header.
 * Shows the photo if available, else an initial-letter circle.
 */
function updateHeaderAvatar(photoUrl, name) {
    const headerAvatar = document.getElementById('chat-header-avatar');
    if (!headerAvatar) return;
    if (photoUrl) {
        headerAvatar.innerHTML = `<img src="${photoUrl}" alt="${name}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
        headerAvatar.style.background = 'transparent';
        headerAvatar.style.overflow = 'hidden';
    } else {
        headerAvatar.innerHTML = `<span style="font-size:1.4rem;font-weight:700;color:#1e3a5f;">${(name || '?').charAt(0).toUpperCase()}</span>`;
        headerAvatar.style.background = '#e0f2fe';
        headerAvatar.style.display = 'flex';
        headerAvatar.style.alignItems = 'center';
        headerAvatar.style.justifyContent = 'center';
        headerAvatar.style.overflow = 'hidden';
    }
}

/**
 * Switch to a different contact
 */
function switchContact(contactId, contactName, contactStatus) {
    // Leave the old room
    socket.emit('leave_chat', { user_id: CURRENT_USER_ID, contact_id: currentContactId });

    currentContactId = contactId;

    // Store contact name globally for call cards
    window.currentContactId = contactId;
    window.currentContactName = contactName;

    // Join the new room
    socket.emit('join_chat', { user_id: CURRENT_USER_ID, contact_id: contactId });

    // Clear unread badge for this contact and mark messages as read
    clearUnreadBadge(contactId);
    socket.emit('mark_read', { user_id: CURRENT_USER_ID, sender_id: contactId });

    // Update header
    chatContactName.textContent = contactName;
    chatContactStatus.textContent = contactStatus || 'Active';
    const activeItemForPhoto = document.querySelector(`[data-contact-id="${contactId}"]`);
    updateHeaderAvatar(activeItemForPhoto ? activeItemForPhoto.dataset.contactPhoto : '', contactName);

    // Update role in header
    const activeItem = document.querySelector(`[data-contact-id="${contactId}"]`);
    const roleSpan = document.getElementById('chat-contact-role');
    const separator = document.getElementById('chat-header-separator');
    if (activeItem && roleSpan) {
        let type = activeItem.dataset.contactType || 'youth';
        roleSpan.textContent = type === 'youth' ? 'Youth' : (type.charAt(0).toUpperCase() + type.slice(1));
        roleSpan.style.display = 'inline';
        if (separator) separator.style.display = 'inline';
    }

    // Update status color
    if (contactStatus === "Active") {
        chatContactStatus.style.color = "#22c55e";
    } else {
        chatContactStatus.style.color = "#888";
    }

    // Update active state in contact list
    document.querySelectorAll('.contact-item').forEach(item => {
        item.classList.remove('active');
    });
    // activeItem is already defined above in the role update section
    if (activeItem) {
        activeItem.classList.add('active');
    }

    // Load messages from server
    loadMessages(contactId);

    // On mobile, show the chat window
    showChatView();
}

/**
 * Show chat view (for mobile)
 */
function showChatView() {
    const inboxPane = document.querySelector('.inbox-pane');
    const chatWindow = document.querySelector('.chat-window');

    if (inboxPane && chatWindow) {
        inboxPane.classList.add('hidden-mobile');
        chatWindow.classList.add('active-mobile');
    }
}

/**
 * Show contact list (for mobile back button)
 */
function showContactList() {
    const inboxPane = document.querySelector('.inbox-pane');
    const chatWindow = document.querySelector('.chat-window');

    if (inboxPane && chatWindow) {
        inboxPane.classList.remove('hidden-mobile');
        chatWindow.classList.remove('active-mobile');
    }
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
        const activeItem = document.querySelector(`[data-contact-id="${currentContactId}"]`);
        const contactType = activeItem ? activeItem.dataset.contactType : null;

        // Enforce restriction: Only Senior-Youth pairs
        const currentUserType = typeof CURRENT_USER_TYPE !== 'undefined' ? CURRENT_USER_TYPE : 'youth';
        const isSeniorYouthPair = (currentUserType === 'senior' && contactType === 'youth') ||
            (currentUserType === 'youth' && contactType === 'senior');

        if (isSeniorYouthPair) {
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
        } else {
            console.log('[Chat] !cyber blocked: same-role pair');
            // User requested to block it from being sent as a challenge.
            // We'll let it fall through and be sent as a regular message "!cyber"
            // Or we could silently absorb it. The user said "block it from being sent if it is sent from youth-to-youth/senior-to-senior".
            // I'll fall through so it's a normal message, and the backend will also block the challenge creation.
        }
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

    // Ensure button state is updated (return to mic if empty)
    toggleMicSendButton();
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
                const file = e.target.files[0];

                // Validate file type (frontend)
                if (!file.type.startsWith('image/')) {
                    showToast('Only image files are allowed as attachments.', 'error');
                    imageInput.value = ''; // Reset input
                    selectedImageFile = null;
                    return;
                }

                selectedImageFile = file;

                // Show preview
                const reader = new FileReader();
                reader.onload = (e) => {
                    imagePreview.src = e.target.result;
                    imagePreviewContainer.style.display = 'flex';
                };
                reader.readAsDataURL(selectedImageFile);

                // Switch voice bubble to send bubble
                toggleMicSendButton();
            }
        });

        removeImageBtn.addEventListener('click', () => {
            selectedImageFile = null;
            imageInput.value = '';
            imagePreviewContainer.style.display = 'none';
            imagePreview.src = '';
            toggleMicSendButton();
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
    sendBtn.addEventListener('click', () => {
        if (isRecording) {
            stopRecording();
        } else {
            sendMessage();
        }
    });

    // Enter key to send
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Typing indicator + mic/send button toggle
    messageInput.addEventListener('input', (e) => {
        handleTyping();
        toggleMicSendButton();
    });

    // Mic button - start recording
    if (micBtn) {
        micBtn.addEventListener('click', startRecording);
    }

    // Voice delete button - cancel recording
    if (voiceDeleteBtn) {
        voiceDeleteBtn.addEventListener('click', cancelRecording);
    }

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

    // Initialize mic/send button state
    toggleMicSendButton();
});

// ============================================
// VOICE RECORDING FUNCTIONS
// ============================================

/**
 * Toggle between mic and send button based on input state
 */
function toggleMicSendButton() {
    const hasText = messageInput.value.trim().length > 0;
    const hasImage = selectedImageFile !== null;

    if (hasText || hasImage || isRecording) {
        // Show send button
        if (micBtn) micBtn.style.display = 'none';
        if (sendBtn) sendBtn.style.display = 'flex';
    } else {
        // Show mic button
        if (micBtn) micBtn.style.display = 'flex';
        if (sendBtn) sendBtn.style.display = 'none';
    }
}

/**
 * Start voice recording
 */
async function startRecording() {
    if (!currentContactId) {
        showToast('Please select a contact first', 'warning');
        return;
    }

    try {
        // Request microphone permission
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        // Create MediaRecorder
        mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus'
        });

        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                audioChunks.push(e.data);
            }
        };

        mediaRecorder.onstop = () => {
            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());
        };

        // Start recording
        mediaRecorder.start(100); // Collect data every 100ms
        isRecording = true;
        recordingStartTime = Date.now();

        // Start timer
        timerInterval = setInterval(updateTimer, 1000);

        // Show recording UI
        showRecordingUI();

        console.log('[Voice] Recording started');

    } catch (error) {
        console.error('[Voice] Error starting recording:', error);
        if (error.name === 'NotAllowedError') {
            showToast('Microphone access denied. Please allow microphone access.', 'error');
        } else {
            showToast('Could not start recording. Please try again.', 'error');
        }
    }
}

/**
 * Stop recording and send voice message
 */
async function stopRecording() {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        console.log('[Voice] No active recording to stop');
        return;
    }

    // Stop the recorder
    mediaRecorder.stop();

    // Wait for data to be collected
    await new Promise(resolve => setTimeout(resolve, 200));

    // Create audio blob
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });

    // Get duration
    const duration = Math.floor((Date.now() - recordingStartTime) / 1000);

    // Hide recording UI first
    hideRecordingUI();

    // Send voice message
    await sendVoiceMessage(audioBlob, duration);

    // Reset state
    isRecording = false;
    mediaRecorder = null;
    audioChunks = [];
    recordingStartTime = null;
    clearInterval(timerInterval);
    timerInterval = null;

    // Update button state
    toggleMicSendButton();

    console.log('[Voice] Recording stopped, duration:', duration, 'seconds');
}

/**
 * Cancel recording without sending
 */
function cancelRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }

    // Reset state
    isRecording = false;
    mediaRecorder = null;
    audioChunks = [];
    recordingStartTime = null;
    clearInterval(timerInterval);
    timerInterval = null;

    // Hide recording UI
    hideRecordingUI();

    // Update button state
    toggleMicSendButton();

    console.log('[Voice] Recording cancelled');
}

/**
 * Send voice message to server
 */
async function sendVoiceMessage(audioBlob, duration) {
    try {
        // Show uploading state
        sendBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
        sendBtn.disabled = true;

        // Upload audio file
        const formData = new FormData();
        formData.append('file', audioBlob, 'voice_message.webm');

        const response = await fetch('/social/api/upload_audio', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Upload failed');

        const data = await response.json();
        const audioUrl = data.url;

        // Send message with audio URL via Socket.IO
        const voiceMessageContent = JSON.stringify({
            type: 'voice',
            audio_url: audioUrl,
            duration: duration
        });

        socket.emit('send_message', {
            sender_id: CURRENT_USER_ID,
            receiver_id: currentContactId,
            content: voiceMessageContent
        });

        console.log('[Voice] Voice message sent:', audioUrl);

    } catch (error) {
        console.error('[Voice] Error sending voice message:', error);
        showToast('Failed to send voice message. Please try again.', 'error');
    } finally {
        sendBtn.innerHTML = '<i class="bi bi-send"></i>';
        sendBtn.disabled = false;
    }
}

/**
 * Update recording timer display
 */
function updateTimer() {
    if (!recordingStartTime) return;

    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;

    voiceTimer.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

/**
 * Show recording UI
 */
function showRecordingUI() {
    const inputArea = document.querySelector('.input-area');
    inputArea.classList.add('recording');

    // Hide message input and actions
    messageInput.style.display = 'none';
    document.querySelector('.input-actions').style.display = 'none';

    // Show recording container
    voiceRecordingContainer.style.display = 'flex';
    voiceTimer.textContent = '0:00';

    // Show send button (for stopping recording)
    micBtn.style.display = 'none';
    sendBtn.style.display = 'flex';
}

/**
 * Hide recording UI and restore normal state
 */
function hideRecordingUI() {
    const inputArea = document.querySelector('.input-area');
    inputArea.classList.remove('recording');

    // Show message input and actions
    messageInput.style.display = '';
    document.querySelector('.input-actions').style.display = '';

    // Hide recording container
    voiceRecordingContainer.style.display = 'none';
}

// ============================================
// AUDIO PLAYBACK FUNCTIONS
// ============================================

/**
 * Toggle between play and pause for voice message
 */
function toggleVoicePlayback(button, audioUrl) {
    const player = button.closest('.voice-message-player');
    const audio = player.querySelector('audio');
    const icon = button.querySelector('i');

    // Stop any other playing audio
    document.querySelectorAll('audio').forEach(a => {
        if (a !== audio && !a.paused) {
            a.pause();
            const btn = a.parentElement.querySelector('.voice-play-btn i');
            if (btn) btn.className = 'bi bi-play-fill';
        }
    });

    if (audio.paused) {
        audio.play();
        icon.className = 'bi bi-pause-fill';
    } else {
        audio.pause();
        icon.className = 'bi bi-play-fill';
    }
}

/**
 * Update progress bar and time during playback
 */
function updateVoiceProgress(audio) {
    const player = audio.closest('.voice-message-player');
    const progressFill = player.querySelector('.voice-progress-fill');
    const durationText = player.querySelector('.voice-time');

    const percent = (audio.currentTime / audio.duration) * 100;
    progressFill.style.width = `${percent}%`;

    // Show current time / total duration
    if (!isNaN(audio.duration)) {
        durationText.textContent = `${formatDuration(audio.currentTime)} / ${formatDuration(audio.duration)}`;
    }
}

/**
 * Reset player UI when audio ends
 */
function resetVoicePlayer(audio) {
    const player = audio.closest('.voice-message-player');
    const icon = player.querySelector('.voice-play-btn i');
    const progressFill = player.querySelector('.voice-progress-fill');
    const durationText = player.querySelector('.voice-time');

    icon.className = 'bi bi-play-fill';
    progressFill.style.width = '0%';

    if (!isNaN(audio.duration)) {
        durationText.textContent = `0:00 / ${formatDuration(audio.duration)}`;
    }
}

/**
 * Seek to a specific position in the audio
 */
function seekVoice(event, progressBar) {
    const audio = progressBar.closest('.voice-message-player').querySelector('audio');
    const rect = progressBar.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const width = rect.width;
    const percent = x / width;

    if (!isNaN(audio.duration)) {
        audio.currentTime = percent * audio.duration;
    }
}

/**
 * Format timestamp to HH:mm AM/PM
 * Ensures that UTC strings from the server are converted to local browser time
 */
function formatMessageTime(sentAt) {
    const date = parseTimestamp(sentAt);
    if (!date) return '';

    return date.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    });
}

/**
 * Format duration in seconds to M:SS
 */
function formatDuration(seconds) {
    if (isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}


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

                // Update button state
                toggleMicSendButton();

                // Optional: Close picker after selection
                // emojiPicker.style.display = 'none';
            }
        });
    }
});

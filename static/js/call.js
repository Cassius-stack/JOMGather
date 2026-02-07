/**
 * Video & Voice Call Module
 * Uses WebRTC for peer-to-peer media and Socket.IO for signaling
 */

// ========== CALL STATE ==========
let currentCall = {
    active: false,
    isInitiator: false,
    callType: 'voice',  // 'voice' or 'video'
    remoteUserId: null,
    remoteUserName: null,
    peerConnection: null,
    localStream: null,
    remoteStream: null,
    startTime: null,
    durationTimer: null,
    offerSent: false  // Track if we've already sent an offer
};

// WebRTC configuration - using public STUN servers
const rtcConfig = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
    ]
};

// ========== UTILITY FUNCTIONS ==========
// Fallback for showToast if not defined in chat.js
if (typeof showToast === 'undefined') {
    window.showToast = function (message, type) {
        console.log(`[Toast ${type}]: ${message}`);
        alert(message);
    };
}

// ========== START CALL ==========
async function startCall(contactId, contactName, callType = 'video') {
    if (currentCall.active) {
        showToast('You are already in a call', 'warning');
        return;
    }

    console.log(`[Call] Starting ${callType} call with ${contactName} (${contactId})`);

    // Check if browser supports WebRTC
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('Your browser does not support video/voice calls. Please use Chrome, Firefox, or Edge.');
        console.error('[Call] WebRTC not supported - navigator.mediaDevices unavailable');
        return;
    }

    // Set call state
    currentCall.active = true;
    currentCall.isInitiator = true;
    currentCall.callType = callType;
    currentCall.remoteUserId = contactId;
    currentCall.remoteUserName = contactName;

    // Show calling screen
    showCallScreen('calling', contactName, callType);

    // Request media access
    try {
        // Always request video so user can toggle camera on during voice calls
        const constraints = {
            audio: true,
            video: true
        };
        currentCall.localStream = await navigator.mediaDevices.getUserMedia(constraints);

        // For voice calls, disable video track initially (can be enabled later)
        if (callType === 'voice') {
            currentCall.localStream.getVideoTracks().forEach(track => {
                track.enabled = false;
                console.log(`[Call] Voice call - video track disabled initially`);
            });
        }

        // Explicitly enable audio tracks
        currentCall.localStream.getAudioTracks().forEach(track => {
            track.enabled = true;
            console.log(`[Call] Track ${track.kind} enabled:`, track.enabled);
        });

        // Show local video preview
        const localVideo = document.getElementById('localVideo');
        if (localVideo && currentCall.localStream) {
            localVideo.srcObject = currentCall.localStream;
            // Reset video opacity based on call type
            localVideo.style.opacity = callType === 'voice' ? '0' : '1';
        }

        // Reset local avatar placeholder based on call type
        const localAvatar = document.getElementById('localAvatarPlaceholder');
        if (localAvatar) {
            localAvatar.style.display = callType === 'voice' ? 'flex' : 'none';
        }
    } catch (err) {
        console.error('[Call] Media access error:', err);
        alert('Could not access camera/microphone. Please check permissions.');
        endCall();
        return;
    }

    // Emit call request to server
    socket.emit('call_user', {
        caller_id: CURRENT_USER_ID,
        callee_id: contactId,
        call_type: callType,
        caller_name: CURRENT_USER_NAME || 'Unknown'
    });
}

// ========== INCOMING CALL HANDLER ==========
function handleIncomingCall(data) {
    if (currentCall.active) {
        // Busy - auto-decline
        socket.emit('call_decline', {
            caller_id: data.caller_id,
            callee_id: CURRENT_USER_ID
        });
        return;
    }

    console.log(`[Call] Incoming ${data.call_type} call from ${data.caller_name}`);

    // Store caller info
    currentCall.remoteUserId = data.caller_id;
    currentCall.remoteUserName = data.caller_name;
    currentCall.callType = data.call_type;

    // Show incoming call popup
    showIncomingCallPopup(data.caller_name, data.call_type);
}

// ========== ACCEPT CALL ==========
async function acceptCall() {
    console.log('[Call] Accepting call...');

    hideIncomingCallPopup();
    currentCall.active = true;
    currentCall.isInitiator = false;

    // Show connecting screen
    showCallScreen('connecting', currentCall.remoteUserName, currentCall.callType);

    // Request media access
    try {
        // Always request video so user can toggle camera on during voice calls
        const constraints = {
            audio: true,
            video: true
        };
        currentCall.localStream = await navigator.mediaDevices.getUserMedia(constraints);

        // For voice calls, disable video track initially (can be enabled later)
        if (currentCall.callType === 'voice') {
            currentCall.localStream.getVideoTracks().forEach(track => {
                track.enabled = false;
                console.log(`[Call] Voice call - video track disabled initially`);
            });
        }

        // Explicitly enable audio tracks
        currentCall.localStream.getAudioTracks().forEach(track => {
            track.enabled = true;
            console.log(`[Call] Track ${track.kind} enabled:`, track.enabled);
        });

        const localVideo = document.getElementById('localVideo');
        if (localVideo && currentCall.localStream) {
            localVideo.srcObject = currentCall.localStream;
            // Reset video opacity based on call type
            localVideo.style.opacity = currentCall.callType === 'voice' ? '0' : '1';
        }

        // Reset local avatar placeholder based on call type
        const localAvatar = document.getElementById('localAvatarPlaceholder');
        if (localAvatar) {
            localAvatar.style.display = currentCall.callType === 'voice' ? 'flex' : 'none';
        }
    } catch (err) {
        console.error('[Call] Media access error:', err);
        showToast('Could not access camera/microphone', 'error');
        endCall();
        return;
    }

    // Notify caller that we accepted
    console.log('[Call] Emitting call_answer to caller:', currentCall.remoteUserId);

    socket.emit('call_answer', {
        caller_id: currentCall.remoteUserId,
        callee_id: CURRENT_USER_ID,
        callee_name: CURRENT_USER_NAME || 'Unknown'
    });

    // Wait for WebRTC offer from caller
}

// ========== DECLINE CALL ==========
function declineCall() {
    console.log('[Call] Declining call...');

    hideIncomingCallPopup();

    socket.emit('call_decline', {
        caller_id: currentCall.remoteUserId,
        callee_id: CURRENT_USER_ID
    });

    resetCallState();
}

// ========== END CALL ==========
function endCall() {
    console.log('[Call] Ending call...');

    if (currentCall.remoteUserId) {
        socket.emit('call_end', {
            user_id: CURRENT_USER_ID,
            other_user_id: currentCall.remoteUserId
        });
    }

    cleanupCall();
}

// ========== WEBRTC SETUP ==========
function setupPeerConnection() {
    console.log('[Call] Setting up peer connection...');

    currentCall.peerConnection = new RTCPeerConnection(rtcConfig);

    // Add local tracks in consistent order: video first, then audio
    // This is critical for WebRTC SDP compatibility
    if (currentCall.localStream) {
        // Add video tracks first (if any)
        const videoTracks = currentCall.localStream.getVideoTracks();
        videoTracks.forEach(track => {
            console.log('[Call] Adding video track to peer connection');
            currentCall.peerConnection.addTrack(track, currentCall.localStream);
        });

        // Then add audio tracks
        const audioTracks = currentCall.localStream.getAudioTracks();
        audioTracks.forEach(track => {
            console.log('[Call] Adding audio track to peer connection');
            currentCall.peerConnection.addTrack(track, currentCall.localStream);
        });
    }

    // Handle incoming tracks
    currentCall.peerConnection.ontrack = (event) => {
        console.log('[Call] Received remote track');
        currentCall.remoteStream = event.streams[0];
        const remoteVideo = document.getElementById('remoteVideo');
        if (remoteVideo) {
            remoteVideo.srcObject = currentCall.remoteStream;

            // Hide placeholder when video starts playing
            remoteVideo.addEventListener('loadedmetadata', () => {
                console.log('[Call] Remote video metadata loaded');
                const placeholder = remoteVideo.parentElement.querySelector('.video-placeholder');
                if (placeholder) placeholder.style.display = 'none';
            });

            remoteVideo.addEventListener('playing', () => {
                console.log('[Call] Remote video playing');
                const placeholder = remoteVideo.parentElement.querySelector('.video-placeholder');
                if (placeholder) placeholder.style.display = 'none';
            });
        }
        updateCallScreen('connected');
    };

    // Handle ICE candidates
    currentCall.peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
            socket.emit('ice_candidate', {
                from_user_id: CURRENT_USER_ID,
                to_user_id: currentCall.remoteUserId,
                candidate: event.candidate
            });
        }
    };

    // Connection state changes
    currentCall.peerConnection.onconnectionstatechange = () => {
        console.log('[Call] Connection state:', currentCall.peerConnection.connectionState);
        if (currentCall.peerConnection.connectionState === 'connected') {
            console.log('[Call] ✅ WebRTC connection established');
            // Update UI to show connected status
            updateCallScreen('connected');

            // Send initial camera/mic status to remote user
            sendInitialMediaStatus();
        } else if (currentCall.peerConnection.connectionState === 'disconnected') {
            console.log('[Call] ⚠️ Connection disconnected');
            setTimeout(() => {
                if (currentCall.peerConnection?.connectionState === 'disconnected') {
                    endCall();
                }
            }, 3000); // Wait 3s before ending (might reconnect)
        } else if (currentCall.peerConnection.connectionState === 'failed') {
            console.log('[Call] ❌ Connection failed');
            endCall();
        }
    };

    // ICE connection state (for debugging)
    currentCall.peerConnection.oniceconnectionstatechange = () => {
        console.log('[Call] ICE connection state:', currentCall.peerConnection.iceConnectionState);
    };
}

// ========== CREATE & SEND OFFER (CALLER) ==========
async function createAndSendOffer() {
    // Guard: only create offer once per call
    if (currentCall.offerSent) {
        console.log('[Call] Ignoring duplicate createAndSendOffer - offer already sent');
        return;
    }

    currentCall.offerSent = true;  // Mark as sent before async operations

    setupPeerConnection();

    try {
        const offer = await currentCall.peerConnection.createOffer();
        await currentCall.peerConnection.setLocalDescription(offer);

        socket.emit('webrtc_offer', {
            caller_id: CURRENT_USER_ID,
            callee_id: currentCall.remoteUserId,
            offer: offer
        });

        console.log('[Call] Offer sent');
    } catch (err) {
        console.error('[Call] Error creating offer:', err);
        currentCall.offerSent = false;  // Reset flag on error
        endCall();
    }
}

// ========== HANDLE OFFER (CALLEE) ==========
async function handleWebRTCOffer(data) {
    console.log('[Call] Received offer from', data.caller_id);

    // Only process offers from the caller we're expecting (the one we accepted a call from)
    if (!currentCall.active || currentCall.remoteUserId != data.caller_id) {
        console.log('[Call] Ignoring offer - not in active call with this caller');
        return;
    }

    // Prevent processing duplicate offers if peer connection already exists and is not closed
    if (currentCall.peerConnection && currentCall.peerConnection.signalingState !== 'closed') {
        console.log('[Call] Ignoring duplicate offer - peer connection already established');
        return;
    }

    setupPeerConnection();

    try {
        await currentCall.peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer));

        const answer = await currentCall.peerConnection.createAnswer();
        await currentCall.peerConnection.setLocalDescription(answer);

        socket.emit('webrtc_answer', {
            caller_id: data.caller_id,
            callee_id: CURRENT_USER_ID,
            answer: answer
        });

        console.log('[Call] Answer sent');
    } catch (err) {
        console.error('[Call] Error handling offer:', err);
        endCall();
    }
}

// ========== HANDLE ANSWER (CALLER) ==========
async function handleWebRTCAnswer(data) {
    console.log('[Call] Received answer from', data.callee_id);

    // Only the caller (initiator) should process answers
    if (!currentCall.isInitiator) {
        console.log('[Call] Ignoring answer - we are not the initiator');
        return;
    }

    // Ensure peer connection exists and is in correct state
    if (!currentCall.peerConnection || currentCall.peerConnection.signalingState !== 'have-local-offer') {
        console.log('[Call] Ignoring answer - peer connection not in correct state:',
            currentCall.peerConnection?.signalingState);
        return;
    }

    try {
        await currentCall.peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer));
    } catch (err) {
        console.error('[Call] Error handling answer:', err);
        endCall();
    }
}

// ========== HANDLE ICE CANDIDATE ==========
async function handleICECandidate(data) {
    if (currentCall.peerConnection && data.candidate) {
        try {
            await currentCall.peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
        } catch (err) {
            console.error('[Call] Error adding ICE candidate:', err);
        }
    }
}

// ========== CALL CONTROLS ==========
function toggleMic() {
    if (currentCall.localStream) {
        const audioTracks = currentCall.localStream.getAudioTracks();
        audioTracks.forEach(track => {
            track.enabled = !track.enabled;
        });

        const isMuted = !audioTracks[0]?.enabled;

        // Update button state
        const micBtn = document.getElementById('toggleMicBtn');
        if (micBtn) {
            micBtn.innerHTML = isMuted ? '<i class="bi bi-mic-mute-fill"></i>' : '<i class="bi bi-mic-fill"></i>';
            micBtn.classList.toggle('muted', isMuted);
        }

        // Show/hide local mute indicator
        const localMuteIcon = document.getElementById('localMuteIcon');
        if (localMuteIcon) {
            localMuteIcon.style.display = isMuted ? 'inline-block' : 'none';
        }

        // Broadcast mute status to remote user
        if (currentCall.remoteUserId) {
            socket.emit('mic_status', {
                from_user_id: CURRENT_USER_ID,
                to_user_id: currentCall.remoteUserId,
                is_muted: isMuted
            });
        }
    }
}

function toggleCamera() {
    if (currentCall.localStream) {
        const videoTracks = currentCall.localStream.getVideoTracks();
        videoTracks.forEach(track => {
            track.enabled = !track.enabled;
        });

        const isOff = !videoTracks[0]?.enabled;

        // Update button state
        const camBtn = document.getElementById('toggleCameraBtn');
        if (camBtn) {
            camBtn.innerHTML = isOff ? '<i class="bi bi-camera-video-off-fill"></i>' : '<i class="bi bi-camera-video-fill"></i>';
            camBtn.classList.toggle('camera-off', isOff);
        }

        // Show/hide local avatar placeholder
        const localVideo = document.getElementById('localVideo');
        const localAvatar = document.getElementById('localAvatarPlaceholder');
        if (localVideo && localAvatar) {
            if (isOff) {
                localVideo.style.opacity = '0';
                localAvatar.style.display = 'flex';
            } else {
                localVideo.style.opacity = '1';
                localAvatar.style.display = 'none';
            }
        }

        // Broadcast camera status to remote user
        if (currentCall.remoteUserId) {
            socket.emit('camera_status', {
                from_user_id: CURRENT_USER_ID,
                to_user_id: currentCall.remoteUserId,
                is_camera_off: isOff
            });
        }
    }
}

// ========== SEND INITIAL MEDIA STATUS ==========
function sendInitialMediaStatus() {
    if (!currentCall.localStream || !currentCall.remoteUserId) return;

    // Get current camera status
    const videoTracks = currentCall.localStream.getVideoTracks();
    const isCameraOff = videoTracks.length === 0 || !videoTracks[0]?.enabled;

    // Get current mic status
    const audioTracks = currentCall.localStream.getAudioTracks();
    const isMicMuted = audioTracks.length === 0 || !audioTracks[0]?.enabled;

    console.log('[Call] Sending initial media status - camera off:', isCameraOff, 'mic muted:', isMicMuted);

    // Send camera status
    socket.emit('camera_status', {
        from_user_id: CURRENT_USER_ID,
        to_user_id: currentCall.remoteUserId,
        is_camera_off: isCameraOff
    });

    // Send mic status
    socket.emit('mic_status', {
        from_user_id: CURRENT_USER_ID,
        to_user_id: currentCall.remoteUserId,
        is_muted: isMicMuted
    });
}

// ========== UI FUNCTIONS ==========
function showIncomingCallPopup(callerName, callType) {
    const popup = document.getElementById('incomingCallPopup');
    if (!popup) return;

    const icon = callType === 'video' ? '📹' : '📞';
    popup.querySelector('.caller-name').textContent = callerName;
    popup.querySelector('.call-type-label').textContent = `${icon} Incoming ${callType} call`;
    popup.classList.add('show');

    // Play ringtone (optional)
}

function hideIncomingCallPopup() {
    const popup = document.getElementById('incomingCallPopup');
    if (popup) {
        popup.classList.remove('show');
    }
}

function showCallScreen(state, userName, callType) {
    const screen = document.getElementById('callScreen');
    if (!screen) return;

    screen.querySelector('.call-user-name').textContent = userName;

    // Set remote user name on their video panel
    const remoteNameEl = document.getElementById('remoteUserName');
    if (remoteNameEl) {
        remoteNameEl.textContent = userName;
    }

    // Update status text
    const statusEl = screen.querySelector('.call-status');
    const durationEl = document.getElementById('callDuration');

    if (state === 'calling') {
        statusEl.textContent = 'Calling...';
        if (durationEl) durationEl.style.display = 'none';
    } else if (state === 'connecting') {
        statusEl.textContent = 'Connecting...';
        if (durationEl) durationEl.style.display = 'none';
    } else {
        statusEl.textContent = '';
    }

    // Always show video panels for both voice and video calls
    const videoSection = screen.querySelector('.video-container');
    if (videoSection) {
        videoSection.style.display = 'flex';
    }

    // Reset mic button to ON (unmuted) state for new calls
    const micBtn = document.getElementById('toggleMicBtn');
    if (micBtn) {
        micBtn.innerHTML = '<i class="bi bi-mic-fill"></i>';
        micBtn.classList.remove('muted');
    }

    // Reset camera button based on call type
    const camBtn = document.getElementById('toggleCameraBtn');
    if (camBtn) {
        camBtn.style.display = 'flex';
        // For voice calls, show camera as off by default
        if (callType === 'voice') {
            camBtn.innerHTML = '<i class="bi bi-camera-video-off-fill"></i>';
            camBtn.classList.add('camera-off');
        } else {
            camBtn.innerHTML = '<i class="bi bi-camera-video-fill"></i>';
            camBtn.classList.remove('camera-off');
        }
    }

    // Reset local video placeholder visibility
    const localPlaceholder = document.querySelector('.local-video-wrapper .video-placeholder');
    if (localPlaceholder) {
        localPlaceholder.style.display = callType === 'voice' ? 'flex' : 'none';
    }

    // Reset local mute indicator
    const localMuteIndicator = document.getElementById('localMuteIcon');
    if (localMuteIndicator) {
        localMuteIndicator.style.display = 'none';
    }

    // Reset remote user UI elements to default (show video, hide mute/camera icons)
    const remoteMuteIcon = document.getElementById('remoteMuteIcon');
    if (remoteMuteIcon) {
        remoteMuteIcon.style.display = 'none';
    }

    const remoteCameraIcon = document.getElementById('remoteCameraOffIcon');
    if (remoteCameraIcon) {
        remoteCameraIcon.style.display = 'none';
    }

    const remoteAvatar = document.getElementById('remoteAvatarPlaceholder');
    if (remoteAvatar) {
        remoteAvatar.style.display = 'none';
    }

    const remoteVideo = document.getElementById('remoteVideo');
    if (remoteVideo) {
        remoteVideo.style.opacity = '1';
    }

    screen.classList.add('show');
}

function updateCallScreen(state) {
    const statusEl = document.querySelector('#callScreen .call-status');
    const durationEl = document.getElementById('callDuration');

    if (!statusEl) return;

    if (state === 'connected') {
        statusEl.textContent = 'Connected';
        // Start call duration timer
        startCallDurationTimer();
    } else if (state === 'connecting') {
        statusEl.textContent = 'Connecting...';
        if (durationEl) durationEl.style.display = 'none';
    } else {
        statusEl.textContent = '';
        if (durationEl) durationEl.style.display = 'none';
    }
}

function startCallDurationTimer() {
    currentCall.startTime = Date.now();
    const durationEl = document.getElementById('callDuration');

    if (durationEl) {
        durationEl.style.display = 'block';
        durationEl.textContent = '00:00';
    }

    // Clear any existing timer
    if (currentCall.durationTimer) {
        clearInterval(currentCall.durationTimer);
    }

    // Update every second
    currentCall.durationTimer = setInterval(() => {
        if (!currentCall.active || !currentCall.startTime) {
            clearInterval(currentCall.durationTimer);
            return;
        }

        const elapsed = Math.floor((Date.now() - currentCall.startTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;

        if (durationEl) {
            durationEl.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        }
    }, 1000);
}

function hideCallScreen() {
    const screen = document.getElementById('callScreen');
    if (screen) {
        screen.classList.remove('show');
    }
}

function cleanupCall() {
    // Stop duration timer
    if (currentCall.durationTimer) {
        clearInterval(currentCall.durationTimer);
    }

    // Stop local stream
    if (currentCall.localStream) {
        currentCall.localStream.getTracks().forEach(track => track.stop());
    }

    // Close peer connection
    if (currentCall.peerConnection) {
        currentCall.peerConnection.close();
    }

    // Clear video elements
    const localVideo = document.getElementById('localVideo');
    const remoteVideo = document.getElementById('remoteVideo');
    if (localVideo) localVideo.srcObject = null;
    if (remoteVideo) remoteVideo.srcObject = null;

    // Hide call screen
    hideCallScreen();

    // Reset state
    currentCall = {
        active: false,
        isInitiator: false,
        callType: 'voice',
        remoteUserId: null,
        remoteUserName: null,
        peerConnection: null,
        localStream: null,
        remoteStream: null,
        startTime: null,
        durationTimer: null,
        offerSent: false
    };
}

// ========== SOCKET EVENT HANDLERS ==========
function registerCallSocketEvents() {
    // Incoming call notification
    socket.on('incoming_call', handleIncomingCall);

    // Call was accepted - initiate WebRTC
    socket.on('call_accepted', (data) => {
        console.log('[Call] Call accepted by', data.callee_name);
        updateCallScreen('connecting');
        createAndSendOffer();
    });

    // Call was declined
    socket.on('call_declined', (data) => {
        console.log('[Call] Call declined');
        // Only process if we're actually in a call with this person
        if (currentCall.active && currentCall.remoteUserId === data.callee_id) {
            showToast('Call declined', 'info');
            cleanupCall();
        } else {
            console.log('[Call] Ignoring stale call_declined event');
        }
    });

    // Call was ended by other party
    socket.on('call_ended', (data) => {
        console.log('[Call] Received call_ended event from', data.user_id);
        // Only end the call if we're actually in an active call
        // This prevents stale events from ending newly started calls
        if (currentCall.active && currentCall.remoteUserId === data.user_id) {
            console.log('[Call] Call ended by other user');
            showToast('Call ended', 'info');
            cleanupCall();
        } else {
            console.log('[Call] Ignoring stale call_ended event (not in active call)');
        }
    });

    // WebRTC signaling
    socket.on('webrtc_offer', handleWebRTCOffer);
    socket.on('webrtc_answer', handleWebRTCAnswer);
    socket.on('ice_candidate', handleICECandidate);

    // Mute status updates
    socket.on('mute_status', (data) => {
        console.log('[Call] Remote user mute status:', data.is_muted);
        const remoteMuteIcon = document.getElementById('remoteMuteIcon');
        if (remoteMuteIcon) {
            remoteMuteIcon.style.display = data.is_muted ? 'inline-block' : 'none';
        }
    });

    // Camera status updates
    socket.on('camera_status', (data) => {
        console.log('[Call] Remote user camera status:', data.is_camera_off ? 'OFF' : 'ON');
        const remoteVideo = document.getElementById('remoteVideo');
        const remoteAvatar = document.getElementById('remoteAvatarPlaceholder');
        const remoteCameraIcon = document.getElementById('remoteCameraOffIcon');

        if (data.is_camera_off) {
            if (remoteVideo) remoteVideo.style.opacity = '0';
            if (remoteAvatar) remoteAvatar.style.display = 'flex';
            if (remoteCameraIcon) remoteCameraIcon.style.display = 'inline-block';
        } else {
            if (remoteVideo) remoteVideo.style.opacity = '1';
            if (remoteAvatar) remoteAvatar.style.display = 'none';
            if (remoteCameraIcon) remoteCameraIcon.style.display = 'none';
        }
    });

    // Mic status updates
    socket.on('mic_status', (data) => {
        console.log('[Call] Remote user mic status:', data.is_muted ? 'MUTED' : 'UNMUTED');
        const remoteMuteIcon = document.getElementById('remoteMuteIcon');

        if (remoteMuteIcon) {
            remoteMuteIcon.style.display = data.is_muted ? 'inline-block' : 'none';
        }
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Wait for socket to be available
    if (typeof socket !== 'undefined') {
        // Register user with Socket.IO to join personal room for call notifications
        const registerUser = () => {
            console.log('[Socket.IO] ✅ Registering user', CURRENT_USER_ID, 'for call notifications');
            socket.emit('register', { user_id: CURRENT_USER_ID });
        };

        // If socket is already connected, register immediately
        if (socket.connected) {
            registerUser();
        }

        // Also register on connect/reconnect events
        socket.on('connect', () => {
            console.log('[Socket.IO] ✅ Connected to server as user', CURRENT_USER_ID);
            registerUser();
        });

        socket.on('disconnect', () => {
            console.log('[Socket.IO] ❌ Disconnected from server');
        });

        registerCallSocketEvents();
    } else {
        console.error('[Call] Socket.IO not available!');
    }
});

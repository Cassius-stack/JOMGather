/**
 * Savvy Guide - AI Navigation Assistant
 * Handles user queries, sends them to the backend, and executes navigation actions.
 */

document.addEventListener('DOMContentLoaded', function () {
    const bubble = document.getElementById('savvyBubble');
    const panel = document.getElementById('savvyPanel');
    const closeBtn = document.getElementById('savvyClose');
    const input = document.getElementById('savvyInput');
    const sendBtn = document.getElementById('savvySend');
    const chatHistory = document.getElementById('savvyChat');

    if (!bubble) return;

    // Toggle Panel
    bubble.addEventListener('click', () => {
        panel.classList.toggle('show');
        bubble.classList.toggle('active');
        if (panel.classList.contains('show')) {
            input.focus();
        }
    });

    // Close Panel
    window.addEventListener('click', (e) => {
        if (!bubble.contains(e.target) && !panel.contains(e.target)) {
            panel.classList.remove('show');
            bubble.classList.remove('active');
        }
    });

    // Handle Query
    async function handleQuery() {
        const query = input.value.trim();
        if (!query) return;

        // Add user message
        addMessage(query, 'user');
        input.value = '';

        // Add loading indicator
        const loadingId = addLoading();

        try {
            const response = await fetch('/social/api/savvy-assist', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            });

            const result = await response.json();

            // Remove loading
            document.getElementById(loadingId).remove();

            // Handle AI Response
            if (result.response) {
                addMessage(result.response, 'ai');
            }

            // Execute Action
            if (result.action === 'redirect' || result.action === 'chat') {
                setTimeout(() => {
                    window.location.href = result.target;
                }, 1500); // 1.5s delay so user can read the confirmation
            }

        } catch (error) {
            console.error('Savvy Assist Error:', error);
            document.getElementById(loadingId).remove();
            addMessage("Oops! I'm having a little trouble connecting. Please try again later.", 'ai');
        }
    }

    // --- Live Transcription Logic ---
    const micBtn = document.getElementById('savvyMic');
    let recognition;
    let isRecording = false;

    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US'; // Can be made dynamic later

        recognition.onstart = () => {
            isRecording = true;
            micBtn.classList.add('recording');
            micBtn.innerHTML = '<i class="bi bi-stop-fill"></i>';
            input.placeholder = "Listening...";
        };

        recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            // Populate input field in real-time
            if (finalTranscript || interimTranscript) {
                input.value = (finalTranscript + interimTranscript).trim();
            }
        };

        recognition.onerror = (event) => {
            console.error("Speech Recognition Error:", event.error);
            stopRecording();
            if (event.error === 'not-allowed') {
                addMessage("Microphone access denied. Please check your browser settings.", 'ai');
            }
        };

        recognition.onend = () => {
            stopRecording();
        };

        micBtn.addEventListener('click', () => {
            if (!isRecording) {
                recognition.start();
            } else {
                recognition.stop();
            }
        });
    } else {
        micBtn.style.display = 'none';
        console.warn("Speech Recognition not supported in this browser.");
    }

    function stopRecording() {
        if (recognition && isRecording) {
            recognition.stop();
        }
        isRecording = false;
        micBtn.classList.remove('recording');
        micBtn.innerHTML = '<i class="bi bi-mic-fill"></i>';
        input.placeholder = "Where do you want to go?";
    }

    // Note: handleVoiceQuery is no longer needed for live mode as SpeechRecognition handles it natively.

    function addMessage(text, type) {
        const div = document.createElement('div');
        div.className = `savvy-msg ${type}`;
        div.textContent = text;
        chatHistory.appendChild(div);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function addLoading() {
        const id = 'loading-' + Date.now();
        const div = document.createElement('div');
        div.id = id;
        div.className = 'typing-dots ai';
        div.innerHTML = '<span></span><span></span><span></span>';
        chatHistory.appendChild(div);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        return id;
    }

    sendBtn.addEventListener('click', handleQuery);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleQuery();
    });
});
